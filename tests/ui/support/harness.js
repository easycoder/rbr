// harness.js — everything a UI spec needs to get the real page running with a
// scripted controller.
//
//   const { openApp, pushMap, sentText } = require('./support/harness');
//
// openApp() routes the two CDN scripts and installs the MQTT stub, then waits
// until the shell has connected. It does NOT push a map: the spec decides what
// the controller says, and when.
//
// The AllSpeak runtime is fetched once per worker from the URL new-ui/index.html
// names — the same rule tests/pwa-compile-check.js follows, so the suite tests
// the pinned build rather than a copy that can drift. It is then served through
// page.route, so the run itself needs no network.

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..', '..');
const UI = path.join(ROOT, 'new-ui');

let runtimePromise = null;

// The pin lives in index.html; never hard-code it here.
function runtimeUrl() {
  const html = fs.readFileSync(path.join(UI, 'index.html'), 'utf8');
  const m = /<script[^>]+src=['"]([^'"]*allspeak[^'"]*\.js[^'"]*)['"]/i.exec(html);
  if (!m) throw new Error('new-ui/index.html names no allspeak runtime');
  return new URL(m[1], 'https://allspeak.ai/').href;
}

function getRuntime() {
  if (!runtimePromise) {
    runtimePromise = (async () => {
      const url = runtimeUrl();
      const res = await fetch(url);
      if (!res.ok) throw new Error(`could not fetch the AllSpeak runtime at ${url} (${res.status})`);
      return { url, body: await res.text() };
    })();
  }
  return runtimePromise;
}

const MAC = '00:11:22:33:44:55';

function stubSource(mac) {
  const source = fs.readFileSync(path.join(__dirname, 'browser-stub.js'), 'utf8');
  return source.replaceAll('__RBR_TEST_MAC__', JSON.stringify(mac));
}

// Install routes and the stub, load the page, wait for the shell to get as far
// as the caller needs.
//
// `demo: true` produces the no-credentials path: credentials.json answers with
// nothing, no MAC is stored, and the shell renders demo-map.json and opens the
// About sheet. That path never connects, so there is no `connected` flag to
// wait for; the room list appearing is the signal instead.
async function openPage(page, options) {
  const demo = !!(options && options.demo);
  const runtime = await getRuntime();

  // The page names both CDN scripts; neither should be allowed through.
  await page.route('**/dist/allspeak.js*', route => route.fulfill({
    status: 200,
    contentType: 'text/javascript; charset=utf-8',
    body: runtime.body,
  }));
  await page.route('**/mqtt.min.js*', route => route.fulfill({
    status: 200,
    contentType: 'text/javascript; charset=utf-8',
    body: '/* MQTT client is stubbed by tests/ui/support/browser-stub.js */',
  }));

  if (demo) {
    // The suite's server vends a fake broker for the normal path; demo mode
    // has to be given nothing, or the shell would connect instead.
    await page.route('**/new-ui/credentials.json*', route => route.fulfill({
      status: 200,
      contentType: 'application/json; charset=utf-8',
      body: '{}',
    }));
  }

  await page.addInitScript({ content: stubSource(demo ? '' : MAC) });
  await page.goto('/new-ui/index.html');

  if (demo) {
    await page.waitForFunction(
      () => !!document.getElementById('room-0-name') && !!document.getElementById('sheet-title'),
      null,
      { timeout: 30000 });
    return;
  }

  // The shell reaches Connected from `on mqtt connect`, then sends its first
  // map request. Waiting for the flag (not a fixed delay) also proves the
  // credentials path was taken rather than demo mode.
  await page.waitForFunction(() => !!window.__rbr && window.__rbr.connected === true, null, { timeout: 30000 });
}

async function openApp(page) {
  return openPage(page, { demo: false });
}

async function openDemo(page) {
  return openPage(page, { demo: true });
}

async function pushMap(page, map) {
  await page.evaluate(m => window.__rbr.pushMap(m), map);
}

async function pushRaw(page, payload) {
  await page.evaluate(p => window.__rbr.pushRaw(p), payload);
}

// Every payload the UI published, decoded and joined. The runtime chunks large
// requests and prefixes each with `!last!` / `!part!`; the header is stripped so
// a spec can assert on the JSON underneath.
async function sentText(page) {
  return page.evaluate(() => window.__rbr.messages().join('\n'));
}

// The outbound envelopes, parsed. Each is `{sender, action, message}`; for an
// `uirequest`, `message` is the JSON text of the request itself.
async function sentRequests(page) {
  return page.evaluate(() => window.__rbr.messages().map(text => {
    try { return JSON.parse(text); } catch (e) { return null; }
  }).filter(Boolean));
}

// The newest request whose Action matches (`Update Profiles`, etc.), with the
// nested `message` string parsed, or null if the UI has not sent one yet.
async function lastRequest(page, action) {
  const sent = await sentRequests(page);
  for (let i = sent.length - 1; i >= 0; i--) {
    let message = sent[i].message;
    if (typeof message === 'string') {
      try { message = JSON.parse(message); } catch (e) { continue; }
    }
    if (message && (message.Action === action || message.action === action)) return message;
  }
  return null;
}

// The home screen is built asynchronously after the first map. The last thing
// BuildHomeScreen renders is the sheet chrome, and every sheet handler returns
// early until then, so specs that click through to a sheet wait for this.
async function waitForHome(page) {
  await page.waitForFunction(() => !!document.getElementById('special-time-sheet'), null, { timeout: 30000 });
}

// The three sheet entry points the shell actually uses.
async function openSchedule(page, roomIndex) {
  await page.locator(`#room-${roomIndex}-rest`).click();
  await page.locator(`#room-${roomIndex}-edit-schedule`).click();
  await page.waitForSelector('#schedule-editor-sheet', { state: 'visible', timeout: 15000 });
}

async function openProfileSheet(page) {
  await page.locator('#summary-profile-pill').click();
  await page.waitForSelector('#profile-sheet', { state: 'visible', timeout: 15000 });
}

async function openDeviceEditor(page) {
  await page.locator('#top-bar-menu-btn').click();
  await page.locator('#menu-row-devices').click();
  await page.waitForSelector('#device-editor-sheet', { state: 'visible', timeout: 15000 });
}

// Native prompt/confirm/alert, answered from a mutable object the spec sets.
// Playwright dismisses unhandled dialogs, which would silently turn a rename
// into a cancel.
function answerDialogs(page) {
  const answers = { prompt: null, confirm: true };
  page.on('dialog', async dialog => {
    if (dialog.type() === 'prompt') {
      await dialog.accept(answers.prompt === null ? undefined : answers.prompt);
    } else if (dialog.type() === 'confirm') {
      if (answers.confirm) await dialog.accept();
      else await dialog.dismiss();
    } else {
      await dialog.accept();
    }
  });
  return answers;
}

module.exports = {
  openApp,
  openDemo,
  pushMap,
  pushRaw,
  sentText,
  sentRequests,
  lastRequest,
  waitForHome,
  openSchedule,
  openProfileSheet,
  openDeviceEditor,
  answerDialogs,
  runtimeUrl,
  MAC,
};
