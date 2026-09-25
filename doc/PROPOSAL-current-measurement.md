# Proposal: current and power measurement

**Status:** proposal for the RBR project **Author:** Graham **Date:** 2026-09-20

## Motivation

The two present installations read temperatures and drive radiators, and know nothing about the environment. [current-measurement.md](current-measurement.md) sets out why that matters: solar output is the cleanest proxy for solar gain, which affects rooms irrespective of the heating system, and correlating electricity consumption with solar input, tariff bands and storage is what makes an all-electric system plannable. This proposal is the *how*.

Four constraints shape everything below.

1. **A gas installation with no meters must be completely unaffected.** Not "degraded gracefully" — unaffected, with no new failure modes and no new startup cost. This is the reason for the `meters.json`-absent rule in §4.
2. **The heating path must not become a power-monitoring program.** `controller.as` is already the largest file in the repo. Power flows are a separate concern with a separate failure mode, so they get their own module and their own config file, and `controller.as` gains four lines (§6).
3. **Local only.** No cloud dependency, no vendor account, no reverse-engineered protocol. This is a product principle, not a preference — it is the difference between a "distributed appliance" and a smart-home gadget, and it settles the eddi question in §7.
4. **Measure, don't infer.** A flow that is clamped is a measurement; a flow derived by subtraction is an assumption that silently absorbs every error. Where a flow matters, clamp it.

## 1. What is measured, and where

Five flow identities, of which four are instrumented in the reference installation:

| Flow | Clamp site | Sign convention | Why it earns a clamp |
|---|---|---|---|
| `grid` | Incoming live tail, after the meter/isolator | positive = import, negative = export | The only place export is visible. Everything else follows from it. |
| `solar` | Inverter's AC feed, at its MCB | positive = generation | The number the solar-gain correlation needs |
| `heatpump` | Heat pump circuit live, at its MCB | positive = consumption | The one flow that joins to the `heatlog` room records; RBR's own subject matter |
| `store` | **The eddi's supply feed** | positive = consumption | "Power to storage" for this installation |
| `ev` | EV charger circuit (reserved) | positive = consumption | Deferred; no EV yet |

`heatpump` is an addition to the four flows in [current-measurement.md](current-measurement.md). It earns its place because RBR is a heating product: electrical demand against delivered heat is the measurement that can eventually say whether a heat pump is performing, whereas the other four are system-planning data. Keep it first-class rather than a special case.

**Clamp the boundary, not the elements.** An eddi can drive two immersion heaters (H1/H2) and reports them separately. Clamping each element feed would need two clamps and would go stale the moment the store is rewired. Clamping the eddi's *supply* feed measures total power to storage in one clamp, and it is the natural boundary: that cable carries diverted power and nothing else. Recommended even if the store currently has a single element.

### Load figures and clamp rating

The planned installation cannot approach an 80 A clamp:

| Circuit | Rating | Current at 240 V |
|---|---|---|
| Solar inverter | 3.6 kW max | 15.0 A |
| Heat pump | 10 kW thermal, SCOP ≥ 3 → ~3.3 kW electrical seasonal average; size the *circuit* on worst-case cold-weather input (~4–5 kW) | ~17–21 A |
| eddi | 3.68 kW max output | 15.3 A |
| Dual oven | 32 A circuit, the largest single circuit | ~17–29 A typical |
| Grid tail | all of the above, with diversity | realistically 40–55 A |

So **order the standard 80 A clamps and do not pay for higher-rated CTs.** The earlier caution about an 80 A clamp on a 100 A cutout is retired by these numbers: with diversity, the tail will not reach 80 A, and a saturating clamp clips rather than damages.

The real limit is at the *other* end of the range. An 80 A clamp on a ≤ 20 A circuit operates in its bottom quarter, and low-end linearity is where cheap CTs are worst. Expect a tolerance of a few per cent and treat sub-1 kW readings as indicative rather than accurate. That matters most for `store`: a diverter modulates continuously and spends much of its shoulder-hour life in the 0.5–2 kW band, which is exactly the region where the clamp is least reliable. Two consequences:

- The eddi app's own diverted totals are a useful periodic **cross-check** (see §7) — compare at the end of a sunny day, not minute by minute.
- If the low band turns out to matter analytically, the alternative for that one circuit is a series-wired DIN-rail meter (single-phase, bidirectional, `energy` + `produced_energy` exposes), which measures in-series and is good across the whole range. It needs the 16 A spur interrupted and a spare DIN way, so it is electrician work rather than a clamp — justified for the store circuit, not for the others.

### Zigbee hardware

Two two-channel bidirectional meters, not four single-clamp devices:

| Position | Device | Channels |
|---|---|---|
| Meter 1 | `PJ-1203A` / `PC311-Z-TY` family | A = `grid`, B = `solar` (the bilateral pair the device is designed for) |
| Meter 2 | same model | A = `heatpump`, B = `store` |

An 80 A clamp on the HP circuit and the cooker's 29 A are in the same range, so a single model works everywhere. Verify the `manufacturerName` fingerprint before ordering — the family covers `_TZE204_81yrt3lo`, `_TZE284_81yrt3lo` and `_TZE200_rks0sgb7`, and near-identical Tuya devices exist that report only unsigned consumption. Avoid `TS0601_3_phase_clamp_meter` for `grid`: Zigbee2MQTT exposes consumed `energy` only, with no `produced_energy`, so export would be invisible.

Both units need a 13 A socket within CT-lead reach of the board, and both should sit **outside** the enclosure. `setupRBR.md` step 5 records that a dongle against metalwork degraded every link in the mesh; a mains-powered meter inside a steel consumer unit is the same hazard with the same symptom.

### Fingerprints, and the one flow that needs them all

White-label listings are not manufacturers: the brand name says nothing about what is inside, and Zigbee2MQTT matches Tuya devices on `TS0601` **plus the `manufacturerName` fingerprint**, never on the model string. Two units from the same listing can carry different modules. So a description like "dual-channel 0.2–80 A bi-directional meter" identifies the *class* — the PJ-1203A family this proposal assumes — but not the support status.

There is a functional trap inside that class, and it falls across exactly one flow:

| Z2M device | Direction exposes | Usable for |
|---|---|---|
| Tuya `PJ-1203A` | `energy_flow_a/b`, `energy_produced_a/b`, `signed_power_a/b` option | all four flows |
| Tuya `2CT` | none — `energy_a/b` (consumed only); no flow, no produced energy, no signed-power option | `solar`, `heatpump`, `store` — **not** `grid` |

Both are sold as bidirectional 80 A meters, by the same description. Only `grid` needs the direction, because import and export share one cable; the other three are single-direction flows where a magnitude is enough. A consumption-only unit is therefore a false economy in the `grid` position and perfectly adequate everywhere else — an asymmetry worth exploiting rather than treating the purchase as all-or-nothing.

Practical consequence for the order: **buy one, prove it, then buy the second.** Pair it, read the fingerprint from the Zigbee2MQTT log, and confirm three things before buying its twin — that the device reports `supported: true`, that it exposes `energy_flow_a`, and that `energy_produced_a` increments while the installation is exporting. An unsupported fingerprint is recoverable (an external converter in `data/external_converters/`, auto-loaded since Zigbee2MQTT 2.0.0) but it is per-device work that cannot be shipped generically for an unknown brand. That is why §10 puts the fingerprint into RBR's own diagnostics.

RBR builds Zigbee2MQTT from git master (`rbr-setup.sh`, `git clone --depth 1`), so a controller gets upstream converter support as soon as it is merged — the stale-`zigbee-herdsman-converters` problem that catches Home Assistant add-on users does not apply here. The other side of that coin is that the converter set is unpinned, so the same controller rebuilt a year later is not running the same code. That is a reproducibility question in its own right, and it is not settled by this proposal.

## 2. Data path

```
zigbee2mqtt ──MQTT──▶ zigbee-bridge.py ──▶ zigbee-meters.json ──▶ meters.as ──┬──▶ powerlog.py        (history)
                                                                (module)  ├──▶ message to controller.as ──▶ MQTT ──▶ UI
                                                                          └──▶ /tmp/rbr-flows.json ──▶ rbr-dashboard.py

meters.json  (hand-maintained config)  ──────────────────────────────────▶ meters.as
```

The shape follows the existing thermometer path exactly — the bridge persists raw device state to a JSON file, and the controller-side code reads and merges it. Recognising that pattern is deliberate: `zigbee-temperatures.json` already proves it works, and it keeps the always-on observation in the daemon and the RBR-side reasoning in AllSpeak.

## 3. `zigbee-bridge.py`

The bridge already receives every field it needs. It subscribes to `zigbee2mqtt/#`, and `_handle_device_update` currently keeps only `state`, `temperature`, `humidity`, `battery`, `power` and `energy` — so `power_a/b`, `energy_a/b`, `energy_produced_a/b`, `energy_flow_a/b`, `current_a/b`, `voltage` and `ac_frequency` arrive and are dropped.

Three changes:

1. **Passthrough.** Keep the meter-shaped keys for any device that publishes them, under a per-device `channels` dict.
2. **`_update_meters_file()`**, mirroring `_update_temperatures_file()`: atomic write (`mkstemp` + `os.replace`) of `zigbee-meters.json`.
3. **Surface on `/device/{name}`**, so `diagnose.as` can show meter readings without reading the file itself.

**No coupling to `meters.json`.** The bridge classifies a meter purely by the shape of its payload, so it never has to know which device is on which flow, and a smartplug's power reading lands in the same file for free.

**Store both forms of direction.** Persist the `energy_flow` enum *and* the signed power. RBR should not depend on Zigbee2MQTT's `signed_power_a/b` option being set — a customer or a firmware reset can lose that setting, and a flow that silently changes meaning is worse than one that is missing.

`update_frequency: 10` on both meters — see the cadence table in §5 for why that number and not 60.

## 4. `meters.json` — configuration

Machine-specific, hand-maintained, never written by the controller: the `config.json` precedent, for the same reasons. Absent file means the whole feature is off, logged at startup and costing nothing — the `heatlog-root` precedent.

```json
{
  "_doc": "Meter/flow configuration — machine-specific, mirrors config.json",
  "meters": [
    { "name": "Mains-meter", "channels": { "a": "grid",     "b": "solar" } },
    { "name": "Loads-meter", "channels": { "a": "heatpump", "b": "store" } }
  ],
  "flows": {
    "grid":     { "sign": "import-positive" },
    "solar":    { "sign": "generation-positive" },
    "heatpump": { "sign": "consumption-positive" },
    "store":    { "sign": "consumption-positive" }
  }
}
```

- `name` is the Zigbee2MQTT friendly name, and it must match character for character — the same contract `setupRBR.md` lays down for rooms and relays.
- `channels` maps a channel to a flow identity. A channel absent from the map is ignored, not guessed. A meter absent from `zigbee-meters.json` leaves its flows `unknown`.
- `sign` is where the desired convention is *stated*, so the normalisation in §5 is a declared contract rather than an accident of device wiring. An optional `"invert": true` on a channel covers a clamp that was physically fitted the wrong way round — recorded in RBR's own config so the data stays interpretable even if the Zigbee2MQTT side is reconfigured or lost.

One flow cannot appear twice, and one meter name cannot appear twice: both are load-time errors rather than silent last-one-wins.

## 5. `meters.as` — the module

Started by `controller.as`, released to run concurrently, forked onto its own sampling loop. Read-only: it commands nothing.

**Lifecycle — the important design note.** An AllSpeak module is not a separate process. `run ... as MetersModule` plus `release parent` makes it a *cooperative thread in the controller's own interpreter*, and the controller exits after its six 10-second cycles. So `meters.as` lives at most ~60 seconds per controller run, and is re-started by the next cron invocation. Three consequences, all of which the design has to respect:

- **No long-lived connection and no in-memory continuity.** Anything that must survive belongs on disk. This is cheap here: the meters maintain their own cumulative `energy`/`produced_energy` counters in firmware, so RBR never needs to accumulate anything (§8).
- **Sampling cadence is tied to the controller's 10-second cycle** — `fork` a loop that reads `zigbee-meters.json`, normalises, logs and then `wait 10 seconds`. The `wait` is not optional: a loop without one starves the controller's own threads and the UI, per `reference/11-cooperative-multitasking.md`.
- **The bridge remains the only always-on observer.** It sees every 10-second report whether or not the controller is alive. `meters.as` is the reasoning and logging layer, not the observer. If continuous 24/7 sampling is ever needed, that is a bridge change, not a module change.

**Cadence.** Five different rates are in play, and they are not the same thing. Conflating them is how a stale reading gets mistaken for a quiet house.

| Rate | Owned by | Setting | Why |
|---|---|---|---|
| Report interval | the meter | `update_frequency: 10` | Mains-powered, so airtime is not precious; 10 s is the grid the rest of the system already runs on |
| Ingestion | `zigbee-bridge.py` | event-driven, no rate of its own | Caches every report and stamps `last_seen`; the only process that is always running |
| Sampling | `meters.as` | `wait 10 seconds` | Matches the meter's interval and the control cycle; sampling faster only re-reads the same value |
| Control | `controller.as` | 6 × 10 s cycles, relaunched each minute | Unchanged by this proposal |
| Logging | `powerlog.py` | On change, rounded to 10 W | Change-driven rows with forward-fill on read, the model [HEATING-DATA.md](HEATING-DATA.md) already documents for heating |

10 s is chosen to match `heatlog`, whose rows are written on a change detected at the controller's own per-cycle cadence — so power and heating records land on the *same* time grid, and a join between them needs no resampling. Two further reasons favour it over 60 s: a heat pump's defrost cycles and short cycling are a few minutes long with distinctive power signatures, which a 60-second sample blurs but a 10-second sample resolves; and the PJ-1203A's late-flow-direction bug is bounded to one cycle, so a 10 s interval caps that artefact at 10 s rather than 60 s.

The controller exits after its six cycles and is relaunched by cron, so there is a few seconds of startup gap each minute during which `meters.as` is not sampling. The bridge keeps observing throughout, so nothing is lost — the gap narrows the sampling resolution slightly, and it does not create a hole in the data.

Two verification notes. First, these devices do not all honour `update_frequency` exactly, and `timestamp_a`/`timestamp_b` exist precisely to tell you when a value was *measured* as opposed to published — confirm the real period from those after a day rather than trusting the setting. Second, 10 s is the right default for a reference installation, not a universal law: on a congested mesh (the failure mode `setupRBR.md` describes, where relays intermittently fail to switch), relax it to 30–60 s, since the staleness threshold below scales with the interval.

**Normalisation.** Each sample reads `zigbee-meters.json`, maps it through `meters.json`, and produces a canonical record per flow:

```
Flows[flow] = { watts, ts, age, state, energy, produced }
```

with `state` one of `fresh` / `stale` / `unknown`, and `watts` already normalised to the declared sign convention. Nothing downstream — not the controller, not the logger, not the UI — should ever have to know which meter or channel a flow came from, or which way a clamp was fitted.

**Staleness is not zero.** A meter that has stopped reporting must read `unknown`, never `0 W`. This mirrors the controller's sensor-staleness discipline in `SetRelay`, and it matters more here: a dead clamp that reads 0 W looks exactly like a house consuming nothing, and every derived figure silently becomes plausible nonsense. Threshold: `max(3 × update_frequency, 45 s)` — three missed reports, floored at 45 s so that a momentary Zigbee hiccup at a short interval is not reported as stale. At the 10 s default a meter reads `unknown` after 45 s of silence.

**Message API.**

| Direction | Message | Reply |
|---|---|---|
| controller → module | `{ "request": "flows" }` | `{ grid: {...}, solar: {...}, ... }` |
| module → parent | `Flows` on change | — |

The module pushes on change so the controller can forward flows to the UI, and answers on demand so the dashboard and `diagnose.as` can ask. This is the only coupling between the two, and it is one message shape in each direction.

## 6. `controller.as` — the four-line footprint

```as
module MetersModule                     ! declaration, beside DeviceModule
    ...
if file `meters.json` exists run `meters.as` as MetersModule
else log `No meters.json — power measurement disabled`
    ...
send MeterRequest to MetersModule and assign reply to MeterReadings
```

That is the whole footprint: a declaration, a guarded `run`, and a passthrough that hands flow data to the existing MAP publication unchanged. The guarded `run` follows the `sim` / `deviceControl.as` pattern already at `controller.as:159`, so the shape is not new. `controller.as` never learns what a flow means or how many there are. Anything beyond this belongs in `meters.as` — if a future change needs `controller.as` to understand a *flow*, that is the signal the boundary has been drawn in the wrong place.

## 7. Why the eddi is not integrated

The obvious alternative to clamping `store` is to read it from the eddi. It should not be done, and the reason is decisive rather than a preference:

- **There is no official local API.** The `cgi-*` JSON endpoints that circulate in the Home Assistant community are on myenergi's cloud, requiring internet, a hub serial and an API key from the portal. The vHub is documented as a gateway *to* myenergi's servers, not a local server.
- **The only local option is reverse-engineered.** `mqtt-energi` and similar sniff the device-to-device UDP/multicast traffic on a promiscuous NIC and decode the diverted-power field. It is unsupported, firmware-version sensitive, and its own author flags uncertainty about V5 firmware. myenergi has declined local access for years.
- **The product argument is worse than the technical one.** The moment one flow depends on a vendor integration, RBR grows a support surface for a device it neither controls nor ships — for one flow, on one customer's installation, with no equivalent on the next one. Every customer is different; a common mechanism for all flows is what makes this maintainable.

So `store` is clamped like everything else. The eddi is still useful as a **manual cross-check**: its app shows accumulated diverted energy, so at the end of a sunny day the day's `store` total can be compared against it. That validates the clamp without any dependency on it.

One thing worth confirming on your installation: for a diverter to divert it must detect export, so the eddi is almost certainly already fitted with a grid CT. That means your grid flow is already measured — but in myenergi's cloud, so unusable here. Confirm which CTs are fitted so that the new clamps sit where they add information rather than duplicating a measurement that exists but cannot be read.

## 8. Units, signs and energy

- **Power in whole watts, energy in whole watt-hours.** Both integers, for the same reason temperatures are centidegrees and schedule temperatures hundredths: `ALLSPEAK.md` is explicit that floats are strings in AllSpeak, so fractional values are scaled integers at the edge. The bridge converts the meters' kWh floats to Wh integers once.
- **Canonical signs** are the ones in §1, and `meters.json` declares them (§4). Grid is the only signed flow — a negative grid reading *is* export, and it is the one place where a sign is load-bearing rather than cosmetic.
- **Do not integrate power in RBR to obtain energy.** Take the meters' cumulative `energy` / `produced_energy` counters: they are exact, they integrate at the device's own sampling rate, and they do not drift with the controller's uptime or the 10-second cadence. The power log exists for *instantaneous* power and for provenance — what was measured, when, and by which flow — not to be summed into totals.
- Cumulative counters can regress (firmware reset, Zigbee2MQTT `clear_metering`). Detect a regression and record it as an event rather than emitting a negative energy delta.

## 9. History: `powerlog.py`

A twin of `heatlog.py`, on purpose — the same writer contract keeps one concept in the reader's head:

- `<root>/<Flow>/<YYYY>/<MM>/<DD>.csv`, root named by a `powerlog-root` file in the controller directory (absent = logging off, exactly like `heatlog-root`), with the same symlink pattern for machines without the data partition.
- One atomic `O_APPEND` write per row, spawned by `system background python3 powerlog.py ...` — so rows survive the module thread being killed at the end of a controller run.
- Row per **change**, not per sample: `epochMinutes,watts,state`, with `state` a single letter (`f`/`s`/`u`) so a gap is distinguishable from a genuine zero. Change-driven logging with forward-fill on read is what keeps a year well under a megabyte and is already the documented reading model in [HEATING-DATA.md](HEATING-DATA.md).
- Power is rounded before comparison (to 10 W), so sensor jitter does not manufacture rows — the same reasoning as rounding temperatures to tenths.

## 10. Diagnosis and display

- **`diagnose.as`:** a meters section listing each configured flow, its meter and channel, the last reading, its age and state, plus any meter seen in `zigbee-meters.json` that `meters.json` does not reference (and vice versa). This is where a friendly-name mismatch surfaces, exactly as it does for rooms — the single most likely installation error, and the one `setupRBR.md` already warns about.

  It should also print each meter's `supported` flag and its fingerprint. Both are already available and both are currently dropped: `zigbee2mqtt/bridge/devices` carries `modelID` and `manufacturerName` per device, `_handle_bridge_devices` in `zigbee-bridge.py` keeps only `ieee`, `type`, `model`, `vendor` and `supported`, and `diagnose.as` prints only `type=` and `model=`. So the two fields that identify an unsupported white-label meter are exactly the two that go missing. `supported: false` *plus* the fingerprint is the message that says "this unit needs an external converter", and it belongs in RBR's own output rather than in a Zigbee2MQTT log the installer has to go digging for.
- **`rbr-dashboard.py`:** meter data goes in the `/tmp/rbr-dashboard.json` payload the controller already writes, rendered as a separate flows panel. It is a fixed-column per-room renderer and should not grow flow columns.
- **UI:** a flows view of its own, fed by the MQTT passthrough in §6. Flows are not rooms and should not be squeezed into the room list.

## 11. Rollout

Each step is independently verifiable, and the order keeps a broken step from being masked by a later one.

| # | Change | Proven by |
|---|---|---|
| 1 | Bridge passthrough + `zigbee-meters.json` + `manufacturerName`/`modelID` capture in `_handle_bridge_devices` | `curl localhost:8889/device/Mains-meter` shows per-channel fields while a load is switched, and `/devices` shows the fingerprint |
| 2 | `powerlog.py` | `tests/unit/powerlog_test.py`, matching `heatlog_test.py` |
| 3 | `meters.json` + `meters.as` skeleton: load, sample, normalise, log | a hand-written `zigbee-meters.json` and a `sim` file — no hardware needed, as `simulator.as` already demonstrates |
| 4 | `controller.as` wiring (§6) | controller logs no new errors with `meters.json` absent, and flows appear when present |
| 5 | `diagnose.as` | an unmatched meter name is reported, and each meter shows its `supported` flag and fingerprint |
| 6 | Dashboard panel, then the UI view | — |
| 7 | Shipping: `meters.as` and `powerlog.py` into `TARBALL_FILES` in `rbr-updater.py` and both file lists in `deploy.sh`; `meters.as` and `powerlog.py` into the `controller.service` dependency tuple (the `heatlog.py` precedent); `powerlog-root` into `rbr-setup.sh`; `meters.as`, `powerlog.py`, `meters.json`, `powerlog-root`, `zigbee-meters.json` into `CONTROLLER-FILES.md` | a fresh install and an update both land the files |

Note that `meters.as` is **not** a new service — it is a module inside `controller.service` — so `rbr-watchdog.sh` needs no change.

## 12. Not in this phase

- **Control actions.** Boost the heat pump on surplus, defer the store, schedule the EV charger. This phase measures; acting on it is a separate proposal with its own safety argument.
- **COP.** Electrical input gives running cost, not efficiency. COP needs heat output — a heat meter or the heat pump's own telemetry — which is a different question from this one, and it should be answered on its own merits rather than assumed to follow from a clamp.
- **Tariffs and standing charges.** The data will support it; the model is not here yet.
- **Per-appliance disaggregation.** The bridge will capture smartplug power for free (§3), but nothing consumes it yet.

## Open questions

1. Should `heatpump` be a first-class flow, or an optional extra for installations that have one? (This proposal says first-class.)
2. Where does the flows view live in the new UI — its own screen, or a card on the home screen?
3. Is the low-band accuracy of an 80 A clamp on the `store` circuit acceptable for the analyses intended, or should that circuit get the series-wired DIN meter instead?
