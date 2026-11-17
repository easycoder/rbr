// pwa-handover-alert-check.js — the owner-only handover banner.
//
//   node tests/pwa-handover-alert-check.js
//
// Why this exists. A handover request is a once-in-a-project event, and the
// owner's only warning while it can still be cancelled is a banner in the app.
// The server includes the `handover` object only for the system configured as
// the owner, so this test checks both halves of that promise: the alert paints
// and offers Cancel when credentials.php supplies one, and the banner stays
// hidden when it does not. Tapping Cancel must post the owner's MAC and token
// to /handover.php?action=cancel and then stop offering the action.
//
// It drives the real shell in the real runtime with a fake MQTT client and no
// controller, broker or browser. credentials.json is served by the harness, so
// PHP naming rules are not exercised here — the server-side contract is covered
// by the updater test and the documented readiness check.

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

const BASE_CREDENTIALS = { broker: 'broker.invalid', port: 443, username: 'check', password: 'check' };
let credentialsPayload = BASE_CREDENTIALS;

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
        return res.end(JSON.stringify(credentialsPayload));
      }
      if (url.pathname === '/handover.php') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ ok: true, state: 'cancelled' }));
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

async function runCase(server, port) {
  const lines = [];
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
      window.__handoverRequests = [];
      window.fetch = (url, opts) => {
        const resolved = new URL(url, window.location.href);
        if (resolved.pathname === '/handover.php') {
          window.__handoverRequests.push({
            url: resolved.href,
            method: (opts && opts.method) || 'GET',
            body: (opts && opts.body) || ''
          });
          return Promise.resolve({
            ok: true,
            status: 200,
            headers: { get: () => 'application/json' },
            json: () => Promise.resolve({ ok: true, state: 'cancelled' }),
            text: () => Promise.resolve('{"ok":true,"state":"cancelled"}')
          });
        }
        return globalThis.fetch(resolved.href, opts);
      };
      Object.defineProperty(window.HTMLElement.prototype, 'innerText', {
        get() { return this.textContent; }, set(v) { this.textContent = v; }, configurable: true
      });
      window.scrollTo = () => {};
      window.alert = m => lines.push('alert: ' + m);
      window.confirm = () => true;
      window.TextEncoder = TextEncoder;
      window.TextDecoder = TextDecoder;
      try { window.localStorage.setItem('dev-mac', '00:11:22:33:44:55'); } catch (e) { /* no storage */ }
      try { window.localStorage.setItem('dev-token', 'token-check'); } catch (e) { /* no storage */ }
      try { window.localStorage.setItem('rbr-simple-view', 'off'); } catch (e) { /* no storage */ }
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
  try {
    await waitUntil(() => d.getElementById('top-bar-handover'), BUILD_MS, 'the top bar');
    await waitUntil(() => d.getElementById('top-bar-system-id'), BUILD_MS, 'the top bar row');
    await sleep(300);
    return { dom, d, w, waitUntil };
  } catch (e) {
    try { dom.window.close(); } catch (ignored) { /* already closed */ }
    throw e;
  }
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

  try {
    console.log('\n== the owner sees a flashing banner with a working Cancel ==');
    credentialsPayload = Object.assign({}, BASE_CREDENTIALS, {
      handover: {
        state: 'pending',
        days_left: 9,
        requested_at: 1763000000,
        effective_at: 1764200000,
        url: 'https://new.example.com'
      }
    });
    const first = await runCase(server, port);
    await first.waitUntil(() => {
      const t = first.d.getElementById('top-bar-handover-text');
      return t && t.textContent !== '';
    }, 10000, 'the handover banner text');
    const banner = first.d.getElementById('top-bar-handover');
    const text = first.d.getElementById('top-bar-handover-text');
    const cancel = first.d.getElementById('top-bar-handover-cancel');

    check('the banner is shown', banner && banner.style.display === 'flex', banner && banner.style.display);
    check('it names the days left', text && text.textContent ===
      'Handover request pending — the new owner takes over in 9 days.', text && text.textContent);
    check('the Cancel button is offered', cancel && cancel.style.display === 'inline-block',
      cancel && cancel.style.display);
    check('  and carries a visible label', cancel && cancel.textContent === 'Cancel',
      cancel && cancel.textContent);
    check('the banner carries an alert role', banner && banner.getAttribute('role') === 'alert',
      banner && banner.getAttribute('role'));

    cancel.dispatchEvent(new first.w.MouseEvent('click', { bubbles: true }));
    await first.waitUntil(() => text.textContent === 'Handover request cancelled.',
      10000, 'the cancellation reply');
    check('the banner says the request was cancelled', text.textContent === 'Handover request cancelled.',
      text.textContent);
    check('Cancel is no longer offered', cancel.style.display === 'none', cancel.style.display);
    const sent = first.w.__handoverRequests;
    check('one cancellation was posted', sent.length === 1, sent.length);
    check('  to the handover endpoint', sent[0] && /\/handover\.php\?action=cancel$/.test(sent[0].url),
      sent[0] && sent[0].url);
    check('  with the owner MAC and token', sent[0] && sent[0].body.indexOf('"mac":"00:11:22:33:44:55"') >= 0
      && sent[0].body.indexOf('"token":"token-check"') >= 0, sent[0] && sent[0].body);
    try { first.dom.window.close(); } catch (e) { /* already closed */ }

    console.log('\n== every other system sees nothing ==');
    credentialsPayload = BASE_CREDENTIALS;
    const second = await runCase(server, port);
    const hidden = second.d.getElementById('top-bar-handover');
    check('the banner stays hidden', hidden && hidden.style.display === 'none', hidden && hidden.style.display);
    check('no cancellation was posted', second.w.__handoverRequests.length === 0,
      second.w.__handoverRequests.length);
    try { second.dom.window.close(); } catch (e) { /* already closed */ }

    console.log('\n== the waiting period has ended, so there is nothing left to cancel ==');
    credentialsPayload = Object.assign({}, BASE_CREDENTIALS, {
      handover: {
        state: 'pending',
        days_left: 0,
        requested_at: 1763300000,
        effective_at: 1764510000,
        url: 'https://new.example.com'
      }
    });
    const third = await runCase(server, port);
    await third.waitUntil(() => {
      const t = third.d.getElementById('top-bar-handover-text');
      return t && t.textContent !== '';
    }, 10000, 'the end-of-period banner text');
    const endedText = third.d.getElementById('top-bar-handover-text');
    const endedCancel = third.d.getElementById('top-bar-handover-cancel');
    check('the banner says the period has ended',
      /waiting period has ended/.test(endedText.textContent), endedText.textContent);
    check('and offers no Cancel button', endedCancel.style.display === 'none',
      endedCancel.style.display);
    try { third.dom.window.close(); } catch (e) { /* already closed */ }
  } finally {
    server.close();
  }

  console.log(`\n${pass} passed, ${fail} failed`);
  if (fail) {
    console.log('\nFailures: ' + failures.join(', '));
    process.exit(1);
  }
}

main().catch(e => { console.error(e); process.exit(1); });
