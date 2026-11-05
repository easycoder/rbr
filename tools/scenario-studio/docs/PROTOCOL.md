# Runner protocol

The studio launches one runner process per run and talks to it over stdout and
stdin. One JSON object per line; stderr is for human-readable tracebacks and is
never parsed. Version 1.

## Invocation

```
python -m scenario_runner \
  --scenario path/to/scenario.json \
  --repo /path/to/rbr \
  [--headless|--headed] \
  [--device phone|desktop] \
  [--from STEP_ID] \
  [--validate-only]
```

`--repo` is the checkout being tested. It defaults to the repository containing
the runner. `--from` runs from a step onward, still using the scenario's clock
and base map. `--validate-only` resolves schema, targets and rooms, emits
`validation.issue` events, and finishes without launching Chromium.

Exit codes: `0` all steps passed, `1` a step failed, `2` invalid scenario or
configuration, `3` runner error (browser launch, crash).

## Events (runner → app)

Every event carries `v` and `event`.

```json
{"v":1,"event":"run.started","runId":"2026-11-05T14-30-00-advance",
 "scenario":{"name":"Advance holds until the next schedule change","path":"..."},
 "environment":{"runner":"0.1.0","playwright":"1.5x","chromium":"147",
   "repo":"/path/to/rbr","commit":"b12d008","viewport":{"width":390,"height":844},
   "timeZone":"Europe/London","headless":true}}
```

```json
{"v":1,"event":"step.started","stepId":"s5","index":5,"at":"15:00","actor":"ui"}
```

The `actor` is one of `controller`, `ui`, `expect`, `wire`, `connection` or `delay`. A `delay` step is a paced-demo pause and is skipped in a normal run.

```json
{"v":1,"event":"step.finished","stepId":"s5","status":"passed","durationMs":38}
```

```json
{"v":1,"event":"step.finished","stepId":"s6","status":"failed","durationMs":5021,
 "failure":{"message":"no Operating Mode request matched",
   "expected":{"request":"Operating Mode","match":{"Room":"Office","advance":"A"}},
   "actual":{"request":"Operating Mode","fields":{"Room":"Office","advance":"none"}},
   "artifacts":["screenshots/s6.png","wire.jsonl"]}}
```

```json
{"v":1,"event":"log","stepId":"s5","level":"info","source":"wire",
 "message":"Operating Mode {\"Room\":\"Office\",\"Mode\":\"timed\",\"advance\":\"A\"}"}
```

`source` is `console`, `wire`, `runner` or `page`. `level` is `info`, `warn`,
`error` or `debug`.

```json
{"v":1,"event":"artifact","stepId":"s6","kind":"screenshot",
 "path":"runs/.../screenshots/s6.png"}
```

```json
{"v":1,"event":"validation.issue","severity":"error","stepId":"s6",
 "path":"steps[5].expectWire.request","message":"RBR does not send a request called 'Operate Mode'",
 "suggestions":["Operating Mode"]}
```

```json
{"v":1,"event":"run.finished","status":"failed","passed":5,"failed":1,
 "durationMs":6820,"artifacts":{"dir":"runs/...","result":"result.json",
 "trace":"trace.zip","wire":"wire.jsonl","console":"console.log"}}
```

`run.finished.status` is `passed`, `failed`, `cancelled` or `invalid`.

## Commands (app → runner)

One line per command on stdin:

```json
{"command":"cancel"}
```

Cancellation stops after the current step, writes the artefacts it has, emits
`run.finished` with `status: "cancelled"` and exits `1`.

## Rules

- A line is complete JSON; no pretty printing, no embedded newlines.
- Unknown event types must be ignored by clients, so the runner can add fields.
- Paths are absolute in artifacts; the app may rewrite them for display.
- The scenario snapshot in the run directory is the authority for what ran, not
  the file the user has open.
- The runner never opens a listening socket. This is deliberate: no port
  conflicts, no firewall prompts, and the boundary is the process pipe.
