// pwa-build-tap-check.js — a tap that lands while the home screen is still
// being built must not kill the shell.
//
//   node tests/pwa-build-tap-check.js
//
// Why this exists. BuildHomeScreen renders the room rows — and wires their
// click handlers — long before it fetches and attaches the sheet chrome at the
// bottom of the same routine. The `rest get` calls in between park the program,
// so the runtime runs a tap's handler in that gap. A tap on a room's info
// button therefore reached PaintInfoSheet while InfoRelayValue had not been
// attached yet, and the runtime failed the statement with "Variable
// 'InfoRelayValue' has not been attached to a DOM element" — which also marks
// the program aborted, so the rest of the build never runs. That is the
// 2026-11-04 report of the error dialog on launch: one tap in the wrong
// millisecond, not repeatable afterwards.
//
// HideAllSheets already carries the same guard ("The SheetsReady gate prevents
// a tap during BuildHomeScreen …"), but the openers reach their own DOM before
// they get that far. This drives the real shell in the real runtime with a
// fake MQTT client, holds the first sheet template on the wire to widen the
// window deterministically, taps the info button inside it, and then checks
// the build finished and the sheet still opens normally.

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

const CREDENTIALS = { broker: 'broker.invalid', port: 443, username: 'check', password: 'check' };

// sheet.json is the first template BuildHomeScreen fetches after rendering and
// wiring the room rows, so holding it puts the test inside the exact window
// the live tap hit. `state.sheetRequested` says the shell is parked on it;
// `state.releaseSheet()` lets the build continue.
function serve(runtimeBody) {
  const state = { sheetRequested: false, releaseSheet: null };
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
    if (url.pathname === '/new-ui/resources/webson/sheet.json') {
      state.sheetRequested = true;
      state.releaseSheet = () => {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(fs.readFileSync(path.join(UI, 'resources', 'webson', 'sheet.json')));
      };
      return;
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
  return new Promise(resolve => {
    server.listen(0, '127.0.0.1', () => resolve({ server, state }));
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

  const { server, state } = await serve(body);
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
  const runtimeErrors = since => since.filter(l => /Runtime error in|has not been attached|is not attached/.test(l));

  try {
    await waitUntil(() => w.__pushMap, BUILD_MS, 'the MQTT client');
    await sleep(100);
    w.__pushMap(map);

    // Rows exist (and their handlers are wired) while the shell is parked on
    // the held sheet template. That is the window the live report fell into.
    await waitUntil(() => state.sheetRequested && d.getElementById('room-0-info-btn'),
      BUILD_MS, 'the room rows and the first sheet fetch');
    const marker = lines.length;
    d.getElementById('room-0-info-btn').click();
    await sleep(300);

    console.log('\n== a tap on the info button during the build ==');
    const early = lines.slice(marker);
    check('the tap does not raise a runtime error', runtimeErrors(early).length === 0,
      runtimeErrors(early));

    state.releaseSheet();
    const built = await waitUntil(() => d.getElementById('special-time-sheet'), SETTLE_MS, 'the home screen')
      .catch(() => false);
    check('the build carries on and finishes', built, lines.slice(-5));

    if (built) {
      console.log('\n== the same button afterwards ==');
      d.getElementById('room-0-info-btn').click();
      await waitUntil(() => d.getElementById('info-sheet') &&
        d.getElementById('info-sheet').style.display === 'block', SETTLE_MS, 'the info sheet')
        .catch(() => false);
      check('the info sheet opens',
        d.getElementById('info-sheet').style.display === 'block',
        d.getElementById('info-sheet').style.display);
      check('  and carries the room readings',
        d.getElementById('info-relay').textContent === 'On'
        && d.getElementById('info-temp').textContent === '18.5°C',
        { relay: d.getElementById('info-relay').textContent, temp: d.getElementById('info-temp').textContent });
    }
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
