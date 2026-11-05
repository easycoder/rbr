# UI tests

Playwright drives the real PWA in Chromium against a scripted controller.

```bash
npx playwright install chromium   # once per machine or CI runner
npm run test:ui
```

The run needs no broker, no controller, no PHP and no `allspeak` CLI. It needs
network once, for the AllSpeak runtime that `new-ui/index.html` pins; the
harness fetches that URL and serves it through `page.route`, so the browser run
itself is offline.

## Where the controller went

The controller's only contribution to a page is the map it publishes. A spec
supplies that map as a fixture, in the controller's shape (`fixtures/map.json`,
and `new-ui/demo-map.json` for a fuller one), and pushes it through
`window.__rbr.pushMap()`. `window.mqtt` is replaced before the page's scripts
run by `support/browser-stub.js`; the CDN MQTT client is routed to an empty body
so it cannot take the name back. `serve.js` vends a fake `credentials.json` from
memory, which keeps the shell out of demo mode without writing a file into
`new-ui/`.

The AllSpeak runtime is still the real pinned build: `support/harness.js` reads
its URL from `index.html`, the same rule `tests/pwa-compile-check.js` follows.
So this suite tests the page that ships, not a copy that can drift.

## What the stub can do

Everything a controller does, including the wrong things:

| call | what it simulates |
| --- | --- |
| `pushMap(map)` | a normal full map |
| `pushRaw(payload)` | a malformed, truncated or unexpected payload |
| `emit('error', err)` | a broker/client error |
| `disconnect()` | the socket closing (the UI should notice, not hang) |
| `connectAgain()` | a reconnect event |
| `failPublish = true` | a publish that never gets an ack |

Outgoing traffic is recorded in `window.__rbr.messages()`; `sentText(page)`
returns the reassembled payloads and `lastRequest(page, 'Update Profiles')`
returns the newest parsed request. That replaces `page.waitForRequest` — there
is no HTTP request to watch. The runtime chunks anything over one publish
(`!part!i N … !last!N …`), so the stub reassembles before the harness parses;
assert against the request, not the raw frames.

## What to provoke

The shell already has explicit defences, so each is worth a spec:

- **Map shape.** Empty heartbeat payload; `profiles` missing or null; `rooms`
  missing; a profile naming a room that is not in `rooms`; duplicate room names;
  wrong types (`temperature` as text, unknown `relay`/`status`); a very large
  map. `OnMapReceived` validates before replacing `Map`, and
  `tests/pwa-profile-sheet-check.js` already pins the "(missing)" day case.
- **Sequence.** A map during `BuildHomeScreen`; a map while a module editor
  holds the runtime's one reply slot (the 2026-10-24 bug); two maps back to
  back; heartbeat-only replies; a map before the subscribe returns; a
  disconnect mid-edit and a reconnect with a stale map.
- **Silence and transport.** No reply at all (the first-map watchdog reloads
  after 30s and keeps retrying); `MQTT error`; a socket that dies without a
  close event (the poll staleness check).
- **Boot.** Neither CDN reachable (the boot guard's "Trying to reach Room By
  Room…" path), which is a pure `page.route` abort in this suite.

Two limits are worth stating. Fixtures encode what the UI *expects*, so they
cannot discover a shape the controller invents — re-capture a real payload into
`fixtures/` when the map format changes, and let `AI/MAP_FORMAT.md` be the
reference. And this suite never proves the controller's own behaviour; that
stays in `tests/unit/` and, for a true end-to-end run, in an optional smoke test
against a real broker and controller.

## Layout

```
playwright.config.js          one worker, phone viewport, service worker blocked
tests/ui/serve.js             static server + fake credentials.json
tests/ui/support/harness.js   routes, runtime pin, openApp/pushMap/sentText
tests/ui/support/browser-stub.js  the scripted MQTT client
tests/ui/fixtures/map.json    the default controller reply
tests/ui/smoke.spec.js        harness check: boot, `first` request, render
tests/ui/demo-mode.spec.js    the no-credentials path and its baked map
tests/ui/schedule.spec.js     period start moves, stop follows, saved request
tests/ui/profiles.spec.js     a rename carries the calendar's day names
tests/ui/devices.spec.js      a room rename keeps that room's own wiring
tests/ui/map-mid-edit.spec.js a map pushed mid-edit is held, then applied
```
