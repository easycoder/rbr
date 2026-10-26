// pwa-valve-state-check.js — what the room card says when a valve is not doing
// what the controller asked.
//
//   node tests/pwa-valve-state-check.js
//
// Why this exists. RBR's `relay` field is a *demand*, computed from the room
// thermometer and the schedule target. A self-contained TRV does its own
// control, and the bridge already reports the valve's own verdict in
// `running_state` (`heat` = valve open, `idle` = closed). Without that the card
// said "heating" for rooms whose radiators were cold — the 2026-10-26 report,
// where two rooms called for heat and every valve was idle. The card now shows
// the valve's state, and an unactuated room (no relay, no TRV) says so instead
// of pretending to heat.
//
// This drives the whole shell in the real runtime with a fake MQTT client (no
// broker, controller or browser needed) and a map built here, then reads the
// room rows the page rendered.

const http = require('http');
const fs = require('fs');
const path = require('path');
const { JSDOM, VirtualConsole } = require('jsdom');

const ROOT = path.join(__dirname, '..');
const UI = path.join(ROOT, 'new-ui');
const BUILD_MS = 90000;

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

// Five rooms, chosen to cover each branch of the tag:
//   0 valve state unknown, calling      -> "heating" (fall back to demand)
//   1 valve idle, calling               -> "valve idle"
//   2 valve heat, calling               -> "heating"
//   3 relay only, calling               -> "heating" (unchanged)
//   4 no relay and no TRV               -> no tag, "No radiator assigned"
const ROOMS = [
  { name: 'Valve unknown', relays: [], sensor: 'S0', trv: 'T0', linked: 'yes' },
  { name: 'Valve idle', relays: [], sensor: 'S1', trv: 'T1', trvrunning: 'idle', linked: 'yes' },
  { name: 'Valve heat', relays: [], sensor: 'S2', trv: 'T2', trvrunning: 'heat', linked: 'yes' },
  { name: 'Relay heat', relays: ['R3'], sensor: 'S3', linked: 'yes' },
  { name: 'Unwired', relays: [], sensor: 'S4', linked: 'yes' },
];

function fixture() {
  const map = {
    name: 'Valve check',
    profile: 0,
    calendar: 'off',
    'calendar-data': [],
    rooms: [],
    profiles: [{ name: 'Weekday', rooms: {} }],
  };
  ROOMS.forEach((r, i) => {
    map.rooms.push(Object.assign({
      temperature: 1900, humidity: 50, battery: 90, sensorAge: 60000, timestamp: 1,
      status: 'good', statusMessage: '', relayMessage: '',
      relaysFailed: 0, relaysTotal: r.relays.length, relay: 'on',
    }, r));
    map.profiles[0].rooms[r.name] = { mode: 'timed', target: 20, periods: [], advance: '-' };
  });
  return map;
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
  const tag = i => d.getElementById(`room-${i}-heating-tag`);
  const label = i => d.getElementById(`room-${i}-heating-label`);
  const warn = i => d.getElementById(`room-${i}-warn-text`);

  try {
    await waitUntil(() => w.__pushMap, BUILD_MS, 'the MQTT client');
    await sleep(100);
    w.__pushMap(JSON.stringify(fixture()));
    await waitUntil(() => d.getElementById('special-time-sheet'), BUILD_MS, 'the home screen');
    await sleep(500);

    console.log('\n== the room tag says what the valve is doing ==');
    check('an unknown valve state falls back to the demand', tag(0) && tag(0).style.display === 'inline-flex',
      tag(0) && tag(0).style.display);
    check('  and still reads "heating"', label(0) && label(0).textContent === 'heating',
      label(0) && label(0).textContent);

    check('a valve that is idle while the room calls is shown', tag(1) && tag(1).style.display === 'inline-flex',
      tag(1) && tag(1).style.display);
    check('  reads "valve idle", not "heating"', label(1) && label(1).textContent === 'valve idle',
      label(1) && label(1).textContent);
    check('  in the warning colour', tag(1) && /status-warn/.test(tag(1).style.color),
      tag(1) && tag(1).style.color);

    check('a valve that is heating reads "heating"', tag(2) && tag(2).style.display === 'inline-flex'
      && label(2) && label(2).textContent === 'heating',
      label(2) && label(2).textContent);

    check('a relay room is unchanged', tag(3) && tag(3).style.display === 'inline-flex'
      && label(3) && label(3).textContent === 'heating',
      label(3) && label(3).textContent);

    console.log('\n== a room with no actuator says so ==');
    check('no heating tag', tag(4) && tag(4).style.display === 'none', tag(4) && tag(4).style.display);
    check('the warn row explains why', warn(4) && warn(4).textContent === 'No radiator assigned',
      warn(4) && warn(4).textContent);
    check('a wired room is not marked', warn(3) && warn(3).textContent !== 'No radiator assigned',
      warn(3) && warn(3).textContent);
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
