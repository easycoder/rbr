// pwa-schedule-save-check.js — a map that lands while a sheet editor is open
// must not swallow that editor's reply.
//
//   node tests/pwa-schedule-save-check.js
//
// Why this exists. Every sheet editor (schedule, profiles, devices) is opened
// with `send … and assign reply to …`, which parks shell.allspeak until the
// module ships its Save / Cancel reply. The JS runtime keeps just ONE reply
// slot per program (`program.replyVar`). A controller map push is handled by
// the same program, and applying it calls ApplyMapToRooms — another blocking
// send. If that lands while an editor holds the slot, the map's send takes the
// slot for itself; the editor's reply then finds it empty and is dropped. The
// shell never resumes: the sheet chrome stays up, the module has already
// hidden its content, and every tap goes to a scrim whose close request nobody
// is left to consume. On the live system this is the "widget at the bottom and
// the UI is unresponsive" report of 2026-10-24.
//
// A compile check cannot see it and the module-level tests cannot either: the
// fault needs the real shell, parked on a real module, with a real map push in
// the middle. So this drives the whole page in the real runtime, with a fake
// MQTT client standing in for the broker (no broker, controller or browser
// needed), and checks the three things the failure takes away: the sheet
// closes, the save is still sent, and the held map is applied afterwards.

const http = require('http');
const fs = require('fs');
const path = require('path');
const { JSDOM, VirtualConsole } = require('jsdom');

const ROOT = path.join(__dirname, '..');
const UI = path.join(ROOT, 'new-ui');
// jsdom fetches each template through its own XHR path, which on a cold start
// takes long enough that a shorter wait reports a half-built page as a fault.
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
// global: connect on the next tick so the shell's `on mqtt connect` runs, and
// let the test push a controller message through `emit`.
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
    setTimeout(function () { if (handlers.connect) handlers.connect(); }, 20);
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

// The runtime URL is taken from the page itself, so this follows the pin in
// index.html rather than carrying its own copy of it.
function runtimeUrl() {
  const html = fs.readFileSync(path.join(UI, 'index.html'), 'utf8');
  const m = /<script[^>]+src=['"]([^'"]*allspeak[^'"]*\.js[^'"]*)['"]/i.exec(html);
  return m ? new URL(m[1], 'https://allspeak.ai/').href : null;
}

// Credentials and a MAC keep the shell out of demo mode, which is what gives it
// an MQTT connection to stand in for. The map pushed through the stub is the
// repository's demo map: a real controller payload in the shape the shell
// validates, without needing a controller.
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
      try { window.localStorage.setItem('dev-mac', '00:11:22:33:44:55'); } catch (e) { /* no storage */ }
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

  try {
    // The shell only builds the home screen once a full map arrives, so the
    // first push is the one a controller would answer `first` with.
    await waitUntil(() => w.__pushMap, BUILD_MS, 'the MQTT client');
    await sleep(100);
    w.__pushMap(map);
    await waitUntil(() => d.getElementById('special-time-sheet'), BUILD_MS, 'the home screen');
    await sleep(500);

    console.log('\n== a map push while the schedule editor is open ==');
    d.getElementById('room-0-rest').click();
    await sleep(300);
    d.getElementById('room-0-edit-schedule').click();
    await waitUntil(() => {
      const t = d.getElementById('sheet-title');
      return t && /^Schedule for /.test(t.textContent);
    }, SETTLE_MS, 'the schedule editor');

    const marker = lines.length;
    w.__pushMap(map);
    // The map is handled by the same program that is parked on the editor's
    // reply, and the shell says which of the two outcomes happened. Waiting for
    // that line is what makes this deterministic: the reply is only at risk
    // once the map's own send has run.
    await waitUntil(() => since(marker).some(l => /map held while a sheet module is open|OnMapReceived: applying new map/.test(l)),
      SETTLE_MS, 'the map push to be handled');
    const handled = since(marker);
    check('a map pushed while the sheet is open is held, not applied behind the parked reply',
      handled.some(l => /map held while a sheet module is open/.test(l)), handled);

    d.getElementById('schedule-save-btn').click();
    await waitUntil(() => d.getElementById('sheet-root').style.pointerEvents === 'none', SETTLE_MS,
      'the shell to resume and close the sheet');
    check('Save returns to the shell: the sheet chrome closes',
      d.getElementById('sheet-root').style.pointerEvents === 'none'
      && /translateY\(100%\)/.test(d.getElementById('sheet-container').style.transform),
      { pointerEvents: d.getElementById('sheet-root').style.pointerEvents,
        transform: d.getElementById('sheet-container').style.transform });

    const sent = (w.__sent || []).map(m => Buffer.from(m.payload).toString('utf8'));
    check('the save is still sent to the controller',
      sent.some(p => p.includes('Update Profiles')), sent.slice(-2));

    // The flush re-enters OnMapReceived, whose heartbeat pulse waits half a
    // second before the map is applied, so give it that rather than reading
    // the log in the same instant the sheet closes.
    const applied = await waitUntil(
      () => since(marker).some(l => /OnMapReceived: applying new map/.test(l)),
      SETTLE_MS, 'the held map to be applied').catch(() => false);
    check('the held map is applied once the sheet has closed', applied,
      since(marker).filter(l => /OnMapReceived/.test(l)));
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

main().catch(e => { console.error(e); process.exit(1); });
