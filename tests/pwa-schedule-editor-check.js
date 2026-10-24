// pwa-schedule-editor-check.js — drives the Schedule sheet's time dropdowns in
// the real runtime and checks how a stop follows its start.
//
//   node tests/pwa-schedule-editor-check.js
//
// Why this exists. The schedule editor used to step both times with +/- buttons.
// A dropdown is a different interaction, and the rule the user asked for —
// Google Calendar's: a new period stops an hour after its start, and an
// existing period keeps its duration when the start moves — lives in one
// change handler. A compile check cannot see either the rendered options or
// what a selection does to the other field; this drives the real module, in
// the real runtime, with jsdom and no broker, controller or browser.
//
// The assertions read the selects back from the DOM, then read the module's
// Save reply. That reply is what the shell ships to the controller, so the
// last check is the one that matters: the editing-only `offAuto` flag must not
// escape into the stored periods.

const http = require('http');
const fs = require('fs');
const path = require('path');
const { JSDOM, VirtualConsole } = require('jsdom');

const ROOT = path.join(__dirname, '..');
const UI = path.join(ROOT, 'new-ui');
const MODULE = 'schedule-editor.allspeak';
const MODULE_FILE = path.join(UI, 'resources', 'allspeak', MODULE);
const SETTLE_MS = 25000;
const STEP_MS = 250;

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

// A small map in the shared-room-list shape: one room with two periods, one
// two-hour and one five-hour, plus a second profile that must not change.
const FIXTURE = {
  profiles: [
    { name: 'Weekday', rooms: {
      Kitchen: {
        mode: 'timed', target: 20, advance: '-', events: [],
        periods: [
          { on: '06:00', off: '08:00', temp: '21.0' },
          { on: '18:00', off: '23:00', temp: '22.0' },
        ],
      },
    } },
    { name: 'Weekend', rooms: {
      Kitchen: {
        mode: 'timed', target: 19, advance: '-', events: [],
        periods: [{ on: '09:00', off: '10:00', temp: '20.0' }],
      },
    } },
  ],
};

// A page that loads the runtime and the module, sends the open message the
// shell sends, and parks until the sheet replies.
function checkPage(runtimePath) {
  return `<!DOCTYPE html><html><head><meta charset="UTF-8">
<script type='text/javascript' src='${runtimePath}'></script>
<style>#out{white-space:pre}</style>
</head><body><div id="app"></div><div id="sheet-content"></div><div id="out"></div>
<pre id="allspeak-script" style="display:none">
    !   Schedule-editor check
        script Check

        variable Source
        variable OpenMsg
        variable Reply
        variable FixtureText
        variable FixtureMap
        variable ReplyText

        module ScheduleEditorModule

        div Out
        attach Out to \`out\`

        rest get Source from \`resources/allspeak/${MODULE}?v=\` cat now
        run Source as ScheduleEditorModule

        rest get FixtureText from \`/__fixture.json?v=\` cat now
        put json FixtureText into FixtureMap

        put \`{}\` into OpenMsg
        set property \`roomName\` of OpenMsg to \`Kitchen\`
        set property \`profileIdx\` of OpenMsg to 0
        set property \`profiles\` of OpenMsg to property \`profiles\` of FixtureMap

        send OpenMsg to ScheduleEditorModule and assign reply to Reply

        put the json of Reply into ReplyText
        set the content of Out to ReplyText cat \`__DONE__\`
</pre></body></html>`;
}

// The runtime URL is taken from the page itself, so this follows the pin in
// index.html rather than carrying its own copy of it.
function runtimeUrl() {
  const html = fs.readFileSync(path.join(UI, 'index.html'), 'utf8');
  const m = /<script[^>]+src=['"]([^'"]*allspeak[^'"]*\.js[^'"]*)['"]/i.exec(html);
  return m ? new URL(m[1], 'https://allspeak.ai/').href : null;
}

function serve(runtimeBody) {
  return new Promise(resolve => {
    const server = http.createServer((req, res) => {
      const url = new URL(req.url, 'http://127.0.0.1');
      if (url.pathname === '/new-ui/__check.html') {
        res.writeHead(200, { 'Content-Type': 'text/html' });
        return res.end(checkPage('/__runtime.js'));
      }
      if (url.pathname === '/__runtime.js') {
        if (!runtimeBody) return res.writeHead(503).end('runtime not fetched');
        res.writeHead(200, { 'Content-Type': 'text/javascript' });
        return res.end(runtimeBody);
      }
      if (url.pathname === '/__fixture.json') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify(FIXTURE));
      }
      const rel = decodeURIComponent(url.pathname).replace(/^\/+/, '');
      const file = path.resolve(ROOT, rel);
      if (!file.startsWith(ROOT + path.sep)) return res.writeHead(403).end('outside the repository');
      fs.readFile(file, (err, body) => {
        if (err) return res.writeHead(404).end('not found');
        const type = file.endsWith('.js') ? 'text/javascript'
          : file.endsWith('.json') ? 'application/json'
            : file.endsWith('.allspeak') ? 'text/plain' : 'application/octet-stream';
        res.writeHead(200, { 'Content-Type': type });
        res.end(body);
      });
    });
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
}

// Set a real <select> and fire the event the browser would fire. The handler
// runs on its own thread, so each caller waits for it before the next step.
async function choose(dom, id, value) {
  const el = dom.window.document.getElementById(id);
  if (!el) throw new Error('no element #' + id + ' — the sheet did not render');
  el.value = value;
  el.dispatchEvent(new dom.window.Event('change'));
  await sleep(STEP_MS);
}

function valueOf(d, id) {
  const el = d.getElementById(id);
  return el ? el.value : null;
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
  if (!fs.existsSync(MODULE_FILE)) {
    console.log(`FAIL: ${MODULE} is missing`);
    process.exit(1);
  }

  const server = await serve(body);
  const port = server.address().port;
  const lines = [];
  const vc = new VirtualConsole();
  for (const ev of ['log', 'info', 'warn', 'error']) {
    vc.on(ev, (...a) => {
      const one = a.join(' ');
      if (/^\d+ ms: Compiled/.test(one)) return;
      lines.push(ev + ': ' + one);
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
      // Freeze the clock for Add period. `the hour of now` must be
      // deterministic for the test, so no-argument `new Date()` and `Date.now()`
      // read a value the test can move between scenarios.
      const RealDate = window.Date;
      window.__now = new RealDate(2026, 9, 24, 15, 7, 0).getTime();
      window.Date = class extends RealDate {
        constructor(...args) {
          if (args.length === 0) super(window.__now);
          else super(...args);
        }
        static now() { return window.__now; }
      };
    }
  });
  const d = dom.window.document;

  try {
    for (let i = 0; i < SETTLE_MS / 150; i++) {
      if (d.getElementById('schedule-period-0-start-select')) break;
      await sleep(150);
    }
    if (!d.getElementById('schedule-period-0-start-select')) {
      throw new Error('the module never rendered a period card. console:\n' + lines.join('\n'));
    }
    await sleep(400);

    console.log('\n== the time controls ==');
    const start0 = d.getElementById('schedule-period-0-start-select');
    check('both times are dropdowns, not steppers',
      start0.tagName === 'SELECT' && d.getElementById('schedule-period-0-off-select').tagName === 'SELECT');
    check('the dropdown offers quarter hours through the day',
      start0.options.length === 96 && start0.options[1].value === '00:15' && start0.options[95].value === '23:45',
      { count: start0.options.length, first: start0.options[0].value, last: start0.options[95].value });
    check('each dropdown shows its stored time',
      start0.value === '06:00' && valueOf(d, 'schedule-period-0-off-select') === '08:00'
      && valueOf(d, 'schedule-period-1-start-select') === '18:00' && valueOf(d, 'schedule-period-1-off-select') === '23:00',
      [start0.value, valueOf(d, 'schedule-period-0-off-select'), valueOf(d, 'schedule-period-1-start-select'), valueOf(d, 'schedule-period-1-off-select')]);

    console.log('\n== moving a start ==');
    await choose(dom, 'schedule-period-0-start-select', '06:30');
    check('an existing two-hour period keeps its duration (06:30–08:30)',
      valueOf(d, 'schedule-period-0-off-select') === '08:30', valueOf(d, 'schedule-period-0-off-select'));

    await choose(dom, 'schedule-period-1-start-select', '19:00');
    check('a five-hour period keeps its duration across midnight (19:00–00:00)',
      valueOf(d, 'schedule-period-1-off-select') === '00:00', valueOf(d, 'schedule-period-1-off-select'));

    await choose(dom, 'schedule-period-1-off-select', '23:30');
    await choose(dom, 'schedule-period-1-start-select', '20:00');
    check('a stop picked by hand becomes the duration that travels (20:00–00:30)',
      valueOf(d, 'schedule-period-1-off-select') === '00:30', valueOf(d, 'schedule-period-1-off-select'));

    await choose(dom, 'schedule-period-1-start-select', '00:30');
    check('a start moved back over midnight takes the short way (00:30–05:00)',
      valueOf(d, 'schedule-period-1-off-select') === '05:00', valueOf(d, 'schedule-period-1-off-select'));
    await choose(dom, 'schedule-period-1-start-select', '20:00');
    check('moving it back again restores the same duration',
      valueOf(d, 'schedule-period-1-off-select') === '00:30', valueOf(d, 'schedule-period-1-off-select'));

    console.log('\n== adding a period ==');
    d.getElementById('schedule-add-btn').click();
    for (let i = 0; i < 20; i++) {
      if (d.getElementById('schedule-period-2-start-select')) break;
      await sleep(150);
    }
    check('with no period running, a new period starts at the quarter hour closest to now (15:07 -> 15:00)',
      valueOf(d, 'schedule-period-2-start-select') === '15:00'
      && valueOf(d, 'schedule-period-2-off-select') === '16:00',
      [valueOf(d, 'schedule-period-2-start-select'), valueOf(d, 'schedule-period-2-off-select')]);

    // 07:00 falls inside the first period as the test has edited it
    // (06:30–08:30), so Add should begin where that period ends.
    dom.window.__now = new dom.window.Date(2026, 9, 24, 7, 0, 0).getTime();
    d.getElementById('schedule-add-btn').click();
    for (let i = 0; i < 20; i++) {
      if (d.getElementById('schedule-period-3-start-select')) break;
      await sleep(150);
    }
    check('with a period running, a new period starts where it ends (07:00 -> 08:30)',
      valueOf(d, 'schedule-period-3-start-select') === '08:30'
      && valueOf(d, 'schedule-period-3-off-select') === '09:30',
      [valueOf(d, 'schedule-period-3-start-select'), valueOf(d, 'schedule-period-3-off-select')]);

    d.getElementById('schedule-period-3-delete').click();
    for (let i = 0; i < 20; i++) {
      if (!d.getElementById('schedule-period-3-start-select')) break;
      await sleep(150);
    }
    check('the extra period is deleted again', !d.getElementById('schedule-period-3-start-select'));

    await choose(dom, 'schedule-period-2-start-select', '09:00');
    check('until its stop is picked, the stop tracks the start by an hour',
      valueOf(d, 'schedule-period-2-off-select') === '10:00', valueOf(d, 'schedule-period-2-off-select'));

    await choose(dom, 'schedule-period-2-off-select', '11:30');
    await choose(dom, 'schedule-period-2-start-select', '08:00');
    check('once picked, the chosen duration travels with the start (08:00–10:30)',
      valueOf(d, 'schedule-period-2-off-select') === '10:30', valueOf(d, 'schedule-period-2-off-select'));

    console.log('\n== saving ==');
    d.getElementById('schedule-save-btn').click();
    const out = () => d.getElementById('out').textContent;
    for (let i = 0; i < SETTLE_MS / 150; i++) {
      if (out().includes('__DONE__')) break;
      await sleep(150);
    }
    const text = out().replace('__DONE__', '');
    if (!text) throw new Error('the sheet never replied. console:\n' + lines.join('\n'));
    const reply = JSON.parse(text);

    check('the reply is a save', reply.cancelled === 'no', reply.cancelled);
    const periods = reply.profiles[0].rooms.Kitchen.periods;
    check('the saved periods are sorted by start',
      periods.map(p => p.on).join(',') === '06:30,08:00,20:00', periods.map(p => p.on));
    check('the saved on/off/temp values are the ones on screen',
      periods[0].on === '06:30' && periods[0].off === '08:30' && periods[0].temp === '21.0'
      && periods[1].on === '08:00' && periods[1].off === '10:30' && periods[1].temp === '21.0'
      && periods[2].on === '20:00' && periods[2].off === '00:30' && periods[2].temp === '22.0',
      periods);
    check('the editing-only offAuto flag is not saved',
      periods.every(p => !('offAuto' in p)), periods);
    check('the other profile is untouched',
      JSON.stringify(reply.profiles[1]) === JSON.stringify(FIXTURE.profiles[1]),
      reply.profiles[1]);
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
