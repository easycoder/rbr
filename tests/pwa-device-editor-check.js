// pwa-device-editor-check.js — drives the Devices sheet in the real runtime and
// checks what a rename actually does.
//
//   node tests/pwa-device-editor-check.js
//
// Why this exists. The Devices sheet edits the shared room list, and a rename
// touches three things at once: the identity record, that room's state key in
// every profile, and nothing else. On 2026-10-17 it touched the wrong record —
// renaming one room wrote another room's wiring over it — because the routine
// held the room in a shared scratch variable and then called a helper that
// looped over all of them (see DIFF.md). A compile check cannot see that, and a
// unit test of the controller cannot see it either: the fault is in the page.
//
// So this loads the real module, in the real runtime, against a small map built
// here rather than read from the repository, opens the sheet the way the shell
// does, taps the picker and the keyboard, and reads what comes back. It needs
// no broker, no controller and no browser: jsdom plus the runtime is enough.
//
// The assertions deliberately compare the *whole* identity record and the whole
// list of names. The bug survived a harness that checked the two things a
// rename is "about" — the new name and the moved state key — so checking only
// what changed is what this test is built not to do.

const http = require('http');
const fs = require('fs');
const path = require('path');
const { JSDOM, VirtualConsole } = require('jsdom');

const ROOT = path.join(__dirname, '..');
const UI = path.join(ROOT, 'new-ui');
const MODULE = 'device-editor.allspeak';
const MODULE_FILE = path.join(UI, 'resources', 'allspeak', MODULE);
const SETTLE_MS = 25000;

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

// A small map in the shared-room-list shape. The outside sensor sits last with
// no relays, and the room at index 2 has wiring of its own — which is the point:
// the bug put the outside sensor's wiring there.
const FIXTURE = {
  name: 'Check home',
  request: 'Request-relay',
  profile: 0,
  calendar: 'off',
  'calendar-data': [],
  rooms: [
    { name: 'Kitchen', relays: ['Kitchen-relay'], sensor: 'Kitchen-thermometer', linked: 'yes',
      protect: 'no', relayfails: [0], temperature: 2000, humidity: 50, battery: 90,
      sensorAge: 60000, timestamp: 1, status: 'good', statusMessage: '', relay: 'off' },
    { name: 'Hall', relays: ['Hall-relay'], sensor: 'Hall-thermometer', linked: 'yes',
      protect: 'no', relayfails: [0], temperature: 1900, humidity: 52, battery: 80,
      sensorAge: 60000, timestamp: 1, status: 'good', statusMessage: '', relay: 'off' },
    { name: 'Study', relays: ['Study-relay'], sensor: 'Study-thermometer', linked: 'yes',
      protect: 'no', relayfails: [0], temperature: 1800, humidity: 48, battery: 70,
      sensorAge: 60000, timestamp: 1, status: 'good', statusMessage: '', relay: 'off' },
    { name: 'Lounge', relays: ['Lounge-relays'], sensor: 'Lounge-thermometer', linked: 'no',
      protect: 'no', relayfails: [0], temperature: 2100, humidity: 45, battery: 60,
      sensorAge: 60000, timestamp: 1, status: 'good', statusMessage: '', relay: 'off' },
    { name: 'Outside', relays: [], sensor: 'Outside-thermometer', linked: 'yes',
      protect: 'yes', ptemp: '-1.5', relayfails: [0], temperature: 900, humidity: 70,
      battery: 90, sensorAge: 60000, timestamp: 1, status: 'good', statusMessage: '', relay: 'off' },
  ],
  profiles: [
    { name: 'Weekday', rooms: {} },
    { name: 'Weekend', rooms: {} },
  ],
};

// Every room has schedule state in every profile, keyed by name.
FIXTURE.profiles.forEach(p => {
  FIXTURE.rooms.forEach(r => {
    p.rooms[r.name] = {
      mode: r.relays.length ? 'timed' : 'off',
      target: 20,
      periods: r.relays.length ? [{ on: '06:00', off: '08:00', temp: '21.0' }] : [],
      events: [],
      advance: '-',
    };
  });
});

const IDENTITY_FIELDS = ['relays', 'sensor', 'linked', 'protect', 'ptemp'];

// A page that loads one runtime + the module, sends the open message the shell
// sends, and parks until the sheet replies.
function checkPage(runtimePath) {
  return `<!DOCTYPE html><html><head><meta charset="UTF-8">
<script type='text/javascript' src='${runtimePath}'></script>
<style>#out{white-space:pre}</style>
</head><body><div id="app"></div><div id="sheet-content"></div><div id="out"></div>
<pre id="allspeak-script" style="display:none">
    !   Device-editor check
        script Check

        variable Source
        variable OpenMsg
        variable Reply
        variable FixtureText
        variable FixtureMap
        variable ReplyText

        module DeviceEditorModule

        div Out
        attach Out to \`out\`

        rest get Source from \`resources/allspeak/${MODULE}?v=\` cat now
        run Source as DeviceEditorModule

        rest get FixtureText from \`/__fixture.json?v=\` cat now
        put json FixtureText into FixtureMap

        put \`{}\` into OpenMsg
        set property \`rooms\` of OpenMsg to property \`rooms\` of FixtureMap
        set property \`profiles\` of OpenMsg to property \`profiles\` of FixtureMap
        set property \`requestRelay\` of OpenMsg to property \`request\` of FixtureMap

        send OpenMsg to DeviceEditorModule and assign reply to Reply

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

// Open the sheet, do something with it, and return the module's reply.
async function session(port, act) {
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
      window.__answers = { prompt: null, confirm: true };
      window.alert = m => lines.push('alert: ' + m);
      window.prompt = () => window.__answers.prompt;
      window.confirm = () => window.__answers.confirm;
    }
  });
  const d = dom.window.document;
  const click = id => {
    const el = d.getElementById(id);
    if (!el) throw new Error('no element #' + id + ' — the sheet did not render');
    el.click();
  };
  for (let i = 0; i < SETTLE_MS / 150; i++) {
    if (d.getElementById('device-editor-sheet')) break;
    await sleep(150);
  }
  if (!d.getElementById('device-editor-sheet')) {
    dom.window.close();
    throw new Error('the module never rendered its sheet. console:\n' + lines.join('\n'));
  }
  await sleep(400);
  await act({ d, w: dom.window, click });
  const out = () => d.getElementById('out').textContent;
  for (let i = 0; i < SETTLE_MS / 150; i++) {
    if (out().includes('__DONE__')) break;
    await sleep(150);
  }
  const text = out().replace('__DONE__', '');
  dom.window.close();
  if (!text) throw new Error('the sheet never replied. console:\n' + lines.join('\n'));
  return { reply: JSON.parse(text), lines };
}

// Rename the room at identity index `row`, which is not the room the form was
// loaded with — the state the bug needed.
async function renameRow(port, row, to) {
  return session(port, async ({ w, click }) => {
    w.__answers.prompt = to;
    click('device-editor-room-pill');          // open the picker
    await sleep(300);
    click(`device-room-edit-${row}-edit`);     // its pencil
    await sleep(400);
    click('device-editor-save-btn');
  });
}

function wiring(rooms) {
  return rooms.map(r => {
    const out = { name: r.name };
    IDENTITY_FIELDS.forEach(f => { if (f in r) out[f] = r[f]; });
    return out;
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
  if (!fs.existsSync(MODULE_FILE)) {
    console.log(`FAIL: ${MODULE} is missing`);
    process.exit(1);
  }

  const server = await serve(body);
  const port = server.address().port;

  // ---- a rename keeps the room's own wiring -------------------------------
  console.log('\n== renaming a room that is not the selected one ==');
  {
    const { reply } = await renameRow(port, 2, 'Study Two');
    const before = wiring(FIXTURE.rooms);
    const after = wiring(reply.rooms);
    check('the reply is a save', reply.cancelled === 'no', reply.cancelled);
    check('the room was renamed', after[2].name === 'Study Two', after[2].name);
    check('it kept its own relays and thermometer',
      JSON.stringify(after[2]) === JSON.stringify({ ...before[2], name: 'Study Two' }),
      { expected: { ...before[2], name: 'Study Two' }, got: after[2] });
    check('no other room was rewritten',
      JSON.stringify(after.filter((_, i) => i !== 2)) === JSON.stringify(before.filter((_, i) => i !== 2)),
      after);
    check('the room count is unchanged', reply.rooms.length === FIXTURE.rooms.length, reply.rooms.length);
    check('every profile moved the state key and nothing else', reply.profiles.every(p => {
      const keys = Object.keys(p.rooms);
      return keys.length === FIXTURE.rooms.length && keys.includes('Study Two') && !keys.includes('Study');
    }), reply.profiles.map(p => Object.keys(p.rooms)));
    check('the state itself travelled',
      JSON.stringify(reply.profiles[0].rooms['Study Two']) === JSON.stringify(FIXTURE.profiles[0].rooms.Study),
      reply.profiles[0].rooms['Study Two']);
  }

  // ---- a duplicate name is refused, and refuses cleanly -------------------
  console.log('\n== renaming onto a name already in use ==');
  {
    const { reply, lines } = await renameRow(port, 2, 'Kitchen');
    check('the identity list is untouched',
      JSON.stringify(reply.rooms) === JSON.stringify(FIXTURE.rooms), reply.rooms.map(r => r.name));
    check('the profiles are untouched',
      JSON.stringify(reply.profiles) === JSON.stringify(FIXTURE.profiles));
    check('the user is told why', lines.some(l => /already a room called/.test(l)), lines.slice(-3));
  }

  server.close();
  console.log(`\n${pass} passed, ${fail} failed`);
  if (fail) {
    console.log('\nFailures: ' + failures.join(', '));
    process.exit(1);
  }
}

main().catch(e => { console.error(e); process.exit(1); });
