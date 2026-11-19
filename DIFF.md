# 2026-11-19 — A stale room heats from the radiator's own sensor

**Action:** `./deploy.sh` (the controller restarts and picks up the new logic), then reload the app once on the phone. Nothing else is needed: the offset starts learning from the next cycle. Give it a few minutes of both sensors reporting before a fallback can run, because it refuses to delegate until it has four paired samples.

## What changed

When a room thermometer goes quiet, the controller used to hold the room off. It now hands the thermostat to the room's self-contained valve, if it has one:

- **Learns the offset.** While both sensors report, it keeps a slow mean of `room − valve-local` (samples capped at ±5 °C), with a min/max envelope around it. Stored on the room as `trvbias`, `trvbiasn`, `trvbiasmin`, `trvbiasmax`, `trvbiasat`, `trvbiasvalve`; a replaced valve resets the estimate.
- **Delegates the thermostat.** With the room reading stale and the valve reporting, it leaves the valve on its own sensor (`local`) and sends a setpoint of *plan target − offset*, so the valve's own reading lands the room on the target. It needs four samples, an offset within 5 °C, a spread within 2.5 °C, a live valve report, and — on the first cycle of an outage — a valve reading no more than 5 °C above the room's last known value. It gives the room back the moment the thermometer reports, and never outlives the plan (Timed only inside a period; On and Boost already carry their own deadlines).
- **Says so.** The room carries `trvfallback` / `trvfallbacktemp`; the card's warning row reads **Radiator sensor in use** rather than `No recent change`, and the Info sheet gains a **HEATING SENSOR** row showing `Radiator — est. N °C` (an estimate, not a measurement). The journal's `room.state` record carries both fields, and the controller log prints one line when the fallback starts and when it ends.
- **Does not touch the schedule.** The dial-adoption guard now ignores a setpoint difference while the fallback is (or was just) shifting it, so the shifted value can never be written into a period target.

The learned fields are identity and survive a materialise; the two display fields are recomputed each cycle and stripped from `map.json`. Deleting the `trvbias*` fields from a room forces a fresh estimate.

## Checked

`tests/unit/run-unit-tests.sh` — 228 tests, including the new `trv_fallback_test` (learning, every refusal gate, the shift arithmetic) and `trv_dial_adoption_test` (a real dial change is still adopted; the shift is not), an extended `setrelay_test` (the fallback heats a stale room and outlives `fail`), and `commit_roundtrip_test` (the learned fields survive; the display fields reach the page but not the plan). `node tests/pwa-compile-check.js` 18/18, and all eight `tests/pwa-*-check.js` pass; `pwa-valve-state-check` now also pins the warning row and the Info sheet row.

## Docs

`docs/concept/02-what-rbr-is.md`, `docs/technical/01-architecture.md`, `docs/technical/07-events-and-the-journal.md`, `docs/operation/01-the-interface.md`, `docs/operation/04-troubleshooting.md`, `docs/appendix/glossary.md`, `doc/setupRBR.md`, `doc/SENSOR-REPORTING.md`, `doc/HEATING-DATA.md`, `AI/MAP_FORMAT.md`, `doc/EVENT-JOURNAL.md`. The old promise — "held off until a fresh reading arrives" — is now "held off, unless the radiator's own sensor can take over".
