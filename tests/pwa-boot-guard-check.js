// pwa-boot-guard-check.js — the page must say something, and keep trying,
// when the CDN scripts it boots from never arrive.
//
//   node tests/pwa-boot-guard-check.js
//
// Why this exists. Everything on the page is driven by the AllSpeak runtime;
// the MQTT client comes from a second CDN. If either fails to load, no script
// is left running to retry, so an offline reload left an empty window for
// ever. The service worker now caches both (pwa-sw-check covers that), and
// index.html adds a small guard for the case where even the cache has nothing:
// it says the app is trying, offers a Retry, and reloads with a backoff.
//
// The other half of the guard matters as much: it must NOT fire on a good
// boot. It runs 200ms after `load`, so this drives both cases in jsdom — one
// with the runtime missing, one with it present — and checks which of the two
// happened.

const http = require('http');
const fs = require('fs');
const path = require('path');
const { JSDOM, VirtualConsole } = require('jsdom');

const ROOT = path.join(__dirname, '..');
const UI = path.join(ROOT, 'new-ui');

let pass = 0;
let fail = 0;
const failures = [];

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
  connect: function () {
    var handlers = {};
    var client = {
      on: function (ev, cb) { handlers[ev] = cb; return client; },
      subscribe: function () { return client; },
      publish: function (t, p, o, cb) { var d = (typeof o === 'function') ? o : cb; if (d) setTimeout(function () { d(null); }, 1); return client; },
      end: function () {}
    };
    setTimeout(function () { if (handlers.connect) handlers.connect(); }, 20);
    return client;
  }
};`;

const CREDENTIALS = { broker: 'broker.invalid', port: 443, username: 'check', password: 'check' };

// The real index.html with only its two CDN script URLs swapped for local
// ones, so the test can make each of them missing or present.
function pageHtml(runtimePath) {
  const html = fs.readFileSync(path.join(UI, 'index.html'), 'utf8');
  return html
    .replace(/<script[^>]+src=['"]https:\/\/allspeak\.ai\/[^'"]+['"][^>]*><\/script>/, `<script src="${runtimePath}"></script>`)
    .replace(/<script[^>]+src=['"]https:\/\/cdn\.jsdelivr\.net\/[^'"]+['"][^>]*><\/script>/, '<script src="/__mqtt-stub.js"></script>');
}

function runtimeUrl() {
  const html = fs.readFileSync(path.join(UI, 'index.html'), 'utf8');
  const m = /<script[^>]+src=['"]([^'"]*allspeak[^'"]*\.js[^'"]*)['"]/i.exec(html);
  return m ? new URL(m[1], 'https://allspeak.ai/').href : null;
}

function serve(runtimeBody) {
  const state = { runtimeAvailable: true };
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://127.0.0.1');
    if (url.pathname === '/new-ui/__check.html') {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      return res.end(pageHtml('/__runtime.js'));
    }
    if (url.pathname === '/__runtime.js') {
      if (!state.runtimeAvailable || !runtimeBody) return res.writeHead(404).end('missing');
      res.writeHead(200, { 'Content-Type': 'text/javascript' });
      return res.end(runtimeBody);
    }
    if (url.pathname === '/__mqtt-stub.js') {
      res.writeHead(200, { 'Content-Type': 'text/javascript' });
      return res.end(MQTT_STUB);
    }
    if (url.pathname === '/new-ui/credentials.json') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify(CREDENTIALS));
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

async function openPage(port, state, runtimeAvailable) {
  state.runtimeAvailable = runtimeAvailable;
  const conflicts = [];
  const vc = new VirtualConsole();
  vc.on('jsdomError', err => { if (/navigation/i.test(err.message)) conflicts.push(err.message); });
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
      window.alert = () => {};
      window.confirm = () => true;
      window.TextEncoder = TextEncoder;
      window.TextDecoder = TextDecoder;
      try { window.localStorage.setItem('dev-mac', '00:11:22:33:44:55'); } catch (e) { /* no storage */ }
    }
  });
  return { dom, conflicts };
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

  const { server, state } = await serve(body);
  const port = server.address().port;

  try {
    console.log('\n== the runtime never arrives ==');
    {
      const { dom, conflicts } = await openPage(port, state, false);
      const d = dom.window.document;
      await sleep(1500);
      const app = d.getElementById('app');
      check('the page says what is happening', /Trying to reach Room By Room/.test(app.textContent),
        app.textContent.slice(0, 80));
      check('  and offers a way to retry', !!app.querySelector('button'));
      check('  without breaking the markup', /data-boot-warning/.test(app.outerHTML));
      // The guard's first retry is 5 seconds out.
      await sleep(5000);
      check('a reload is attempted when nothing recovers it', conflicts.length > 0, conflicts);
      try { dom.window.close(); } catch (e) { /* already closed */ }
    }

    console.log('\n== a normal boot ==');
    {
      const { dom } = await openPage(port, state, true);
      const d = dom.window.document;
      await sleep(1500);
      const app = d.getElementById('app');
      check('the guard leaves the app alone', !/data-boot-warning/.test(app.outerHTML),
        app.textContent.slice(0, 80));
      check('  the runtime started', !!dom.window.AllSpeak);
      try { dom.window.close(); } catch (e) { /* already closed */ }
    }
  } finally {
    server.close();
  }

  console.log(`\n${pass} passed, ${fail} failed`);
  if (fail) {
    console.log('\nFailures: ' + failures.join(', '));
    process.exit(1);
  }
}

main().catch(err => {
  console.log('FAIL: ' + err.stack);
  process.exit(1);
});
