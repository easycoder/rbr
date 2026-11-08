# RBR Studio — specification

Status: design, 2026-11-05. The v0 Python runner in `scenario_runner/`
implements validation, the controller stub, semantic targets, the virtual
clock and artefacts, and runs both reference scenarios. The AllSpeak/PySide
shell (`studio.allspeak`) uses the graphics `table`, `logpane`, `panes` and
`tabs` and the `process` domain; Run is wired to `scenario_runner`, and Demo
adds headed, paced playback with collapsed poll logging.

## 1. Purpose

RBR Studio builds and runs UI test scenarios for Room By Room. A scenario
is a list of things the **controller** does, things the **user** does, and
things the **UI must show**. The studio gives that list a visual editor, a
validator, an AI drafting aid and a runner that reports results step by step.

The two reference scenarios are:

1. **Temperature** — the controller reports Kitchen 18.4 °C at 07:12 and
   18.8 °C at 07:23; the card shows each value.
2. **Advance** — Office is 22.5 °C at 14:40; at 15:00 the user taps Advance;
   the controller holds the advance; at 18:00 it clears it and at 18:30 reports
   21.9 °C. The UI must stop showing the advance and show the new reading.

`docs/examples/delay.json` is a short third example: it demonstrates the `delay` step, which holds a state for the viewer in a paced demo.

The second is the interesting one: it spans hours. The runner therefore owns a
**virtual clock**; a scenario is never bounded by wall-clock time.

### Non-goals

- Not a controller simulator for heating policy. Schedule boundaries, advance
  expiry and relay decisions are scenario steps, not engine magic.
- Not a load or performance tool, and not a runner for the controller's own
  unit tests.
- Not a visual-regression suite. Screenshots are failure evidence; pixel
  comparisons are a later, opt-in assertion.
- Not a recorder yet. Capturing a live controller into a scenario is phase 5.

## 2. Decisions

These are the design's load-bearing choices.

**Scenarios are data, not generated Playwright code.** One generic runner
interprets the scenario. Generating a `.spec.py` per scenario makes the
generated file a second source of truth, makes failures point at code nobody
edited, and turns AI output into executable code. If an executable artefact is
wanted for CI, export a four-line wrapper that loads the JSON and calls the
runner.

**Time is virtual.** `HH:MM` in a scenario is scenario time, not execution
time. The runner installs Playwright's clock before navigation and advances it
between steps. 15:00 → 18:00 costs milliseconds. Execution time exists only as
per-step timeouts.

**Expectations are explicit.** A controller event does not silently imply an
assertion. The builder offers an *Insert expectation* shortcut, but the check
appears as a row the author can see, edit and disable.

**The controller is a map, not a brain.** The runner owns a base map, applies
declared state changes, and pushes **full-map** snapshots, exactly as the real
controller does. It does not decide heating, schedule boundaries or advance
expiry; those transitions are scenario steps. Hidden controller logic makes the
UI's expected result depend on a second implementation of the same rule, which
turns the test into a tautology.

**Targets are semantic.** Scenarios name `room.Office.advance`, not
`#room-2-advance-btn`. Names resolve to rows at run time, so reordering rooms
cannot break a scenario. Raw CSS is an escape hatch, marked fragile.

**The app is AllSpeak/PySide; the runner is Python.** The app follows the
`desktop/` pattern: an `.allspeak` graphics program plus a plugin that registers
custom types and commands. The runner is a plain Python process using
Playwright for Python, launched with `QProcess`, speaking JSON Lines. No Node
dependency, and the same runner works headless in CI or from another tool.

## 3. Architecture

```
┌──────────────────────────────────────────────┐
│ RBR Studio (AllSpeak + PySide6)              │
│  scenario browser · step table · inspector   │
│  validation · log panel · AI draft panel     │
└───────────────┬──────────────────────────────┘
                │ QProcess: JSONL over stdout/stdin
┌───────────────▼──────────────────────────────┐
│ scenario_runner (Python, Playwright)         │
│  schema · step engine · virtual clock        │
│  controller stub · target resolver           │
│  static server · CDN routes · artefact writer│
└───────────────┬──────────────────────────────┘
                │ Chromium
┌───────────────▼──────────────────────────────┐
│ new-ui/index.html (the real PWA)             │
└──────────────────────────────────────────────┘
```

The runner serves the PWA from a checkout (`--repo`, default the repository
containing the studio) and routes the two CDN scripts. The AllSpeak runtime is
fetched once from the URL `new-ui/index.html` names, cached by URL, and served
through `page.route`; the MQTT client is replaced by the stub. No broker,
controller, PHP or internet connection is needed after the first fetch.

A separate process is deliberate:

- Playwright's synchronous API blocks; the Qt event loop must not.
- A runner crash cannot take the editor down.
- The runner is reusable from CI and from other tools.
- The JSONL boundary is the integration surface (`PROTOCOL.md`).

**Why Python and not the existing Node harness.** The studio and its future
plugins are Python; Playwright has a first-class Python binding with clock,
routing and init scripts. Porting the harness (static server, MQTT stub, chunk
reassembly, dialogs) is small. The Node suite in `tests/ui/` remains the
repository's low-level gate for the page; the studio is the authoring and
execution tool. The two reference scenarios are kept as the shared cross-check
between them.

## 4. Scenario model

A scenario is one JSON file, validated by `scenario.schema.json`.

```json
{
  "schemaVersion": 1,
  "name": "Advance holds until the next schedule change",
  "clock": { "start": "2026-11-05T14:30:00", "timeZone": "Europe/London" },
  "home": { "map": "fixtures/home.json", "profile": "Weekday" },
  "rooms": { "office": "Office" },
  "steps": [ ... ]
}
```

- `clock.start` is the scenario's date and time-of-day, with an explicit
  timezone. `HH:MM` step times resolve against that date. DST is a first-class
  case, not an accident of the host machine.
- `home.map` is a path relative to the scenario or an inline object. It is a
  **wire-shaped** map: the controller's reply, including `relaysTotal` and
  `relaysFailed`. A copy of a real system map can be used; `snapshot-map.py`
  reads `map.json` beside the studio, fills those derived fields into
  `fixtures/local/`, which is gitignored because room and device names are
  personal, and the shell's Refresh map reloads it. `home.profile` selects the
  active profile by name (or index).
- `rooms` aliases decouple scenarios from RBR's name-keyed join. Renaming a room
  updates one alias, not every step.
- `defaults` carries `stepTimeoutMs`, `continueOnFailure`, `screenshots` and
  `failOnPageError`.

Every step has `id`, `at`, an optional `note`, `disabled` and `timeoutMs`, plus
exactly one action. A step may also carry `"marker": true`; at most one step in a
scenario may do so. In a demo the steps before that marker run at maximum speed
and the marker and later steps use the selected speed.

| Key | Meaning |
| --- | --- |
| `controller` | change map state and/or push a full map; `raw` sends a malformed payload |
| `ui` | tap, select, fill or scroll a semantic target |
| `expect` | assert DOM state: text, contains, visible, hidden, value, count, geometry |
| `expectWire` | assert the newest outbound request (action and fields) |
| `waitFor` | wait for a DOM condition, bounded |
| `connection` | drop, reconnect, or emit an MQTT error |
| `delay` | hold the current state for real seconds; honoured only in a paced demo (`--speed > 0`), skipped in a normal run; does not advance scenario time |

### Library, groups and batches (v0)

The local library is a directory of group folders under `fixtures/local/scenarios/`; `index.json` records each scenario's display name, group, path and brief path. A `<stem>.brief.md` sits beside its scenario. Selecting a scenario loads its brief, and an edit sends both the current scenario and the current brief to the drafter. New clears the editor; Delete moves the scenario and brief to `.trash`.

Groups are real folders and the shell's group selector filters the scenario list; New group creates an empty folder. A batch is a list of scenario paths in the shell's BATCH panel: add the selected scenario, remove entries, and Run batch. `batch_runner.py` runs each scenario as a normal `scenario_runner` run, sequentially, and writes a record under `fixtures/local/batches/`. Parallel runs and saved named batch definitions are later.

`at` accepts `HH:MM`, `HH:MM:SS` or an ISO date-time. Steps are executed in
file order; `at` may only move forward unless the scenario sets
`allowOutOfOrder`, because a table that reads out of order is almost always a
mistake.

### Controller events

`controller.room` names the room. `controller.set` changes identity fields in
`rooms[]`; `controller.state` changes that room's state in the active profile
(or a named profile via `profile`). A `push` (default true) sends a deep copy of
the whole map, so a reading and a schedule transition can share one row.

```json
{ "id": "s1", "at": "14:40",
  "controller": { "room": "Office", "set": { "temperature": 2250 } } }

{ "id": "s10", "at": "18:00",
  "controller": { "room": "Office",
                  "set": { "temperature": 2250 },
                  "state": { "set": { "advance": "-" } } } }
```

`raw` sends exactly the given text and is how negative scenarios are written:
a truncated map, `profiles: null`, duplicate room names, an unknown relay state.

The runner also implements the **protocol-level** replies any controller gives,
and nothing else:

- `first` → push the current map.
- `refresh` → an empty heartbeat by default, or the full map if the scenario
  says `defaults.refreshReply: "full"`.
- Every poll received is recorded in the wire log, so a scenario can assert the
  UI's cadence.

That heartbeat matters. The UI polls every 10 s and reloads itself if no reply
arrives for 60 s (`MapPollTask`). Fast-forwarding three hours fires ~1,080
polls; if the stub stayed silent the UI would reload mid-scenario. Replying is
protocol behaviour, not controller semantics.

## 5. Controller model boundaries

What is in scope:

- full-map pushes, as the real controller sends;
- protocol replies (`first`, `refresh`);
- the six UI-owned identity fields in `Update Profiles` (`relays`, `sensor`,
  `trv`, `linked`, `relayfails`, `protect`) for wire assertions.

What is deliberately **not** in scope:

- heating decisions, schedule boundaries, boost/advance expiry, sensor
  staleness. If a scenario depends on one, it states the transition:
  "at 18:00, advance cleared, push". That row is the test's oracle.
- hidden "auto-apply the UI request and push" behaviour. The builder can offer
  **Add controller acknowledgement**, which inserts the explicit state change
  and push rows for the author to inspect.

A future `record` mode captures a live controller's pushes and requests into a
scenario. That is the honest answer to fixture drift; it is not needed for v1.

## 6. Targets

Targets are resolved through the RBR plugin's catalogue. Room targets accept
either the room's name or its alias; the resolver finds its index from the
rendered map and then uses `room-<index>-<element>`.

```
summary.title | subtitle | outside | profile | chip
room.<name>.card | name | temp | subline | heating-tag | warn | rest
room.<name>.advance | mode.timed | mode.boost | mode.on | mode.off
room.<name>.target | target.plus | target.minus | boost.30 | boost.1h | boost.2h
room.<name>.schedule | special | override
sheet.root | title | close
schedule.save | cancel | add | profile | period.<i>.start | stop | temp | enabled | delete
profiles.save | cancel | add | row.<name>.label | row.<name>.rename | row.<name>.delete
devices.save | cancel | add | room.<name>.edit | delete | up | down
menu.system | devices | outside | backups
boot.warning
css:<selector>                      fragile; flagged in validation
```

The catalogue is data, generated from the Webson templates and reviewed. A
target that no longer exists is a validation error before the run and a named
failure during it, never a silent skip.

## 7. Execution semantics

1. Validate the scenario (schema, targets, rooms, times, ids, fixture shape).
2. Start the static server for `--repo`; launch Chromium with the scenario's
   viewport, timezone, locale and device scale.
3. `page.clock.install(time=clock.start)` **before** navigation.
4. Route the pinned AllSpeak runtime, the MQTT CDN client (empty body) and the
   fake `credentials.json`; install the MQTT stub; seed `dev-mac`.
5. Navigate, wait for the shell's connect, push the base map.
6. For each step, in order:
   - advance the clock to `at` in 50-second slices, answering each poll;
   - perform the action;
   - for expectations, wait up to `timeoutMs` using locators, never a sleep;
   - emit `step.started` / `step.finished` with expected, actual, artefacts.
7. Stop on the first failure unless `defaults.continueOnFailure`.
8. Write the run directory and emit `run.finished`.

A page error fails the run by default (`failOnPageError`). Console lines are
collected and attached to the step that produced them; a scenario may assert
on them later.

### Time

There are three clocks and they must not be confused:

| Clock | Source | Used for |
| --- | --- | --- |
| scenario time | step `at` | when events happen, what the user sees |
| browser time | Playwright clock | `Date`, timers, the UI's 10 s poll and projections |
| wall time | host | step timeouts and demo `delay` steps |

The runner sets the browser clock from scenario time before each step and never waits for real seconds, except for an explicit `delay` step in a paced demo; a normal run skips it. The UI's own projections (schedule subline,
boost countdown, advance expiry) then change deterministically.

A demo run can opt into **paced time**: `--speed N` advances 10-second virtual
slices with a real sleep proportional to N (1 is real time; 120 turns three
hours into 90 seconds), `--headed` opens the PWA window, and
`--step-pause-ms` holds each passed step for a moment. A `delay` step is real seconds, unscaled; a normal run skips it. `--collapse-polls`
suppresses the per-poll `Requesting map: refresh` events in the live stream and
emits `refresh ×50` summaries plus a final total; the full console remains in
the run's `console.log`. The shell exposes this as its **Demo** button and
speed selector; **Run** stays headless and as fast as possible.

**Clock spike (settled 2026-11-05):** the pinned runtime's `wait N ticks` does
yield to Playwright's clock, but one multi-hour `fastForward` lets the poll run
once and the 60-second staleness watchdog reloads the page; `set_fixed_time`
stalls the deferred work that applies a map. The runner therefore advances in
50-second slices while the stub answers each `refresh` with a heartbeat. Three
hours costs about ten seconds and ~240 polls, and both reference scenarios pass.
Exact 10-second poll cadence is a later, separate mode.

## 8. Run artefacts

Runs are written outside the repository by default (`~/.local/share/rbr-studio/runs/`),
or under a configured directory:

```
runs/2026-11-05T14-30-00-advance/
  scenario.json        snapshot of exactly what ran
  environment.json     app/runner/browser versions, repo path and commit, viewport
  result.json          per-step status, expected/actual, durations
  wire.jsonl           every outbound request and inbound push, reassembled
  console.log
  screenshots/         on failure, and on request
  trace.zip            on failure (Playwright trace)
```

The scenario file is never mutated by a run. Results attach to stable step ids.

## 9. Validation

Authoring-time checks, all reported with a row link:

- schema errors; duplicate step ids; `at` going backwards;
- unknown room or alias; alias target missing from the base map;
- unknown target; target known but not present in the current layout;
- a controller change with no following expectation (warning);
- an `expectWire` naming a request RBR does not send (warning);
- base map missing `rooms`/`profiles`, or a profile naming an unknown room;
- a step with no action, or two actions;
- `css:` targets (warning, with the fragility reason).

An optional **Validate against the page** run launches the UI, resolves every
target, and reports missing ones without executing the scenario. This catches
layout drift that a static catalogue cannot.

## 10. Builder UX

The window is the target in `docs/MOCKUP.html`.

- **Left:** scenarios (folders/tags), New, and the AI draft panel.
- **Centre:** the step table, with a table/timeline toggle. Columns: `#`, time,
  actor, target, action/value, expectation, result, note. Actor colour and icon;
  icon plus label, never icon alone. Rows reorder by drag; inserting above/below,
  duplicate, disable and delete are row actions.
- **Right:** inspector for the selected step — actor, target picker (filtered to
  valid targets and rooms), value editors, timeout, note, and
  **Insert expectation**.
- **Bottom:** Run / Run from here / Stop, headless/headed, device preset, clock
  range; then the log panel with Steps, Wire, Console and Artefacts tabs.
  Clicking a failure selects its row and shows expected/actual, the screenshot
  and the wire traffic since the previous step.

The timeline view shows the same steps as lanes (Controller, UI, Wire, Expect)
against scenario time. It is a different reading of one model, not a second
document.

Validation issues appear in a strip above the log and on the affected rows.

## 11. AI authoring

The AI produces **scenario JSON, never code**.

Input: the user's description, the scenario schema, the target catalogue, the
room aliases and a summary of the base map, plus the worked examples.
Output: a candidate scenario, a list of `assumptions` and a list of `questions`.
The app validates it, shows a diff against the current scenario, and requires
acceptance. Nothing is executed automatically.

Assumptions are first-class: "assumed Advance clears at the next schedule
change, 18:00" becomes a step note the author must confirm. AI-proposed
expectations are highlighted, because a wrong expectation is the most expensive
kind of wrong.

The provider is pluggable (`AIProvider`); local and remote models are both
options. Scenario data leaving the machine is a visible setting, not a default
hidden in a dependency.

**v0 implementation (2026-11-05):** `ai-draft.py` builds the schema, target,
map-summary and example context; providers are `prompt` (writes a brief for
Reasonix Studio or any chat AI), `claude` (the installed CLI in plan mode) and
`reasonix`/`command` (prompt on stdin, JSON on stdout). `scenario_library.py`
keeps the local library and manifest; the shell's Draft, Refresh scenarios and
two-click Delete wire it. Output is validated with `prepare` before it is
listed; an edit is saved as a new version with a unified diff. The
assumptions/questions fields are not yet separate: the generated scenario may
carry a `note`, and the review is the table plus the diff.

## 12. Plugins and integration

The engine core is product-agnostic; RBR is a plugin:

```python
class ScenarioPlugin:
    name: str
    version: str
    def targets(self) -> dict[str, TargetResolver]
    def step_types(self) -> dict[str, StepHandler]
    def validate(self, scenario, ctx) -> list[Issue]
    def setup(self, ctx) -> None
    def teardown(self) -> None
```

The RBR plugin supplies the target catalogue, room-alias resolution, the map
fixture validation and the `Operating Mode` / `Update Profiles` request parsers.
Another product can supply its own plugin without forking the engine.

Integration points:

- **CLI:** `python -m scenario_runner --scenario ... --repo ...`
- **JSONL:** `PROTOCOL.md`; the PySide app is one client, other tools are others.
- **Library:** `scenario_runner.run(path, emit=callback, options=...)`
- **Export:** a generated CI wrapper that calls the runner with the scenario
  path; no per-step code.

## 13. Packaging

Dependencies: Python 3.11+, `allspeak-ai`, `pyside6`, `playwright`, and a
Chromium build (`python -m playwright install chromium`).

The app launches the runner with the same interpreter by default
(`sys.executable -m scenario_runner`); a setting allows a separate venv, which
is useful when the studio and the runner are upgraded independently.

- `PLAYWRIGHT_BROWSERS_PATH=0` keeps the browser inside the app's environment;
  otherwise it lives in the system cache. The installer chooses and records it.
- The runtime JS is cached by URL under the app data directory, so the second
  run is offline.
- The first distribution to a colleague can be a launcher script plus a venv.
  PyInstaller is possible but large; defer until the tool is stable.
- Windows/macOS support is a Playwright concern, not an app concern, but must be
  tested before promising it.

The studio does not need the `desktop/` MQTT runtime patches: it never speaks
MQTT itself. The runner is a subprocess and speaks to a stubbed page.

## 14. Testing the studio

- Runner unit tests: schema, clock arithmetic, map mutation (deep copies, no
  aliasing), target resolution, wire parsing, failure formatting.
- The two reference scenarios are golden tests, run in CI against the pinned
  runtime.
- The page's own low-level checks stay in `tests/ui/` (Node). The studio must
  not weaken them; the two reference scenarios are the cross-check between the
  Python and Node drivers.
- The PySide shell gets a smoke test for load → validate → run → render a log.

## 15. Roadmap

0. **Spike (1–2 days):** Playwright Python + `page.clock` against the real page;
   prove Scenario 2 with a three-hour jump; measure poll/heartbeat behaviour and
   the runtime's `wait` handling. Exit: a throwaway script passes both examples.
1. **Runner + schema:** CLI, validation, controller stub, wire parsing, artefacts;
   both examples green.
2. **PySide shell:** load/save/validate/run, table, inspector, log. JSON editing
   is acceptable at this stage.
3. **Builder:** drag/reorder, target picker, insert expectation, validation panel,
   timeline view.
4. **AI drafting:** schema-constrained output, diff, assumptions, review gate.
5. **Later:** record from a live controller, parallel runs, real-controller
   drift mode, screenshots/geometry assertions, Qt driver for the desktop app.

## 16. Open questions

- Does the studio stay in this repository permanently, or move once stable? The
  spec assumes `tools/rbr-studio/` for now.
- Should scenarios live beside the UI code (reviewed in the same PR) or in the
  studio's own store? Default: a `scenarios/` folder in the studio, referenced
  from PRs.
- Does the colleague run Windows or macOS? That decides how much packaging work
  phase 1 needs.
- Should the same scenario language eventually drive the PySide desktop app, not
  just the PWA? The driver is behind an interface, but a Qt driver is a separate
  piece of work and is explicitly out of v1.

## 17. Reference

- `docs/examples/temperature.json`, `docs/examples/advance.json`, `docs/examples/delay.json`
- `docs/PROTOCOL.md`
- `docs/scenario.schema.json`
- `docs/MOCKUP.html`
- Existing page harness: `tests/ui/` (the behaviour the Python runner ports)
- Desktop app pattern: `desktop/README.md`, `desktop/rbr_ui.py`
- Map format: `AI/MAP_FORMAT.md`
