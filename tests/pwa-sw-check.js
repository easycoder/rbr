// pwa-sw-check.js — the service worker has to be able to boot the app with no
// network.
//
//   node tests/pwa-sw-check.js
//
// Why this exists. The app is two scripts from two CDNs (the AllSpeak runtime
// and MQTT.js) plus a pile of same-origin files. The worker cached only the
// same-origin half, so a reload that landed while the phone was offline served
// index.html and then waited for two scripts that could not arrive — an empty
// window with nothing left running to retry. The shell now reloads itself to
// recover a dead socket, which makes that path routine rather than rare: every
// one of those reloads had a chance of landing in a network gap.
//
// The worker now caches both boot scripts: precached on install (tolerating a
// CDN failure so an update is never blocked) and network-first with a cache
// fallback on every load. This drives sw.js in a tiny sandbox — no browser, no
// network — with fake caches and fetch, and checks the four behaviours the
// offline boot depends on.

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const SW_PATH = path.join(ROOT, 'new-ui', 'sw.js');
const ORIGIN = 'https://rbr.example';

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

function absolute(input) {
  if (typeof input === 'string') return new URL(input, ORIGIN + '/new-ui/').href;
  return input.url;
}

function response(url, type, status) {
  return {
    url,
    type: type || 'basic',
    status: status === undefined ? 200 : status,
    ok: (status === undefined ? 200 : status) >= 200 && (status === undefined ? 200 : status) < 300,
    clone() { return response(url, type, status); }
  };
}

// A Cache-compatible store, just the calls sw.js makes.
function makeCache(store) {
  const keyOf = input => absolute(input);
  return {
    async put(input, res) { store.set(keyOf(input), res); },
    async match(input, options) {
      const key = keyOf(input);
      if (store.has(key)) return store.get(key);
      if (options && options.ignoreSearch) {
        const bare = key.split('?')[0];
        for (const [k, v] of store) if (k.split('?')[0] === bare) return v;
      }
      return undefined;
    }
  };
}

// Load sw.js against fake globals and return its listeners plus the machinery.
function loadWorker() {
  const store = new Map();
  const cache = makeCache(store);
  const listeners = {};
  const deleted = [];
  const claims = [];
  const calls = [];

  const self = {
    location: { origin: ORIGIN },
    addEventListener(ev, fn) { listeners[ev] = fn; },
    async skipWaiting() { calls.push('skipWaiting'); },
    clients: { async claim() { claims.push('claim'); } }
  };

  let openedName = null;
  const caches = {
    async open(name) { openedName = name; return cache; },
    async keys() { return ['rbr-cache-old', openedName || 'rbr-cache-current']; },
    async delete(name) { deleted.push(name); return true; },
    async match(input, options) { return cache.match(input, options); }
  };

  // Each test sets `fail` to the set of bare URLs that should throw.
  let failing = new Set();
  let served = [];
  async function fetchStub(input) {
    const url = absolute(input);
    const bare = url.split('?')[0];
    if (failing.has(bare)) throw new Error('offline');
    served.push(url);
    // jsDelivr's scripts arrive as opaque responses to a no-cors <script>.
    const opaque = bare.indexOf('cdn.jsdelivr.net') >= 0;
    return response(url, opaque ? 'opaque' : 'basic', opaque ? 0 : 200);
  }

  const sandbox = {
    self, caches, fetch: fetchStub, URL, console: { log() {}, warn() {}, error() {} }
  };
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(SW_PATH, 'utf8'), sandbox, { filename: 'sw.js' });

  return {
    listeners, store, deleted, claims, calls,
    cacheName() { return openedName; },
    setFailing(urls) { failing = new Set(urls); },
    resetServed() { served = []; },
    served() { return served.slice(); },
    install() {
      let work;
      listeners.install({ waitUntil(p) { work = p; } });
      return work;
    },
    activate() {
      let work;
      listeners.activate({ waitUntil(p) { work = p; } });
      return work;
    },
    async fetch(request) {
      let responded = null;
      listeners.fetch({
        request,
        respondWith(p) { responded = p; }
      });
      return responded === null ? null : responded;
    }
  };
}

async function main() {
  console.log('\n== install ==');
  {
    const w = loadWorker();
    await w.install();
    check('the install finishes', w.store.size > 0);
    check('the app shell is precached', !!w.store.get(ORIGIN + '/new-ui/index.html'));
    check('the AllSpeak runtime is precached',
      !!w.store.get('https://allspeak.ai/dist/allspeak.js'), [...(await w.store.keys())]);
    check('the MQTT client is precached',
      !!w.store.get('https://cdn.jsdelivr.net/npm/mqtt/dist/mqtt.min.js'));
    check('the worker takes over immediately', w.calls.indexOf('skipWaiting') >= 0);
  }

  console.log('\n== install with both CDNs unreachable ==');
  {
    const w = loadWorker();
    w.setFailing(['https://allspeak.ai/dist/allspeak.js', 'https://cdn.jsdelivr.net/npm/mqtt/dist/mqtt.min.js']);
    let threw = false;
    await w.install().catch(() => { threw = true; });
    check('a CDN failure does not block the update', !threw);
    check('  and the app shell is still cached', !!w.store.get(ORIGIN + '/new-ui/index.html'));
  }

  console.log('\n== a boot script while online ==');
  {
    const w = loadWorker();
    const req = { url: 'https://allspeak.ai/dist/allspeak.js?v=26051101', method: 'GET' };
    const res = await w.fetch(req);
    check('the request is answered from the network', !!res && res.status === 200, res && res.status);
    check('  and kept for the next offline start',
      !!w.store.get('https://allspeak.ai/dist/allspeak.js?v=26051101'));
  }

  console.log('\n== a boot script while offline ==');
  {
    const w = loadWorker();
    await w.install();
    const runtime = 'https://allspeak.ai/dist/allspeak.js?v=26051101';
    const mqtt = 'https://cdn.jsdelivr.net/npm/mqtt/dist/mqtt.min.js';
    w.setFailing([runtime.split('?')[0], mqtt]);
    const gotRuntime = await w.fetch({ url: runtime, method: 'GET' }).catch(() => null);
    const gotMqtt = await w.fetch({ url: mqtt, method: 'GET' }).catch(() => null);
    check('the runtime still loads', !!gotRuntime, gotRuntime && gotRuntime.url);
    check('  from the cached copy', gotRuntime && gotRuntime.type === 'basic');
    check('the MQTT client still loads', !!gotMqtt, gotMqtt && gotMqtt.url);
    check('  opaque responses are cached too', gotMqtt && gotMqtt.type === 'opaque');
  }

  console.log('\n== a new runtime pin while offline ==');
  {
    const w = loadWorker();
    await w.install();
    w.setFailing(['https://allspeak.ai/dist/allspeak.js']);
    const got = await w.fetch({ url: 'https://allspeak.ai/dist/allspeak.js?v=99999999', method: 'GET' })
      .catch(() => null);
    check('an unknown pin falls back across the query string', !!got, got && got.url);
    check('  rather than leaving a blank page', got && /allspeak\.js|99999999/.test(got.url), got && got.url);
  }

  console.log('\n== everything else is untouched ==');
  {
    const w = loadWorker();
    const other = await w.fetch({ url: 'https://example.com/tracker.js', method: 'GET' });
    check('an unrelated cross-origin request is not intercepted', other === null);
    const sameOrigin = await w.fetch({ url: ORIGIN + '/new-ui/resources/allspeak/shell.allspeak?v=1', method: 'GET' });
    check('a same-origin file is still network-first', !!sameOrigin && sameOrigin.status === 200);
    check('  and cached',
      !!w.store.get(ORIGIN + '/new-ui/resources/allspeak/shell.allspeak?v=1'));
    const post = await w.fetch({ url: ORIGIN + '/new-ui/credentials.php', method: 'POST' });
    check('a POST passes straight through', post === null);
  }

  console.log('\n== activate ==');
  {
    const w = loadWorker();
    await w.install();
    const current = w.cacheName();
    await w.activate();
    check('old caches are deleted', w.deleted.indexOf('rbr-cache-old') >= 0, w.deleted);
    check('  and the current one is kept', current && w.deleted.indexOf(current) < 0, w.deleted);
    check('the worker claims its clients', w.claims.length > 0);
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
