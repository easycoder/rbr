# Scenario runner (v0)

Runs a scenario JSON against the real `new-ui` page in Chromium.

```bash
cd tools/rbr-studio

# once per machine
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium

# validate without a browser
.venv/bin/python -m scenario_runner --scenario docs/examples/advance.json --validate-only

# run (the default --repo is this repository)
.venv/bin/python -m scenario_runner --scenario docs/examples/advance.json
.venv/bin/python -m scenario_runner --scenario docs/examples/temperature.json
.venv/bin/python -m scenario_runner --scenario docs/examples/delay.json

# run several scenarios in one batch (a record is written under fixtures/local/batches/)
.venv/bin/python batch_runner.py \
    --scenario docs/examples/temperature.json \
    --scenario docs/examples/delay.json

# show the browser, or stream JSONL for the studio app
.venv/bin/python -m scenario_runner --scenario docs/examples/advance.json --headed
.venv/bin/python -m scenario_runner --scenario docs/examples/advance.json --jsonl

# Show playback: headed, paced, collapsed polls
.venv/bin/python -m scenario_runner --scenario docs/examples/advance.json \
    --headed --speed 120 --collapse-polls --step-pause-ms 300
```

Artefacts go to `~/.local/share/rbr-studio/runs/<timestamp>-<slug>/`
unless `--run-dir` is given: the scenario snapshot, base map, environment,
`result.json`, `wire.jsonl`, `console.log`, failure screenshot and trace.
If the user data directory is not writable, the default falls back to `.runs/`
in the current directory or the temp directory. The run path printed at the end
is the authoritative one.

## What a run prints

```
  ✓ s1   07:12  identity temperature = 1840
  ✓ s2   07:12  room.Kitchen.temp contains 18.4
  ...
PASSED  Kitchen temperature follows the controller  (8144 ms)
artefacts: /home/.../.runs/20261105-160644-kitchen-temperature-follows-the-controller
```

Each line is one step: id, scenario time, and what it did. A failure prints
`✗`, the expected/actual detail, exits 1, and saves a screenshot and trace in
the artefacts directory. The first run fetches the pinned runtime and caches
it; later runs use the cache.

## What it is

This is the engine from `docs/SPEC.md`, not the PySide studio yet. It covers the
two reference scenarios and the parts they need:

- schema and semantic validation (rooms, targets, times, step ids);
- the pinned AllSpeak runtime, routed from `new-ui/index.html` and cached by URL;
- a static server and a fake `credentials.json`;
- the scripted MQTT client, including chunk reassembly and outbound request parsing;
- full-map controller pushes, with identity and profile-state changes;
- protocol replies for `first` and `refresh`;
- semantic targets (`room.Office.advance`, `sheet.title`, …);
- a virtual clock, wire assertions and artefacts.

## The clock finding

A single `fast_forward` over a multi-hour gap makes the shell's 10-second poll
run once, see no reply for longer than its 60-second staleness limit, and
reload. `set_fixed_time` stops the deferred message handling that applies a map.
What works is advancing in 50-second slices while the stub answers each poll
with a heartbeat: three hours takes about ten seconds, fires ~240 polls, and the
page stays alive. That is `PageDriver.advance_to`.

Polling is therefore exercised at a reduced cadence during big jumps, not at
the real 10-second cadence. A scenario that needs the exact cadence will need a
separate "run timers" mode; the scenarios here do not.

## Show playback

`--speed N` plays the virtual clock at N scenario seconds per real second:
`1` is real time, `120` turns a three-hour gap into 90 seconds, `300` into 36.
In this mode the clock advances in 10-second virtual slices with a real sleep
after each, so the page's poll, clock tick and heartbeat are visible. `--headed`
opens the PWA window; `--step-pause-ms` holds each passed step on screen for a
moment. `--collapse-polls` suppresses the per-poll `Requesting map: refresh`
log events and emits a `refresh ×50` summary every fifty, plus a final total;
the full console is still written to the run's `console.log`.

The shell uses these together for its **Show** button. **Run** uses `--collapse-polls --step-pause-ms 300` as well, without `--view` or the speed selector, so its live log arrives in small batches; only `--fold-to-marker` and `--pause-at-marker` remain Show-only, because Run has no breakpoint to honour.

A step may carry `"marker": true`, and at most one step in a scenario may do so.
`--fold-to-marker` applies the controller steps before the marker to the base
map in Python, sets the clock to the marker and starts there; `--pause-at-marker`
then stops after the marker and reads `{"command":"step"}` and
`{"command":"continue"}` from stdin. The Studio's **Show** sends both flags, so
a long journal scenario reaches its breakpoint without replaying its history
through the page. **Step** advances one step and **Show** again continues. A
normal run ignores the breakpoint because it is already as fast as possible.
The Studio's **Mark** column sets or clears the marker on a library scenario.

## Not in v0

- the PySide window, table, inspector and log (the JSON is edited by hand);
- `--from STEP_ID` / run-from-here;
- geometry and screenshot assertions;
- parallel runs;
- the real controller as the engine.

The JSONL protocol from `docs/PROTOCOL.md` is implemented for the events the
runner emits; the studio can consume it as-is.
