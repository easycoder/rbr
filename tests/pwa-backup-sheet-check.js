// pwa-backup-sheet-check.js — the Backups sheet under the hamburger.
//
//   node tests/pwa-backup-sheet-check.js
//
// Why this exists. The backup itself is a timer on the controller; the only
// part a person can get wrong is the browser: the menu row must open the
// sheet, the sheet must show the address the controller will use, the toggle
// must ship `Backup` with the address (the timer may run with no browser
// open), and "send now" must ship `Backup Now` without closing the sheet.
// This drives the whole shell in the real runtime with a fake MQTT client and
// a map built here, then reads what was sent.

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

const CREDENTIALS = {
  broker: 'broker.invalid', port: 443, username: 'check', password: 'check',
  email: 'owner@example.com'
};

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

function fixture() {
  return {
    name: 'Backup check',
    profile: 0,
    calendar: 'off',
    'calendar-data': [],
    rooms: [{
      name: 'Kitchen', relays: ['Kitchen-radiator'], sensor: 'Kitchen-thermometer',
      linked: 'yes', temperature: 1900, humidity: 50, battery: 90, sensorAge: 60000,
      timestamp: 1, status: 'good', statusMessage: '', relayMessage: '',
      relaysFailed: 0, relaysTotal: 1, relay: 'on'
    }],
    profiles: [{ name: 'Default', rooms: { Kitchen: { mode: 'timed', target: 20, periods: [], advance: '-' } } }],
    backup: {
      enabled: 'off',
      address: 'owner@example.com',
      last_display: '1 Nov 2026 at 03:00',
      emailed: 'yes',
      ok: 'yes',
      error: ''
    }
  };
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
  const sentRaw = () => (w.__sent || []).map(entry => Buffer.from(entry.payload).toString('utf8'));
  const sent = () => sentRaw()
    .map(text => {
      const start = text.indexOf('{');
      if (start < 0) return null;
      try { return JSON.parse(text.slice(start)); } catch (e) { return null; }
    })
    .filter(frame => frame && frame.message)
    .map(frame => {
      let message = frame.message;
      if (typeof message === 'string') {
        try { message = JSON.parse(message); } catch (e) { /* leave it */ }
      }
      return message;
    })
    .filter(message => message && typeof message === 'object');

  try {
    await waitUntil(() => w.__pushMap, BUILD_MS, 'the MQTT client');
    await sleep(100);
    w.__pushMap(JSON.stringify(fixture()));
    // The last sheet template in BuildHomeScreen, so this waits for the build
    // to finish rather than for the first sheet to appear. Tapping a menu row
    // mid-build is the race the openers now ignore (see pwa-build-tap-check),
    // so a weaker wait here made the click land in the gap and do nothing.
    await waitUntil(() => d.getElementById('special-time-sheet'), BUILD_MS, 'the home screen');

    console.log('\n== the hamburger opens the Backups sheet ==');
    d.getElementById('top-bar-menu-btn').click();
    await sleep(200);
    const menu = d.getElementById('menu-row-backups');
    check('the menu has a Backups row', !!menu, menu && menu.outerHTML.slice(0, 160));
    check('  labelled Backups', menu && /Backups/.test(menu.textContent), menu && menu.textContent);
    menu.click();
    await sleep(300);
    check('the sheet is shown', d.getElementById('backup-sheet').style.display === 'block',
      d.getElementById('backup-sheet').style.display);
    check('  with the registered address', d.getElementById('backup-sheet-email').textContent === 'To owner@example.com',
      d.getElementById('backup-sheet-email').textContent);
    check('  and the last run', /1 Nov 2026 at 03:00/.test(d.getElementById('backup-sheet-last').textContent),
      d.getElementById('backup-sheet-last').textContent);
    check('  toggle reads Off', d.getElementById('backup-sheet-toggle').textContent === 'Off',
      d.getElementById('backup-sheet-toggle').textContent);

    console.log('\n== turning the email copy on keeps the address for the timer ==');
    d.getElementById('backup-sheet-toggle').click();
    await sleep(400);
    check('the toggle reads On', d.getElementById('backup-sheet-toggle').textContent === 'On',
      d.getElementById('backup-sheet-toggle').textContent);
    const backupMessages = sent().filter(message => message.Action === 'Backup');
    check('a Backup uirequest was sent', backupMessages.length > 0, sentRaw());
    const setting = backupMessages[backupMessages.length - 1] || {};
    check('  enabled is on', setting.enabled === 'on', setting);
    check('  the registered address travels with it', setting.address === 'owner@example.com', setting);

    console.log('\n== send now ==');
    d.getElementById('backup-sheet-send').click();
    await sleep(400);
    const nowMessages = sent().filter(message => message.Action === 'Backup Now');
    check('a Backup Now uirequest was sent', nowMessages.length === 1, sentRaw());
    check('the sheet stays open so the result can land', d.getElementById('backup-sheet').style.display === 'block',
      d.getElementById('backup-sheet').style.display);
    check('the notice says it has started', /Backup started/.test(d.getElementById('backup-sheet-notice').textContent),
      d.getElementById('backup-sheet-notice').textContent);
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
