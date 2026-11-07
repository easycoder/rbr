# UI testing strategy

> **Audience:** developer, maintainer · **Status:** draft · **Last verified:** 2026-11-05 · **See also:** [Architecture](../technical/01-architecture.md) · [What RBR is](../concept/02-what-rbr-is.md)

## What this page is

This is the starting point for how the RBR interface is tested, and it will grow into the full UI test strategy; at present it records the two layers that exist, where they run, what they deliberately do not cover, and why the split is where it is. The engineering detail stays with the code: `tests/ui/README.md`, `tools/rbr-studio/README.md` and `tools/rbr-studio/docs/SPEC.md`.

## Two layers

| Layer | Where it lives | What question it answers |
|---|---|---|
| **Browser regression suite** | `tests/ui/` | Does the page that ships still boot, render and send the right requests when the controller sends a given map? |
| **RBR Studio** | `tools/rbr-studio/` | Can a described sequence of controller events and user actions be run against the page, step by step, with a readable result? |

The regression suite is the gate: it is small, deterministic and can run on every change. RBR Studio is the authoring and investigation tool: it makes a sequence visible, executable and easy to vary. Neither replaces the other, and a scenario that is useful in the studio should be distilled into a suite spec when it becomes a fixed expectation.

## Where the tests run

Both layers run on a development machine or a CI runner, never on a controller. The page is served statically, the controller's map arrives as a fixture or a local snapshot, and the browser's MQTT client is replaced by a scripted stub before the page's own scripts run. No broker, no controller, no PHP and no Zigbee hardware are involved.

The AllSpeak runtime is still the real pinned build: the harness reads its URL from `new-ui/index.html`, so the tests exercise the page that ships rather than a fresh copy of the language. `tests/ui` fetches the runtime once and serves it through `page.route`; the run itself is then offline.

## What the browser suite covers

The suite drives the real PWA in Chromium at a phone viewport. It covers booting from a controller map, demo mode, the schedule editor, the profile sheet, the device editor and a map push arriving while an editor is open. It can also push malformed or unexpected payloads, drop and restore the connection and make publishes fail; those are the controller's failure modes, not the happy path.

Requests are checked as the page would actually send them, including the runtime's chunked message format. Each test states its expectation in the page's own vocabulary — the room card, the summary, the sheet — rather than in pixels.

## What the scenario layer covers

The runner in `tools/rbr-studio/` uses the same real page and a stubbed controller, but its unit is a scenario: a timed sequence of controller events, user actions, expectations and wire checks. It advances a virtual clock, resolves semantic targets such as `room.Office.advance` against the map in use, and records every step with its result, a wire log and, on failure, a screenshot and a Playwright trace.

Scenarios can be built from the two worked examples, from a snapshot of a real system map, or from an AI draft that is validated before it is listed. The point is to make a suspected interaction reproducible, not to replace the regression suite.

## What is not covered

The tests do **not** prove the controller's heating logic, the real broker and its TLS/WebSocket path, the PHP endpoints, Zigbee pairing or the behaviour of physical devices. They do not cover the desktop app, which is secondary, and they do not yet include visual-regression or layout/geometry assertions. The browser suite is Chromium at one viewport; cross-browser and accessibility checks are still to come.

The stub is a scripted map, not a second implementation of the controller. If a scenario expects the interface to change at a schedule boundary, the controller event that causes it must be an explicit step; the runner must not infer it from the same schedule logic the page uses.

## Running them

The browser suite needs Node and Chromium; it has no Python or controller dependency:

```bash
npx playwright install chromium
npm run test:ui
```

The scenario layer needs Python and Playwright; the shell is AllSpeak/PySide6:

```bash
cd tools/rbr-studio
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
.venv/bin/python -m scenario_runner --scenario docs/examples/advance.json
allspeak studio.allspeak
```

A real system map can be snapshotted into the ignored local fixtures with `python3 snapshot-map.py`; the scenario library and the AI authoring path are described in the studio's README.

## What comes next

The full strategy will add the policy for what belongs in the suite versus a scenario, the CI job and its browser install, visual and geometry checks for the layout questions that text assertions cannot settle, a record-from-live-controller mode, cross-browser and accessibility coverage, and the scenario library as a maintained set of regression scenarios. This page will link to those decisions as they are made rather than growing into a second copy of the engineering notes.
