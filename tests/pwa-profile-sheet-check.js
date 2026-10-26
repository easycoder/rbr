// pwa-profile-sheet-check.js — drives the Profile sheet in the real runtime and
// checks what a rename and a delete do to the calendar.
//
//   node tests/pwa-profile-sheet-check.js
//
// Why this exists. The calendar stores profile *names* — `calendar-data[i]`
// holds a string — while the profile list stores the profiles themselves. A
// rename that changes only `profiles[i].name` therefore leaves every day that
// referred to the old name pointing at nothing. Both the controller and the
// page resolve names by lookup and, when a name does not resolve, fall back to
// the selected profile *silently*. On 2026-10-26 that read as "the calendar is
// being ignored": the weekday profile had been renamed "Weekday", the Mon–Fri
// calendar entries still said "Monday-Friday", and the first weekday morning
// ran "All Off" (no heat). A compile check cannot see it; no controller unit
// test can see it either. So this loads the real module against a map built
// here, renames and deletes through the sheet's own buttons, and reads the
// reply the shell would send to the controller.

const http = require('http');
const fs = require('fs');
const path = require('path');
const { JSDOM, VirtualConsole } = require('jsdom');

const ROOT = path.join(__dirname, '..');
const UI = path.join(ROOT, 'new-ui');
const MODULE = 'profile-sheet.allspeak';
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

// Monday-first, as the controller indexes it (Monday=0). The names are the
// live system's: the profile is "Weekday", while the calendar still holds the
// old name "Monday-Friday" — the state the fault left behind.
const PROFILES = [
  { name: 'Weekday', rooms: {} },
  { name: 'Weekend', rooms: {} },
  { name: 'All Off', rooms: {} },
];

function calendar(firstFive) {
  return [
    { 'day0-profile': firstFive }, { 'day1-profile': firstFive },
    { 'day2-profile': firstFive }, { 'day3-profile': firstFive },
    { 'day4-profile': firstFive },
    { 'day5-profile': 'Weekend' }, { 'day6-profile': 'Weekend' },
  ];
}

function fixture(kind) {
  return {
    profiles: JSON.parse(JSON.stringify(PROFILES)),
    activeProfileName: 'All Off',
    calendarOn: 'on',
    calendarData: calendar(kind === 'stale' ? 'Monday-Friday' : 'Weekday'),
  };
}

let ACTIVE_FIXTURE = fixture('ok');

// A page that loads one runtime + the module, sends the open message the shell
// sends, and parks until the sheet replies.
function checkPage(runtimePath) {
  return `<!DOCTYPE html><html><head><meta charset="UTF-8">
<script type='text/javascript' src='${runtimePath}'></script>
<style>#out{white-space:pre}</style>
</head><body><div id="app"></div><div id="sheet-content"></div><div id="out"></div>
<pre id="allspeak-script" style="display:none">
    !   Profile-sheet check
        script Check

        variable Source
        variable OpenMsg
        variable Reply
        variable FixtureText
        variable FixtureMap
        variable ReplyText

        module ProfileSheetModule

        div Out
        attach Out to \`out\`

        rest get Source from \`resources/allspeak/${MODULE}?v=\` cat now
        run Source as ProfileSheetModule

        rest get FixtureText from \`/__fixture.json?v=\` cat now
        put json FixtureText into FixtureMap

        put \`{}\` into OpenMsg
        set property \`profiles\` of OpenMsg to property \`profiles\` of FixtureMap
        set property \`activeProfileName\` of OpenMsg to property \`activeProfileName\` of FixtureMap
        set property \`calendarOn\` of OpenMsg to property \`calendarOn\` of FixtureMap
        set property \`calendarData\` of OpenMsg to property \`calendarData\` of FixtureMap

        send OpenMsg to ProfileSheetModule and assign reply to Reply

        put the json of Reply into ReplyText
        set the content of Out to ReplyText cat \`__DONE__\`
</pre></body></html>`;
}

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
        return res.end(JSON.stringify(ACTIVE_FIXTURE));
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

// Open the sheet with `kind`'s fixture, do something with it, and return the
// module's reply plus whatever the act measured in the DOM.
async function session(port, kind, act) {
  ACTIVE_FIXTURE = fixture(kind);
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
  const dayText = id => {
    const el = d.getElementById(id);
    return el ? el.textContent : '(no element #' + id + ')';
  };
  for (let i = 0; i < SETTLE_MS / 150; i++) {
    if (d.getElementById('profile-sheet')) break;
    await sleep(150);
  }
  if (!d.getElementById('profile-sheet')) {
    dom.window.close();
    throw new Error('the module never rendered its sheet. console:\n' + lines.join('\n'));
  }
  await sleep(400);
  const seen = await act({ d, w: dom.window, click, dayText });
  const out = () => d.getElementById('out').textContent;
  for (let i = 0; i < SETTLE_MS / 150; i++) {
    if (out().includes('__DONE__')) break;
    await sleep(150);
  }
  const text = out().replace('__DONE__', '');
  dom.window.close();
  if (!text) throw new Error('the sheet never replied. console:\n' + lines.join('\n'));
  return { reply: JSON.parse(text), lines, seen };
}

function names(profiles) {
  return profiles.map(p => p.name);
}

function dayNames(cal) {
  return cal.map((entry, i) => entry['day' + i + '-profile']);
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

  // ---- a rename carries the calendar names --------------------------------
  console.log('\n== renaming a profile updates the days that name it ==');
  {
    const { reply, seen } = await session(port, 'ok', async ({ w, click, dayText }) => {
      w.__answers.prompt = 'Weekday 2';
      click('profile-row-0-rename');
      await sleep(400);
      const before = { mon: dayText('calendar-mon-profile'), sun: dayText('calendar-sun-profile') };
      click('profile-save-btn');
      return before;
    });
    check('the reply is a save', reply.cancelled === 'no', reply.cancelled);
    check('the profile was renamed', names(reply.profiles)[0] === 'Weekday 2', names(reply.profiles));
    check('the other profiles are untouched',
      JSON.stringify(reply.profiles.slice(1)) === JSON.stringify(PROFILES.slice(1)),
      reply.profiles.slice(1));
    check('Mon–Fri followed the rename',
      JSON.stringify(dayNames(reply.calendarData).slice(0, 5)) === JSON.stringify(Array(5).fill('Weekday 2')),
      dayNames(reply.calendarData));
    check('Sat–Sun still name Weekend',
      JSON.stringify(dayNames(reply.calendarData).slice(5)) === JSON.stringify(['Weekend', 'Weekend']),
      dayNames(reply.calendarData));
    check('the day rows repainted before Save', seen.mon === 'Weekday 2' && seen.sun === 'Weekend', seen);
    check('the active profile is still All Off', reply.activeIdx === 2, reply.activeIdx);
  }

  // ---- a duplicate name is refused ---------------------------------------
  console.log('\n== renaming onto a name already in use ==');
  {
    const { reply, lines } = await session(port, 'ok', async ({ w, click }) => {
      w.__answers.prompt = 'Weekend';
      click('profile-row-0-rename');
      await sleep(400);
      click('profile-save-btn');
    });
    check('the profile names are unchanged', JSON.stringify(names(reply.profiles)) === JSON.stringify(names(PROFILES)), names(reply.profiles));
    check('the calendar is unchanged',
      JSON.stringify(dayNames(reply.calendarData)) === JSON.stringify(dayNames(fixture('ok').calendarData)),
      dayNames(reply.calendarData));
    check('the user is told why', lines.some(l => /already a profile called/.test(l)), lines.slice(-3));
  }

  // ---- a delete clears the days that named it ----------------------------
  console.log('\n== deleting a profile clears its calendar days ==');
  {
    const { reply, seen } = await session(port, 'ok', async ({ w, click, dayText }) => {
      w.__answers.confirm = true;
      click('profile-row-0-delete');
      await sleep(400);
      const before = { mon: dayText('calendar-mon-profile'), sun: dayText('calendar-sun-profile') };
      click('profile-save-btn');
      return before;
    });
    check('the reply is a save', reply.cancelled === 'no', reply.cancelled);
    check('the profile is gone', JSON.stringify(names(reply.profiles)) === JSON.stringify(['Weekend', 'All Off']), names(reply.profiles));
    check('its days are cleared',
      dayNames(reply.calendarData).slice(0, 5).every(n => n === undefined || n === ''),
      dayNames(reply.calendarData));
    check('the other days are untouched',
      JSON.stringify(dayNames(reply.calendarData).slice(5)) === JSON.stringify(['Weekend', 'Weekend']),
      dayNames(reply.calendarData));
    check('the active index followed the remaining profile', reply.activeIdx === 1, reply.activeIdx);
    check('the day rows repainted before Save', seen.mon === '—' && seen.sun === 'Weekend', seen);
  }

  // ---- a stale name looks wrong on sight ---------------------------------
  console.log('\n== a day naming a profile that does not exist is marked ==');
  {
    const { reply, seen } = await session(port, 'stale', async ({ click, dayText }) => {
      const before = { mon: dayText('calendar-mon-profile'), sat: dayText('calendar-sat-profile') };
      click('profile-cancel-btn');
      return before;
    });
    check('the reply is a cancel', reply.cancelled === 'yes', reply.cancelled);
    check('the missing name is flagged', seen.mon === 'Monday-Friday (missing)', seen);
    check('a resolvable name is not', seen.sat === 'Weekend', seen);
  }

  server.close();
  console.log(`\n${pass} passed, ${fail} failed`);
  if (fail) {
    console.log('\nFailures: ' + failures.join(', '));
    process.exit(1);
  }
}

main().catch(e => { console.error(e); process.exit(1); });
