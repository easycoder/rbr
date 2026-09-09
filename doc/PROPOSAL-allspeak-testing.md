# Proposal: a testing vocabulary for AllSpeak

**Status:** proposal for submission to the AllSpeak project
**Author:** RBR project (Graham)
**Date:** 2026-08-20

## Motivation

AllSpeak has no in-language way to assert, group, or report on test outcomes. The project's conformance suite tests the runtime *externally* (`.as` script + `.json` expectations of `logs`/`error`, driven by `run_conformance.py`), but a user writing an AllSpeak program has no facility to say "this must hold" and have it checked, counted, and reported — and none of the `spec/`, `opcodes.json`, or `learn/` references define any test-related command.

The need is real and concrete: the RBR controller project (a substantial AllSpeak program with ~25 subroutines of decision logic — schedule-period lookup, boost expiry, relay-fail thresholds) currently has no way to unit-test its pure logic without standing up a broker, a browser, and simulated devices. A small, English-natural testing vocabulary would make the controller's decision rules directly testable.

## Design principles

1. **Reuse, don't invent.** `check that <condition>` accepts the *same condition grammar as `if`* — no new condition syntax, no new operators. Every condition documented in `reference/06-conditions.md` (`is`, `is not`, `is less than`, `is greater than`, `is numeric`, `is empty`, `includes`, `has entry`, `file … exists`, bare truthy) works unchanged.
2. **English verb over programmer jargon.** `check`, not `assert`. `assert` is familiar to programmers but jars with the language's style; `verify` is stiffer than the everyday "check that". The word must read naturally to a reviewer: "check that the room count is 4".
3. **A failed check is a report, not a crash.** Checks accumulate; one run reports every failure. This matches how the existing `or`/`on failure` distinction already thinks about failures.
4. **Compose with existing failure clauses.** `check` optionally takes `or` / `on failure` clauses with their existing semantics, so an author can say "fail and bail" or "fail and recover" without learning new concepts.
5. **CI-friendly.** A `--test` runner mode gives a summary and a process exit code.

## Proposed vocabulary

### `check that <condition>`

Evaluates the condition. On success, records a pass. On failure, records a failure (log line `FAIL: <condition> (<file>:<line>)`) and execution **continues** — a test run collects all failures in one pass.

```as
check that RoomCount is 4
check that Map has entry `Kitchen`
check that SensorId is not empty
check that Target is greater than Ambient
check that the value of Minutes is numeric
check that Time includes `:`
check that file `map-sim.json` exists
check that Linked                    ! bare truthy, same as `if Linked`
```

Optional failure clause, reusing existing semantics:
- `check that X is 3 on failure gosub to FixUp` — record the failure, run `FixUp`, continue.
- `check that X is 3 or gosub to Cleanup` — record the failure, run `Cleanup`, then **stop this test** (it ends, marked failed).

### `test <name>` … `end test`

Groups a run of statements into one named case, so the summary reports per-case results and the runner can isolate errors.

```as
test `Adding a room`
    gosub to AddRoom
    check that RoomCount is 4
    check that the name of the last room is `Kitchen`
end test
```

Checks outside any `test` block belong to an implicit default case. `test`/`end test` are a statement pair in the same spirit as `begin`/`end`.

### Runner: `allspeak --test <file.as | dir>`

- Runs the script(s) in test mode. `check` statements accumulate results.
- Any **unhandled runtime error** (including an `or` clause firing without a clause attached to a `check`) fails the current `test` block and the runner moves to the next block, rather than aborting the whole run — so one broken case doesn't hide the others.
- A normal `exit` (or end of script) triggers the summary and sets the process exit code:
  - `0` — all checks passed
  - `1` — at least one check failed or a test errored
  - `2` — the script itself could not be compiled/run (so CI can distinguish "tests failed" from "tests broke")
- Passing a directory runs every `.as` file in it as its own suite, with an aggregated summary.
- Output shape:

```
Test suite: schedule.as
  ✓ Adding a room        (2 checks)
  ✗ Advance roll-over    (FAIL: the room count is 4 — line 12)
  ✓ Boost expiry         (3 checks)

3 tests, 2 passed, 1 failed — 7 checks, 6 passed, 1 failed
exit code 1
```

- `check` also works in **non-test mode** (a plain `allspeak file.as`): a failed check logs `FAIL` but the script continues, and no exit-code change applies — so `check` doubles as a lightweight defensive-assertion facility in production scripts. Only `--test` adds summary, isolation, and exit codes.

### Dialect parity

Both runtimes should implement the vocabulary (the conformance suite already runs the same script in both). Python runtime is the v1 target; the JS runtime should match, since the browser runtime is equally capable of evaluating conditions — only DOM/browser *testing* is out of scope (below).

## Worked example

A controller-flavoured test of schedule-period selection, written against the vocabulary (illustrative only — the RBR controller's actual subroutines would be the subjects):

```as
!   schedule-test.as

    script ScheduleTest

!! Period lookup: given a time of day, the current period is the last one whose start has passed.

    variable Periods
    variable Current
    variable Target

    reset Periods
    append `07:00|21.0` to Periods
    append `09:00|15.0` to Periods
    append `18:00|22.0` to Periods

    test `Period lookup picks the right row`
        put `08:30` into Current
        gosub to FindCurrentPeriod
        check that Target is 2100
        put `19:00` into Current
        gosub to FindCurrentPeriod
        check that Target is 2200
    end test

    test `Before the first period means background`
        put `06:00` into Current
        gosub to FindCurrentPeriod
        check that Target is 0 or gosub to ReportBug
    end test

    exit
```

## Phase 2 (explicitly optional — include only if the maintainer wants a wider scope)

Three additions that would specifically unlock time-dependent and messaging logic (the RBR controller's two hardest-to-test areas):

1. **Fake clock.** `set the clock to `2026-08-05 09:00``, `advance the clock by 90 minutes`, `use the real clock`. While a fake clock is set, all `now` / `today` / `weekday` reads consult it. Makes day-rollover, staleness windows, and boost expiry deterministic without sleeping.
2. **Send capture.** In test mode, record `send …` operations: `check that a message was sent to SenderTopic`, `check that the last message sent includes `confirm``. Tests the controller's reply/confirm logic without a broker.
3. **Log capture.** `check that the log includes `relayfails`` — assert on `log` output, which is how the conformance harness already asserts today.

## Explicitly out of scope

- Mocking/stubbing frameworks (the existing `sim`-file module-substitution pattern already covers the "replace a module" need; a generic seam could be a separate proposal).
- Code coverage measurement.
- DOM/UI testing (that's what the browser runtime's GUI tests are for, and it's a much larger surface).
- Parallel test execution, property-based testing, test-selectors/filters beyond what the runner's directory argument provides.

## Suggested docs and repo placement

- New reference file `learn/reference/19-testing.md` alongside the existing 18, following the established per-keyword format used by `allspeak-py/doc/core/keywords/*`.
- Conformance additions in the existing `conformance/tests/` style (e.g. `EC-0xxx-check-basic.as` + `.json`) so parity between the Python and JS runtimes is verified automatically.
- A test-file naming convention of `<name>-test.as` or a `tests/` directory, documented in the reference.

## Intended validation

Once the vocabulary lands in the AllSpeak runtime, the RBR project intends to write a small set of tests in RBR to validate it in practice — unit-testing the controller's I/O-free decision subroutines (e.g. `ConvertTimeToInt`, `ConvertTempToInt`, `FindCurrentPeriod`, `FindNextPeriodFromNow`, `ApplyPeriodsAdvance`, `GetNaturalPeriod`, `RoomStatus` thresholds) with no broker, no browser, and no sleeps.
