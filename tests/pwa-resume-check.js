// pwa-resume-check.js — what the shell does when the phone wakes up after a
// long sleep.
//
//   node tests/pwa-resume-check.js
//
// Why this exists. The runtime ends its MQTT client on the first connection
// error (`client.end(true)`) and only calls `on mqtt connect` on a first
// connect, so MQTT.js's own reconnect never runs for that page: the socket is
// gone for good and the only repair is a reload. The shell did not handle that
// error at all, and its resume hook could only compare timestamps — so a page
// whose client had already been ended looked alive and stayed on the last map
// for ever. That is the recurring 2026-11-04 report: left open, the screen
// times out, and hours later the app is visible but no longer connected.
//
// The hook now tracks whether the client is connected: a resume with no client
// reloads, a resume before the first map asks again instead of waiting for a
// poll loop that does not exist yet, and a healthy resume still just refreshes.
// This drives the real shell in the real runtime with a fake MQTT client and
// tallies the requests the page sends and the lines it logs.

const http = require('http');
const fs = require('fs');
const path = require('path');
const { JSDOM, VirtualConsole } = require('jsdom');

const ROOT = path.join(__dirname, '..');
const UI = path.join(ROOT, 'new-ui');
const BUILD_MS = 90000;
const SETTLE_MS = 15000;

let pass = 0;
let fail = 0;
const failures = [];
const lines = [];

function check(name, ok, detail) {
  if (ok) {
    pass++;
    console.log('  ok   ' + name);
  } else {
    fail++;
    failures.push(name);
    console.log('  FAIL ' + name + (detail === undefined ? '' : '   -> ' + JSON.stringify(detail)));
  }
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

// The runtime brings its own MQTT client class but leaves the transport to the
// page's `mqtt` global (index.html loads it from a CDN). This stub is that
// global: connect on the next tick so the shell's `on mqtt connect` runs, let
// the test push a controller message through `emit`, and let it raise the
// connection error the runtime reacts to.
const MQTT_STUB = `
window.__sent = [];
window.mqtt = {
  connect: function (url, options) {
    var handlers = {};
    var client = {
      on: function (ev, cb) { handlers[ev] = cb; return client; },
      subscribe: function () { return client; },
      publish: function (topic, payload, opts, cb) {
        window.__sent.push({ topic: topic, payload: payload });
        var done = (typeof opts === 'function') ? opts : cb;
        if (done) setTimeout(function () { done(null); }, 1);
        return client;
      },
      end: function () {},
      emit: function (ev) {
        var args = Array.prototype.slice.call(arguments, 1);
        if (handlers[ev]) handlers[ev].apply(null, args);
      }
    };
    window.__pushMap = function (payload) { client.emit('message', 'check-system/reply', payload); };
    window.__mqttError = function (message) { client.emit('error', new Error(message)); };
    // The connection is made when the test asks for it, so the page can be
    // left with a connect that never happens — the state a reload during a
    // sleeping phone produces.
    window.__mqttConnect = function () { if (handlers.connect) handlers.connect(); };
    return client;
  }
};`;

function checkPage(runtimePath) {
  return `<!DOCTYPE html><html><head><meta charset="UTF-8">
<script>${MQTT_STUB}</script>
<script type='text/javascript' src='${runtimePath}'></script>
</head><body><div id="app"></div>
<pre id="allspeak-script" style="display:none">
	script Loader
	variable Shell
	rest get Shell from \`resources/allspeak/shell.allspeak?v=\` cat now
	run Shell
</pre></body></html>`;
}

function runtimeUrl() {
  const html = fs.readFileSync(path.join(UI, 'index.html'), 'utf8');
  const m = /<script[^>]+src=['"]([^'"]*allspeak[^'"]*\.js[^'"]*)['"]/i.exec(html);
  return m ? new URL(m[1], 'https://allspeak.ai/').href : null;
}

const CREDENTIALS = { broker: 'broker.invalid', port: 443, username: 'check', password: 'check' };

function serve(runtimeBody) {
  return new Promise(resolve => {
    const server = http.createServer((req, res) => {
      const url = new URL(req.url, 'http://127.0.0.1');
      if (url.pathname === '/new-ui/__check.html') {
        res.writeHead(200, { 'Content-Type': 'text/html' });
        return res.end(checkPage('/__runtime.js'));
      }
      if (url.pathname === '/new-ui/credentials.json') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify(CREDENTIALS));
      }
      if (url.pathname === '/__runtime.js') {
        if (!runtimeBody) return res.writeHead(503).end('runtime not fetched');
        res.writeHead(200, { 'Content-Type': 'text/javascript' });
        return res.end(runtimeBody);
      }
      const rel = decodeURIComponent(url.pathname).replace(/^\/+/, '');
      const file = path.resolve(ROOT, rel);
      if (!file.startsWith(ROOT + path.sep)) return res.writeHead(403).end('outside the repository');
      fs.readFile(file, (err, body) => {
        if (err) return res.writeHead(404).end('not found');
        const type = file.endsWith('.js') ? 'text/javascript'
          : file.endsWith('.json') ? 'application/json'
            : file.endsWith('.css') ? 'text/css' : 'text/plain';
        res.writeHead(200, { 'Content-Type': type });
        res.end(body);
      });
    });
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
}

async function main() {
  const runtime = runtimeUrl();
  if (!runtime) {
    console.log('FAIL: new-ui/index.html names no allspeak runtime');
    process.exit(1);
  }
  let body = null;
  try {
    const res = await fetch(runtime);
    body = res.ok ? Buffer.from(await res.arrayBuffer()) : null;
  } catch (e) { /* reported below */ }
  if (!body) {
    console.log(`FAIL: could not fetch the runtime at ${runtime}`);
    process.exit(1);
  }
  const map = fs.readFileSync(path.join(UI, 'demo-map.json'), 'utf8');

  const server = await serve(body);
  const port = server.address().port;
  const vc = new VirtualConsole();
  for (const ev of ['log', 'info', 'warn', 'error']) {
    vc.on(ev, (...a) => {
      const one = a.join(' ');
      if (/^\d+ ms: Compiled/.test(one)) return;
      lines.push(one);
    });
  }
  const dom = await JSDOM.fromURL(`http://127.0.0.1:${port}/new-ui/__check.html`, {
    runScripts: 'dangerously',
    resources: 'usable',
    pretendToBeVisual: true,
    virtualConsole: vc,
    beforeParse(window) {
      window.fetch = (url, opts) => globalThis.fetch(new URL(url, window.location.href).href, opts);
      Object.defineProperty(window.HTMLElement.prototype, 'innerText', {
        get() { return this.textContent; }, set(v) { this.textContent = v; }, configurable: true
      });
      window.scrollTo = () => {};
      window.alert = m => lines.push('alert: ' + m);
      window.confirm = () => true;
      window.TextEncoder = TextEncoder;
      window.TextDecoder = TextDecoder;
      try {
        window.localStorage.setItem('dev-mac', '00:11:22:33:44:55');
        // Seed the first-map counter so the watchdog reaches the post-cap path
        // on its first tick, where the old code stopped for good.
        window.localStorage.setItem('first-map-attempts', '3');
      } catch (e) { /* no storage */ }
    }
  });
  const d = dom.window.document;
  const w = dom.window;
  const waitUntil = async (fn, ms, what) => {
    for (let i = 0; i < ms / 100; i++) {
      if (fn()) return true;
      await sleep(100);
    }
    throw new Error(`timed out waiting for ${what}. console:\n` + lines.slice(-25).join('\n'));
  };
  const since = n => lines.slice(n);
  const resume = () => d.dispatchEvent(new w.Event('visibilitychange'));
  const sent = () => (w.__sent || []).map(m => Buffer.from(m.payload).toString('utf8'));
  const mapRequests = marker => since(marker).filter(l => /Requesting map:/.test(l));

  try {
    await waitUntil(() => w.__pushMap && w.__mqttConnect, BUILD_MS, 'the MQTT client');

    console.log('\n== no connection at all, past the old three-attempt cap ==');
    // Nothing is ever connected here. The counter is seeded at 3, so the first
    // watchdog tick is attempt 4: the old code alerted and returned, and a page
    // with no first map has no poll loop either, so it sat on an empty screen
    // until it was closed and reopened. The watchdog is now armed from the
    // bootstrap, which is what lets it notice a connect that never happened.
    const watchdogMarker = lines.length;
    const retried = await waitUntil(
      () => since(watchdogMarker).some(l => /Reloading \(first-map attempt 4\)/.test(l)),
      45000, 'the first-map watchdog to keep retrying').catch(() => false);
    check('the watchdog reloads instead of giving up', retried, since(watchdogMarker).slice(-5));

    // Now let the connection happen, and run the resume cases against it.
    w.__mqttConnect();
    await waitUntil(() => lines.some(l => /Requesting map: first/.test(l)), BUILD_MS, 'the first map request');

    console.log('\n== a resume before the first map has arrived ==');
    // No poll loop exists yet, so the hook has to ask again itself.
    let marker = lines.length;
    resume();
    await waitUntil(() => since(marker).some(l => /Tab resumed/.test(l)), SETTLE_MS, 'the resume hook');
    await sleep(300);
    check('the hook asks for the first map again',
      mapRequests(marker).some(l => /Requesting map: first/.test(l)), mapRequests(marker));
    check('  and does not reload a healthy page',
      !since(marker).some(l => /reloading/.test(l)), since(marker));

    w.__pushMap(map);
    await waitUntil(() => d.getElementById('special-time-sheet'), BUILD_MS, 'the home screen');
    await sleep(500);

    console.log('\n== a resume with a live connection ==');
    marker = lines.length;
    resume();
    await waitUntil(() => since(marker).some(l => /Tab resumed/.test(l)), SETTLE_MS, 'the resume hook');
    await sleep(300);
    check('the hook refreshes', mapRequests(marker).length > 0, mapRequests(marker));
    check('  and keeps the page', !since(marker).some(l => /reloading/.test(l)), since(marker));

    console.log('\n== the connection errors ==');
    marker = lines.length;
    w.__mqttError('socket closed');
    await waitUntil(() => since(marker).some(l => /MQTT error: socket closed/.test(l)), SETTLE_MS,
      'the MQTT error handler');
    check('the error is reported', true);
    check('  and does not abort the script',
      !since(marker).some(l => /Runtime error in/.test(l)), since(marker));

    console.log('\n== the next resume with a dead client ==');
    marker = lines.length;
    resume();
    await waitUntil(() => since(marker).some(l => /MQTT not connected on resume; reloading/.test(l)),
      SETTLE_MS, 'the resume hook to reload');
    check('the hook reloads rather than polling a client the runtime ended', true);
  } finally {
    try { dom.window.close(); } catch (e) { /* already closed */ }
    server.close();
  }

  console.log(`\n${pass} passed, ${fail} failed`);
  if (fail) {
    console.log('\nFailures: ' + failures.join(', '));
    process.exit(1);
  }
}

main().catch(err => {
  console.log('FAIL: ' + err.message);
  process.exit(1);
});
