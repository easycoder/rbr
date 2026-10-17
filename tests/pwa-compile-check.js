// pwa-compile-check.js — compile every AllSpeak module the PWA loads.
//
//   node tests/pwa-compile-check.js
//
// The new UI is five AllSpeak scripts fetched and compiled in the browser at
// runtime. There is no compiler on the machine that can check them: the
// `allspeak` CLI is a different implementation of the language (a Python port
// with declared types — `dictionary`, `list` — and, at the time of writing, no
// `property` keyword), so pointing it at these files reports language
// differences rather than mistakes. The only thing that knows this dialect is
// the dialect's own runtime.
//
// So this drives the real runtime, at the very URL new-ui/index.html loads it
// from, against each module in turn, and reads the compiler's verdict out of
// the console. Each module is served through a virtual page that mimics the
// PWA's own bootstrap — the same `rest get` + `run` that index.html uses — so
// what is compiled here is compiled exactly as the browser compiles it.
//
// The modules are RUN, not merely compiled, before the verdict is read, and
// running one without the PWA's sheet chrome fails at the first element it
// looks for. That is expected and is not a finding: a runtime error after a
// successful compile still proves the file compiles. What this checks is only
// what no other tool here can check — that the compiler accepts the file — so
// the assertions are "the compiler said Compiled X" and "it said nothing else".
//
// Unused-variable warnings are treated as failures. The browser runtime does
// not print them today, so the baseline is silence, and they are the cheapest
// signal that a rewrite has left a declaration behind.
//
// Visual and behavioural checks belong in the Playwright specs, which need a
// broker and the controller; this needs neither, only network access for the
// runtime itself.

const http = require('http');
const fs = require('fs');
const path = require('path');
const { JSDOM, VirtualConsole } = require('jsdom');

const ROOT = path.join(__dirname, '..');
const UI = path.join(ROOT, 'new-ui');
const MODULE_DIR = path.join(UI, 'resources', 'allspeak');

// How long to give a module to compile and start running. The largest script
// (shell) compiles in well under a second locally; the wait covers a slow
// network fetch of the runtime on the first page only.
const SETTLE_MS = 8000;

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
    console.log('  FAIL ' + name + (detail === undefined ? '' : '   -> ' + detail));
  }
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// The runtime URL is taken from the page itself, so this check follows the pin
// in index.html rather than carrying its own copy of it — and the build under
// test is the build that ships.
function runtimeUrl() {
  const html = fs.readFileSync(path.join(UI, 'index.html'), 'utf8');
  const m = /<script[^>]+src=['"]([^'"]*allspeak[^'"]*\.js[^'"]*)['"]/i.exec(html);
  if (!m) return null;
  return new URL(m[1], 'https://allspeak.ai/').href;
}

// A virtual page under /new-ui/, so the module paths in it resolve exactly as
// they do for the real page. Nothing is written to the working tree.
function checkPage(module, runtime) {
  return `<!DOCTYPE html><html><head><meta charset="UTF-8">
<script type='text/javascript' src='${runtime}'></script>
</head><body><div id="app"></div>
<pre id="allspeak-script" style="display:none">
    !   Compile check
        script Loader
        variable Source
        rest get Source from \`resources/allspeak/${module}?v=\` cat now
        run Source
</pre>
</body></html>`;
}

// Serve the repository, plus the two virtual routes: the check page for a
// module, and the runtime once fetched, so five modules cost one download.
function serve(runtimeBody) {
  return new Promise(resolve => {
    const server = http.createServer((req, res) => {
      const url = new URL(req.url, 'http://127.0.0.1');
      if (url.pathname === '/new-ui/__compile-check') {
        const module = url.searchParams.get('module') || '';
        if (!/^[\w.-]+\.allspeak$/.test(module)) return res.writeHead(400).end('bad module');
        res.writeHead(200, { 'Content-Type': 'text/html' });
        return res.end(checkPage(module, '/__runtime.js'));
      }
      if (url.pathname === '/__runtime.js') {
        if (!runtimeBody) return res.writeHead(503).end('runtime not fetched');
        res.writeHead(200, { 'Content-Type': 'text/javascript' });
        return res.end(runtimeBody);
      }
      const rel = decodeURIComponent(url.pathname).replace(/^\/+/, '');
      let file = path.resolve(ROOT, rel);
      if (!file.startsWith(ROOT + path.sep)) return res.writeHead(403).end('outside the repository');
      if (fs.existsSync(file) && fs.statSync(file).isDirectory()) file = path.join(file, 'index.html');
      fs.readFile(file, (err, body) => {
        if (err) return res.writeHead(404).end('not found');
        const type = file.endsWith('.js') ? 'text/javascript'
          : file.endsWith('.allspeak') ? 'text/plain' : 'application/octet-stream';
        res.writeHead(200, { 'Content-Type': type });
        res.end(body);
      });
    });
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
}

// Load one module and collect everything the runtime says about it.
async function load(module, port) {
  const lines = [];
  const alerts = [];
  const vc = new VirtualConsole();
  vc.on('log', (...a) => lines.push(a.join(' ')));
  vc.on('info', (...a) => lines.push(a.join(' ')));
  vc.on('warn', (...a) => lines.push('warning: ' + a.join(' ')));
  vc.on('error', (...a) => lines.push('error: ' + a.join(' ')));
  const dom = await JSDOM.fromURL(
    `http://127.0.0.1:${port}/new-ui/__compile-check?module=${encodeURIComponent(module)}`,
    {
      runScripts: 'dangerously',
      resources: 'usable',
      pretendToBeVisual: true,
      virtualConsole: vc,
      beforeParse(window) {
        // jsdom has no fetch and no innerText; the AllSpeak loader needs both.
        window.fetch = (url, opts) => globalThis.fetch(new URL(url, window.location.href).href, opts);
        Object.defineProperty(window.HTMLElement.prototype, 'innerText', {
          get() { return this.textContent; }, set(v) { this.textContent = v; }, configurable: true
        });
        window.scrollTo = () => {};
        // Compile errors are put on the screen with alert(), which jsdom has no
        // implementation for and would otherwise swallow.
        window.alert = m => alerts.push(String(m));
      }
    }
  );
  const wanted = /Compiled \w+:/.test(lines.join('\n'));
  for (let i = 0; i < SETTLE_MS / 200 && !wanted; i++) await sleep(200);
  await sleep(400);
  dom.window.close();
  return { lines, alerts };
}

// The compiler names the script it compiled, so the verdict for one module is
// "a Compiled line mentioning something, and no complaint" — the pages compile
// under one name each and none of them is Loader, which is our own wrapper.
function verdict(module, { lines, alerts }) {
  const text = lines.join('\n');
  const compiled = lines.filter(l => /^\d+ ms: Compiled \w+:/.test(l) && !/Compiled Loader:/.test(l));
  const compileError = /Compile error/.test(text) || alerts.some(a => /Compile error/.test(a));
  const warnings = lines.filter(l => /has not been used|Unrecognised syntax/.test(l));
  const detail = compileError ? (alerts[0] || text).split('\n').filter(Boolean).slice(-1)[0]
    : warnings.length ? warnings.join(' | ')
      : compiled.length ? undefined : 'no compiler output — did the runtime load?';
  return { ok: compiled.length > 0 && !compileError && warnings.length === 0, detail, compiled, compileError, warnings };
}

async function main() {
  const modules = fs.readdirSync(MODULE_DIR).filter(f => f.endsWith('.allspeak')).sort();

  console.log('\n== the runtime ==');
  const url = runtimeUrl();
  check('index.html names the runtime the PWA loads', !!url, 'no allspeak.js script tag found');
  let body = null;
  if (url) {
    try {
      const res = await fetch(url);
      body = res.ok ? Buffer.from(await res.arrayBuffer()) : null;
      check(`the runtime at ${url} is reachable`, !!body, res.status + ' ' + res.statusText);
    } catch (e) {
      check(`the runtime at ${url} is reachable`, false, e.message);
    }
  }
  if (!body) {
    console.log(`\n${pass} passed, ${fail} failed, 0 modules checked`);
    process.exit(1);
  }

  console.log('\n== the modules ==');
  const server = await serve(body);
  const base = `http://127.0.0.1:${server.address().port}`;
  const results = [];
  for (const module of modules) {
    const seen = await load(module, server.address().port);
    const v = verdict(module, seen);
    results.push({ module, ...v });
    check(`${module} compiles`, v.ok, v.detail);
  }
  server.close();

  // The five that make up the UI are the reason this exists; a directory that
  // has lost one is a failure in the same right.
  console.log('\n== the set ==');
  for (const name of ['shell.allspeak', 'map-to-rooms.allspeak', 'device-editor.allspeak',
    'profile-sheet.allspeak', 'schedule-editor.allspeak']) {
    check(`${name} is present and compiles`, results.some(r => r.module === name && r.ok));
  }

  console.log(`\n${pass} passed, ${fail} failed, ${modules.length} modules checked`);
  if (fail) {
    console.log('\nFailures: ' + failures.join(', '));
    process.exit(1);
  }
}

main().catch(e => { console.error(e); process.exit(1); });
