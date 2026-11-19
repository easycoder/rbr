# 2026-11-19

## 20:48

Can you take a look at various/Newton12/261119.jpeg and explain what it means? I'm not familiar with the words "valve idle".

**Assistant**

Yes — that's the PWA home on a four-room system at 08:01, and `valve idle` is a warning about a disagreement between the plan and the radiator.

**What the tag literally means.** `valve idle` is not RBR's word for "off". It is the radiator valve's own report: a self-contained TRV (thermostatic radiator valve — the motorised head on the radiator) publishes `running_state`, where `heat` means the valve is open and hot water can flow, and `idle` means it is closed. The controller copies `trvrunning` into the room and the card tags from that, not from its own demand.

**Why the tag appears at all.** The card only draws it when both things are true: RBR is calling for heat in that room *and* the valve says it is closed. A room that is not calling gets no tag; a calling room whose valve is open gets the normal orange flame and `heating`, like Dining Room. So `valve idle` is deliberately an amber, clock-marked warning state — "asked for heat, not being delivered".

**The two amber signals on that card are probably one fault.** The Living Room is at 18.1 °C with a target of 20 °C, so it is 1.9 °C short and the radiator is shut. It also shows `⚠ No recent change`, which means the thermometer has not reported for over 45 minutes. Once the reading is too old the controller stops driving the valve rather than heating blind, so the valve closes and reports `idle` — the tag and the warning are the same story. The one exception is the first 30 minutes of a scheduled period, when the controller deliberately decides on the last known reading (that is why the summary still counts the room as calling and the card still shows `valve idle`); a one-cycle lag after the reading expires looks the same. The schedule line `20.0° → 09:00` says the next planned change is 20 °C at 09:00, so this is a room inside its morning period, not one in a gap.

**If the sensor turns out to be fine,** the other causes are on the valve itself: its own internal sensor reads warmer than the room thermometer, the head has been turned down by hand or is running its own local program, or commands are not reaching it. Note that it is still *reporting* its state, so this is not `Valve not responding` (that would be the offline tag) — the radio link is up and the valve is simply saying "I'm shut".

**Reading the rest of the screen.** `2 rooms calling for heat` counts Dining Room and Living Room, the two rooms below target; KW and OB are at or above their 18 °C target, so they carry no tag. `OUTSIDE —` means no outside thermometer is configured or none has reported. The dot in the top bar has no flame beside it, which the layout only hides when no system-wide demand relay is configured — consistent with a per-room-valve installation rather than a boiler relay.

**What to do about it,** in order: open Room details on the Living Room to see the age of the last report and the thermometer's battery; replace the thermometer battery or check its range first, since the warning names it; then check the valve head's battery and its dial/setpoint. If both are healthy and the valve still sits closed while the room is cold, that is valve hardware and installer work.

One gap while I was checking: `No recent change` is documented in `docs/operation/04-troubleshooting.md`, but `valve idle` and the joint rule it implies are not in the troubleshooting page or the glossary. I can add a row and a glossary entry if you want it on the site.

## 20:54

Would it be sensible to adopt a strategy that when the room thermometer is stale and the radiator has a self-contained TRV, for it to use its own sensor instead until the room thermometer comes back?

**Assistant**

**Short answer: yes in principle, but as an explicit, bounded fallback — and it would not have rescued the Living Room in the screenshot.**

**What happens today.** After 45 minutes without a room reading the status goes `warn`, `SetRelay` forces the relay/demand off, and `ProcessTrv` sends `mode: off, sensor: local` — so the valve closes. The one exception is a scheduled period's first 30 minutes, which decides on the last known reading; the valve stays on its own sensor and modulates, then the heat goes off. That is the promise in `docs/concept/02-what-rbr-is.md`: a room cools gently rather than being heated without feedback.

**The case for.** "Without feedback" is not quite true of a TRV room: the valve has its own sensor, its own thermostat and a setpoint. Delegation is closed-loop control on a different sensor, and it is what the hardware already does by itself — the TRVZB falls back to its own sensor (`remote_source_offline`) after two hours without an external reading. RBR pre-empts that at 45 minutes with `off`. A thermometer can be out for days (battery, mesh, a neighbour losing its parent); leaving the room with no control at all for that time is the worst outcome for comfort and for frost.

**The case against — and it is strong.** The valve's sensor is bolted to the radiator, not placed in the room, and this project has measured how far apart they get. In the Living Room, the valve read 21 °C while the room thermometer read 19.8 °C — that mismatch is why the external-sensor path exists. On the 2026-10-21 second-system incident, three valves on their own sensors read 28.8 and 29.8 °C while the rooms were 22.0–23.8 °C. The bias is mostly high while the radiator is working, so delegation will usually undershoot: with a 6 °C bias, a 20 °C target becomes a 14 °C room. Better than off, but not by much. In the screenshot's own case it changes nothing: a valve whose local sensor reads ~21 sits idle at a 20 °C target whether RBR says `heat/local` or `off`.

There is a second cost: delegation splits control. RBR knows the timetable but not the temperature, and a valve sensor that sticks low holds a radiator open until the bound expires, invisible to RBR. Today's design can state "the room is not being heated" as a fact; delegation weakens that unless the app states the new fact instead.

**Conditions I would attach.**
- Trigger only when the room has a `trv`, its `sensor` is a different device, the room reading is stale (>45 min) and the valve's `local_temperature` is fresh. A silent valve gets no fallback.
- Plausibility gate: if the local reading is more than about 5 °C above the last known room reading, call it heat-soak, log it and hold off. That keeps the worst measured case out.
- Keep RBR's authority: schedule, mode and target stay RBR's; the valve is only the thermostat. Send `mode: heat`, `sensor: local`, setpoint = current target, and feed the local reading into `TempDecision` so `relay`/demand (and a boiler request relay) stays coherent — but not into the room's displayed `temperature`, which should go on showing the last real value as stale.
- Bound it: until the current period ends, or a fixed number of hours. I would pick the period end — it is already in the plan and needs no new clock. Boost is already bounded by `until`, so it can delegate too.
- Say it out loud: a distinct status message and card tag ("Running on the radiator's own sensor — room thermometer not reporting") instead of today's `No recent change`, plus a journal entry. If a delegated valve still reports `idle`, that is now a real valve fault rather than a policy.
- Return automatically: a fresh room reading already restores `heat` + `remote` + the reading on the next cycle, and the bridge's two-message publish fixes the `remote_source_offline` trap, so that half exists.
- Companion, and I think the real win: calibrate. When the room reading is healthy and the radiator has settled cold, RBR can learn `local − room` per valve and write `local_temperature_calibration` (Zigbee2MQTT exposes it; the bridge does not write it today). Then a fallback starts from a room-referenced local reading. Without that, delegation is "better than nothing"; with it, it is close to the target.

**One consequence to weigh first:** "the room is held off until a fresh reading arrives" is a product promise repeated in `docs/concept/02`, `docs/technical/01`, `docs/technical/07`, `docs/operation/04`, the glossary, `doc/setupRBR.md` and `doc/SENSOR-REPORTING.md`. All of them would change together. If you would rather not change it for every install, the alternative is a per-system option in the map, default off — but that is another field, another switch and another doc, for a behaviour whose safe default I think is on.

**A related inconsistency I noticed.** Boost is documented as bypassing the staleness gate, and `SetRelay` does set the relay on for a boost. But `ProcessTrv` sends the valve `off` whenever `PriorStatus` is `warn` and there is no period-start grace, and boost never sets that grace. So a boost on a TRV room with a stale sensor already shows as calling in the app while the valve is commanded shut. Delegation would resolve that case; if you do not adopt it, that branch should be decided explicitly.

**Scope if you want it:** `ProcessRoom`/`SetRelay` (the stale veto), `ProcessTrv`/`ProcessTrvState` (read `local_temperature`, choose the sensor), a `TrvDelegated` flag; no new bridge field (it already writes `local_temperature`, though `last_seen` is per device and would ideally be per value); UI in `map-to-rooms.allspeak` and `shell.allspeak` for the tag and message; tests in the extracted-controller suite and `tests/pwa-valve-state-check.js`; and the docs above.

## 21:29

The problem is a cheap thermometer, that can't be told to report more frequently. I've fitted 2 Sonoff devices here and had no stale readings since I set a 10-minute maximum. I can recommend an upgrade, but if the system can estimate what the room thermometer would have reported by knowing the difference when both are active, then I think we should try it. I agree fully with your boundary conditions, and also with making it clear that the room is running on the TRV sensor, which should make it visible when it happens again.

**Assistant**

Implemented. The controller now hands a stale room to its radiator's own sensor, with the offset learned while both were reporting.

**What it does**

- `LearnTrvBias` samples `room − valve local` whenever both readings are fresh and less than 5 °C apart, keeping a slow mean plus a decaying min/max envelope. The estimate resets if the room's `trv` name changes.
- `ProcessTrvBias` (before `SetRelay`) decides the fallback: room thermometer stale, valve reporting inside the same 45-minute gate, at least four samples, an offset within 5 °C, a spread within 2.5 °C, `trvfails` ≤ 5, Timed inside a period or On/Boost (their own deadlines bound them), and — on the first cycle — the live valve reading no more than 5 °C above the room's last known value.
- When it runs, `SetRelay` uses the corrected estimate as the room reading (so demand and "N rooms calling" follow it), and `ProcessTrv` keeps the valve on `local` with its setpoint shifted by the learned offset. A valve reading 1.2 °C high is sent 21.2 for a 20 °C target, clamped to the valve's 4–35 °C range.
- It ends when the room thermometer reports again (the sensor-mode change is itself a command, so it does not wait for the 10-minute keepalive), when the plan stops wanting heat, when the valve stops reporting, or when the estimate fails a gate.
- **Dial adoption is guarded.** Without this, entering or leaving the fallback would look like someone turning the valve and would write the shifted value into the period target. `SyncTrvLocalSetpoint` now ignores a difference while the fallback is (or was just) running.

**What you see**

- The card's warning row says `Radiator sensor in use` instead of `No recent change`.
- Room details gains a **HEATING SENSOR** row: `Radiator — est. 18.6 °C` (the estimate, not a measurement), or `Room thermometer` / `Radiator` normally.
- The controller logs one line when the fallback starts and ends; `room.state` journal events carry `trvfallback` and `trvfallbacktemp`.
- The learned fields are identity and survive a materialise/commit; the two display fields are recomputed each cycle and stripped from `map.json`.

**Caveats, all documented.** The estimate needs four samples, so a sensor that dies in the first minutes after a controller restart leaves the room on the ordinary held-off rule. A valve whose sensor swings more than 2.5 °C, or sits more than 5 °C from the room, never qualifies — that is the second-system heat-soak case, and those rooms stay off. Because the valve's setpoint is shifted while the fallback runs, Zigbee2MQTT will show e.g. 21.2 for a 20.0 plan; that is deliberate, and the app always shows the plan's target, not the shifted value.

**Checked.** `tests/unit/run-unit-tests.sh` 228 tests, including the new `trv_fallback_test` (learning, every refusal gate, the shift arithmetic) and `trv_dial_adoption_test`, an extended `setrelay_test` (the fallback heats a stale room and outlives `fail`) and `commit_roundtrip_test` (the learned fields survive; the display fields reach the page, not the plan). `node tests/pwa-compile-check.js` 18/18, and all eight `tests/pwa-*-check.js` pass; `pwa-valve-state-check` now also pins the warning row and the Info sheet row. Docs updated across concept, technical, operation and the glossary, plus `AI/MAP_FORMAT.md`, `doc/EVENT-JOURNAL.md`, `doc/HEATING-DATA.md`, `doc/setupRBR.md`, `doc/SENSOR-REPORTING.md` and `DIFF.md`.

Deploy with `./deploy.sh`; the controller restarts and begins learning the offsets immediately.
