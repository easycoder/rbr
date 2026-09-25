# 2026-09-20

## 11:07

I want to explore the next phase of development. Please read doc/current-measurement.md.

**Assistant**

Read it. The document proposes power-flow monitoring (grid, solar, storage, EV) as the next product phase for all-electric installations, starting with your own system (heat pump, solar, phase-change heat store), and asks how many Zigbee current clamps are needed.

Answer: **4 clamps now (2 two-channel meters), 3 minimum, 6 at full scope.**

Measurement points, counted as circuits rather than rooms:

| # | Flow | Where the clamp goes | Why |
|---|---|---|---|
| 1 | Grid (import **and** export) | Incoming live tail, after the meter/isolator | The only place export is visible; everything else derives from it |
| 2 | Solar generation | Inverter's AC feed (its own MCB) | The number the solar-gain hypothesis needs |
| 3 | Heat pump | HP circuit live, at its MCB | Pairs with existing `heatlog` data — electrical demand vs. delivered heat |
| 4 | Heat store | Immersion / charge spur live | The only "power to storage" flow today |
| — | EV charger | Its own circuit | +1 when it arrives; +3 if three-phase |

With grid + solar you can derive house load, self-consumption and export, but *not* the split into heat pump and store — circuits are additive only if measured. That is what clamps 3 and 4 buy, and the heat pump is the one RBR cares about most, being the only flow that can be joined to the per-room records in `/data/rbr-heating`.

Buy two two-channel bidirectional single-phase meters rather than four single-clamp devices: channel A = grid, B = solar on one; A = heat pump, B = heat store on the second. The Tuya PJ-1203A family (`PC311-Z-TY` white-labels) is the right shape — 2× 80 A clamps, per channel `power_a/b`, `energy_a/b`, `energy_produced_a/b`, `energy_flow_a/b`, `current_a/b`, `voltage`, a `signed_power_a/b` option, and `update_frequency` settable 3–60 s so 60 s matches the controller cycle. Alternatives: Moes ZM6LT1 (1 clamp, `reverse_energy`), NodOn SEM-4-3-20 (3 CTs, DIN, Class 1.0 — best three-phase), Owon PC321 / `TS0601_3_phase_clamp_meter` (3 CTs, but the Zigbee variant is often consumption-only in Z2M — verify the fingerprint).

Purchase gotchas that change the spec, not the count: clamp rating on the tail (check the cutout fuse); bidirectional is not universal (`energy_flow` / `produced_energy` / `reverse_energy` needed for export); the PJ-1203A reports flow direction one cycle late at each produce/consume transition (`late_energy_flow_a/b`, `invert_energy_flow_a/b`, `signed_power_a/b` exist to fix it); ~10 W resolution at ±1–2 %, useless for auditing a 5 W standby load; split-core clamps must go round *one* conductor, tail work means the cabinet is open (electrician), and the radio body should sit outside a steel enclosure — `setupRBR.md` step 5 records that a dongle against metalwork degraded every link in the mesh. Where a clamp cannot answer the question: a DC-coupled hybrid inverter with a battery shows PV minus battery on its AC cable, and a store charged hydraulically from the heat pump has no electrical feed to clamp at all.

Repo-side gaps: `zigbee-bridge.py` already subscribes to `zigbee2mqtt/#` and receives every field, but `_handle_device_update` whitelists only `state`, `temperature`, `humidity`, `battery`, `power`, `energy`, so `power_a/b`, `energy_produced_a/b`, `energy_flow_a/b`, `current_a/b` are dropped, and nothing but temperatures is persisted. Flows are not rooms, so `map.json` has no home for them. `heatlog.py` is the template for a `powerlog.py`; `rbr-dashboard.py` is a fixed-column room renderer needing its own panel.

Asked which of these change the count or the shopping list: single vs three-phase supply, how the store is charged, and how much the first purchase should cover.

## 11:37

1. The heat store is fed directly from an EDDI solar surplus controller. I may be able to get a remote monitoring modue for it, but perhaps simply monitoring current would be more appropriate in this case. The heat store is not charged with hot water from the heat pump - the two systems are completely independent.
2. A separate meters.json would be better, and the code should if possible be run as a concurrent meters.as module to avoid loading up controller.as with stuff that deosn't relate to a conventional gas-powered system. Any communication that is needed between the two can be done with AllSpeak module messaging.
3. There's nothing in these premises that goes anywhere near 80A. The maximum solar output is 3.6KW and the only household item that might occasionally take more than 13A is a dual oven. The heat pump has a rated 10KW output but has a SCOP of at least 3.

**Assistant**

All three answers accepted, and point 1 settles the last open purchase question: clamp it.

**The eddi: clamp, don't integrate.** Your instinct is right, and the reason is decisive rather than a preference. There is no official local API — the `cgi-*` JSON endpoints in circulation are on myenergi's cloud (internet, hub serial, portal API key), and the vHub is documented as a gateway *to* myenergi's servers, not a local server. The only genuinely local route is reverse-engineered sniffing of the device-to-device UDP/multicast traffic (`mqtt-energi` and similar), which is unsupported, firmware-version sensitive, and flagged uncertain on V5 firmware. myenergi has declined local access for years. The product argument is worse than the technical one: one flow depending on a vendor integration means RBR supports a device it neither controls nor ships, for one customer, with no equivalent on the next.

So the store is clamped like everything else, and one clamp site does it: **the eddi's supply feed**, not the element feeds. That single cable carries diverted power and nothing else, so it covers both H1 and H2 in one clamp and survives a store rewire. The eddi's app totals stay useful as an end-of-day cross-check on the clamp — no dependency, just a reference. Worth confirming which CTs are fitted: a diverter needs export detection, so the eddi almost certainly already has a grid CT, meaning your grid flow is measured already — but cloud-locked, so the new clamp sits alongside it rather than replacing it.

That makes it **4 clamps** (grid, solar, heat pump, store), not 3 — and the shopping list is unchanged, because meter 2's B channel was already the spare.

**The design is as you asked**, written up as `doc/PROPOSAL-current-measurement.md`. One correction to the word "concurrent", because it changes what the module may assume: an AllSpeak module is not a separate process. `run ... as MetersModule` plus `release parent` makes it a cooperative *thread in the controller's own interpreter*, so `meters.as` lives at most ~60 seconds per controller run and dies with it. Three consequences, all handled in the proposal: state that must survive goes on disk; the sampling loop is a `fork` with an explicit `wait 10 seconds` (a loop without one starves the controller's own threads); and the always-on observation stays in `zigbee-bridge.py`, which sees every 10-second report whether or not the controller is alive. `meters.as` is the reasoning and logging layer — which is exactly the outcome you wanted anyway, since it keeps power out of `controller.as`. The controller's whole footprint is four lines: the `module` declaration, a guarded `run` (`meters.json` absent = feature off, logged at startup like `heatlog-root`), and a passthrough that hands flows to the existing MQTT publication. `meters.as` is not a new service, so `rbr-watchdog.sh` needs no change.

**On the loads: the 80 A caution is retired.** Solar 3.6 kW is 15 A; the heat pump's SCOP ≥ 3 gives ~3.3 kW electrical seasonal average, though the *circuit* should be sized on worst-case cold-weather input (~4–5 kW, 17–21 A), since SCOP is seasonal and not a peak rail; the eddi is 15.3 A; the dual oven on its 32 A circuit is the largest single circuit at ~17–29 A. With diversity the tail sees 40–55 A. So order the standard 80 A clamps everywhere and do not pay for higher-rated CTs.

The real limit is the opposite end. An 80 A clamp on a ≤ 20 A circuit sits in its bottom quarter, where cheap CTs are least linear — sub-1 kW readings are indicative, not accurate. That bites hardest on `store`, because a diverter modulates continuously and spends its shoulder-hour life in the 0.5–2 kW band. Hence the end-of-day eddi cross-check, and hence the one alternative worth knowing about: a series-wired single-phase DIN meter on the immersion spur is good across the whole range, at the cost of interrupting the circuit and a spare DIN way. Clamp first.

Proposal contents, for review: flow identities and clamp sites; the data path (`zigbee2mqtt → zigbee-bridge.py → zigbee-meters.json → meters.as`); the bridge passthrough and why it needs no knowledge of `meters.json`; `meters.json` shape and why the sign convention is *declared* there; the module's lifecycle, normalisation, staleness rule (a dead meter reads `unknown`, never `0 W`) and two-way message API; the four-line controller footprint; why the eddi is not integrated; units and signs (whole watts and Wh, integers at the edge, no integrating power in RBR — the meters' own counters are exact); `powerlog.py` as a `heatlog.py` twin; diagnosis and display; an eleven-step rollout with the shipping lists (`TARBALL_FILES`, `deploy.sh`, the `controller.service` tuple, `CONTROLLER-FILES.md`); and what is deliberately out of scope (control actions, COP — electrical input is running cost, not efficiency, and needs heat output to become COP — tariffs, disaggregation).

Three open questions are listed at the end of the proposal: whether `heatpump` is first-class or optional, where the flows view lives in the new UI, and whether the store's low-band accuracy justifies the DIN meter. Also added a single pointer line to `doc/current-measurement.md`.

## 11:49

Almost in passing we seem to be talking about a 10s reading frequency. Did I read that corrently - it sounds about right to me.

**Assistant**

Correct — and your question exposed a contradiction in my own proposal, which I have now fixed.

Yes: 10 s, and it appeared twice with two different numbers. §3 said `update_frequency: 60`, and its stated justification ("matching the controller cycle and the heatlog cadence") was wrong twice over, because the controller cycle is 10 s, not 60. §5 said the sampler waits 10 seconds and that the bridge sees "every 10-second report". The proposal only implied the cadence rather than stating it, which is exactly why the two lines drifted. §3 now says `update_frequency: 10`, and §5 has an explicit cadence table so there is one place to check.

Five different rates are in play, and they are not the same thing:

| Rate | Owned by | Setting |
|---|---|---|
| Report interval | the meter | `update_frequency: 10` |
| Ingestion | `zigbee-bridge.py` | event-driven, no rate of its own |
| Sampling | `meters.as` | `wait 10 seconds` |
| Control | `controller.as` | 6 × 10 s cycles, relaunched each minute |
| Logging | `powerlog.py` | on change, rounded to 10 W |

10 s is right for three reasons. It matches `heatlog`, whose rows are written on a change detected at the controller's per-cycle cadence, so power and heating records land on the same time grid and a join needs no resampling. It resolves a heat pump's defrost cycles and short cycling, which are a few minutes long with distinctive power signatures — a 60-second sample blurs them, a 10-second sample shows them. And the PJ-1203A's late-flow-direction bug is bounded to one cycle, so 10 s caps that artefact at 10 s rather than 60 s.

Two nearby 60s that might look like the same number: the controller's run lifetime (~60 s, then cron relaunches it), and the once-a-minute `heatlog-state.json` flush. Neither is a measurement interval. The "10 W" in the logging row is a rounding threshold, not a period, so it is unrelated to the 10 s — worth separating since both numbers are 10.

Two caveats now recorded in the proposal. These devices do not all honour `update_frequency` exactly, and `timestamp_a`/`timestamp_b` exist precisely to say when a value was measured rather than published, so the real period should be confirmed from those after a day rather than assumed. And 10 s is the reference default, not a universal law: on a congested mesh — the failure mode `setupRBR.md` describes, where relays intermittently fail to switch — relax it to 30–60 s, because the staleness threshold scales with the interval.

While checking that, I also tightened the staleness floor from 90 s to 45 s, and corrected its rationale. At a 10 s interval the old floor meant nine missed reports before flagging a meter as `unknown`, which is too lenient for meters that matter to a control decision; 45 s is three missed reports with room for a hiccup. The rule is now `max(3 × update_frequency, 45 s)`.

## 11:55

Let's pause at this point. I'll get some current clamps ordered; when they arrive we can continue.

**Assistant**

Paused, awaiting hardware. State of the working tree: two new files (doc/PROPOSAL-current-measurement.md, conversation/conversation-006.md) and one modified line in doc/current-measurement.md (a pointer). Nothing committed — say the word if you want that done before you stop.

Shopping list when you order: two two-channel bidirectional meters (Tuya PJ-1203A / PC311-Z-TY family), standard 80 A clamps. Verify the fingerprint (`_TZE204_81yrt3lo`, `_TZE284_81yrt3lo`, `_TZE200_rks0sgb7`) before buying, check the cutout fuse rating, confirm there is a 13 A socket within CT-lead reach of the board, and plan to mount the meter bodies outside the steel enclosure. Clamp sites: grid = incoming live tail; solar = inverter AC feed; heat pump = its MCB; store = the eddi's supply feed.

Zigbee2MQTT settings to apply on arrival, per §1 and §5 of the proposal: `update_frequency: 10`, `signed_power_a/b: true`, `late_energy_flow_a/b: true`, `invert_energy_flow_a/b` if a clamp is fitted the wrong way round, and calibration of each channel against a reference. Then confirm the real reporting period from `timestamp_a`/`timestamp_b` rather than trusting the setting.

Work that needs no hardware, if you want to use the waiting time: rollout steps 1–3 (bridge passthrough and `zigbee-meters.json`, `powerlog.py`, then `meters.json` and the `meters.as` skeleton). Step 1 can be exercised by publishing a synthetic meter-shaped payload to `zigbee2mqtt/<name>` rather than waiting for a clamp, and step 3 by a hand-written `zigbee-meters.json` and a `sim` file — the same route `simulator.as` already uses.

Still open, from the end of the proposal: whether `heatpump` is first-class or optional, where the flows view lives in the new UI, and whether the store's low-band accuracy justifies the series-wired DIN meter for that one circuit. None of the three blocks the order.

## 12:11

Amazon offer the Lioaeust 1118674174 dual-channel 0.2A-80A sensor at an attractive price. Users say it's fiddly to set up with Home Assistant but state it to be Z2M-compatible. Any comment?

**Assistant**

The class is right; the listing cannot tell you the one thing that decides it, and there is a functional trap inside that class.

Lioaeust is not a manufacturer — it is a reseller brand (a US trademark held by Shenzhen Yafex E-Commerce). Zigbee2MQTT matches Tuya devices on `TS0601` **plus the `manufacturerName` fingerprint**, never on the model string, so no "Lioaeust" fingerprint exists and the brand tells you nothing about the module inside. The 0.2–80 A dual-channel bidirectional spec does match the Tuya PJ-1203A family the proposal is built on, so the description identifies the right class of hardware.

The trap: that class contains two Z2M device definitions, and they differ in exactly the field that matters for one flow.

| Z2M device | Direction exposes | Usable for |
|---|---|---|
| Tuya `PJ-1203A` | `energy_flow_a/b`, `energy_produced_a/b`, `signed_power_a/b` | all four flows |
| Tuya `2CT` | none — `energy_a/b` (consumed only), no flow, no produced energy, no signed-power option | `solar`, `heatpump`, `store` — **not** `grid` |

Both are sold under the same "bidirectional 80 A" description. Only `grid` needs direction, because import and export are the same cable; the other three are single-direction flows where a magnitude suffices. So a consumption-only unit is a false economy in the `grid` position and perfectly good everywhere else.

So: **buy one, prove it, then buy the second.** Pair it, read the fingerprint from the Zigbee2MQTT log, and confirm three things before ordering its twin — `supported: true`, `energy_flow_a` is exposed, and `energy_produced_a` increments while the house is exporting. An unsupported fingerprint is recoverable with an external converter in `data/external_converters/` (auto-loaded since Z2M 2.0.0), but that is per-device work that cannot be shipped generically for an unknown brand, so it belongs in the buy-one-first plan rather than in the hope that it just works. Amazon's easy returns are an argument in the listing's favour over AliExpress for exactly this reason.

On the "fiddly with Home Assistant" reports: most of that noise is the HA add-on shipping a stale `zigbee-herdsman-converters`, which is not RBR's situation — `rbr-setup.sh` clones Zigbee2MQTT from git master and builds it, so converter support arrives as soon as it is merged upstream. Nothing about an *unknown* fingerprint is fixed by that, though, and the mirror-image cost is that the converter set is unpinned, so the same controller rebuilt a year later is not running the same code.

Two consequences folded into the proposal: a new §1 subsection recording the fingerprint rule and the PJ-1203A-versus-2CT trap, and an addition to §10 — `diagnose.as` should print each meter's `supported` flag and fingerprint, because `zigbee2mqtt/bridge/devices` carries `modelID` and `manufacturerName`, `_handle_bridge_devices` keeps only `ieee`, `type`, `model`, `vendor` and `supported`, and `diagnose.as` prints only `type=` and `model=`. The two fields that identify an unsupported white-label meter are the two that currently go missing. Rollout rows 1 and 5 updated to carry that.

## 18:05

I'd like to start preparing some comprehensive documentation on RBR as a software product that uses standard off-the-shelf hardware. It will cover the basic concept, system preparation, installation and the software itself. The target readership might be technical but should also be aimed at those in the industry of providing heating solutions.

To this end, an observation. Modern housing developments are frequently incorporating solar panels and heat pumps, but there seems as yet to be little overall strategy from the Government to make this happen consistently. Politics may encourage or discourage such a strategy in the short term (<10 years) but in the long term it is probably inevitable. A more optimised approach to heating will be one consequence. Houses are already fitted with radiators in each room, but room by room control is rarely considered. A step towards this would be to supply powered radiator controllers and thermometers in each room and a master controller similar to that of RBR. It's also likely that many houses will come prefitted with an Internet router. This is all rather like the gradual inclusion of heaters and radios in cars during the 20th century. Things that were previously extras become standard in order to gain market share.

For this to happen there must be workable solutions on offer and the will to fit them, so our documentation should clearly illustrate the path we are already offering.

At the moment I'm faced with a blank sheet of paper, so any suggestions on how to get started will be welcome.

**Assistant**

I read the repo end to end. Reframed it: this is not a blank sheet — RBR has a lot of documentation already, but it is inward-facing (written by the developer, for the developer). What is missing is the reader-facing layer.

Inventoried the existing material: `README.md` (concept fragments, components, appliance idea, cost/payback claim); `doc/setupRBR.md` (near-complete install + commissioning, with excellent callouts); `doc/setupHardware.md`, `doc/configurator.md`, `doc/setupIXHUB.md`; `doc/CONTROLLER-FILES.md`, `UPDATE-MECHANISM.md`, `HEATING-DATA.md`; `doc/current-measurement.md` + proposal; `AI/*.md`; `design/handoff/*`.

Gaps identified: (1) any concept/argument piece for someone in the heating trade; (2) the operator side of the software; (3) a glossary; (4) a bill of materials; (5) anything addressing the managed-estate model that `README.md` says is central. Two existing habits worth carrying over: the blockquote callouts and the explain-the-why tone.

Proposed a layered structure mapped onto the four headings the user gave: Concept (industry), Preparation (installer), Installation (installer), Operation (operator), plus a Technical layer (developer) and an Appendix. Landed as a `docs/` tree:

[code omitted]

Provenance to avoid writing anything twice: Concept is new; Preparation and Installation are a re-cut of `setupRBR.md` and `setupIXHUB.md`; Operation is new (walk the running UI); Technical is a lift of `AI/` and `doc/` with uniform front-matter; Appendix is new.

Proposed how to start: write `docs/README.md` (the reading map), then `concept/01-why-room-by-room.md` (the anchor, using the car-heater/car-radio analogy and the solar + heat pump + router argument), then `appendix/glossary.md` alongside it, then re-cut `setupRBR.md`, then the operation layer, then technical last. Conventions to fix first: front-matter per document (audience/status/last-verified); jargon discipline in the top three layers (no AllSpeak, MQTT, Webson or Zigbee2MQTT names); British English; one doc, one job; keep the callout style.

Flagged one thing to decide later: the README's "about a fifth of the annual running cost" and "saves 10%+" are strong claims for a trade audience with two installations, so framing those as indicative is worth more than a big number; and compliance/integration (building regulations, boiler interlock) is a gap the industry reader will ask about.

Asked three decisions via the ask tool: where the docs live and how they are published; which document to write first; and how the audience is packaged.

## 19:03

Yes, I'd like to see thoe.

**Assistant**

Scaffolded. Both earlier decisions held: a new `docs/` tree in this repo as plain Markdown, layered volumes per reader with a shared concept core, and the concept anchor written first.

Created under `docs/`:

[code omitted]

**`docs/README.md`** — the reading map. Four role-based paths (industry / installer / operator / developer), the full document map with a status column, the writing conventions (metadata line, four audiences, plain-words rule above the technical layer, one-doc-one-job, callouts, British English), and a table drawing the boundary between this tree and `doc/`/`AI/`.

**`docs/concept/01-why-room-by-room.md`** — the anchor. Sections: the house has changed and the controls have not; why per-room control is the next step (waste, and heat pumps rewarding gentle demand); why it has not happened (nobody owns the problem, plus no settled strategy, with the short-term/long-term split the user made); the path cars took; the two bars a workable solution must clear (installable by a heating engineer, supportable at estate scale); where RBR fits; and "what we are not claiming yet".

**`docs/appendix/glossary.md`** — grouped: the system, devices and wiring, radio/network/messaging, modes and scheduling, people and roles, and "things that look like faults but are not". Each entry links to the layer that expands it.

Three judgement calls highlighted for review: the concept doc leads with Zigbee and never names MQTT, AllSpeak, Webson or Zigbee2MQTT (those appear only in the glossary and technical layer, with RBR-Now filed as legacy); the "what we are not claiming yet" section states the two-installations limitation, the compliance gap and the policy stance explicitly; and the broken links in the reading paths are intentional, pointing at planned documents that the map below marks as not yet written.

Offered the next step: continue with `concept/02-what-rbr-is.md` and `03-a-fitted-house.md`, or re-cut `doc/setupRBR.md` into the installation layer first so the voice-change can be seen.

## 19:16

That's a very good kick-off. One point I should note: For most of my projects I copy .md files to my Doclet structure for easier (and remote) viewing. I would like to ensure that in files such as why-room-by-room.md, paragraphs are not broken into individual lines but rendered as continuous text. This ensures that when converted to HTML they render as paragraphs. Maybe this needs to be a permanent instruction in AGENT.md.

**Assistant**

Noted that this is the same principle the repo already applies to `.as` doc blocks ("One paragraph = one line"), so made it explicit for Markdown and applied it to the new documents.

Reflowed `docs/README.md`, `docs/concept/01-why-room-by-room.md` and `docs/appendix/glossary.md`: every prose paragraph and every list item is now a single unbroken line. Headings, tables (one row per line), blockquotes and fenced code blocks kept their own line structure. The concept document's metadata blockquote was three hard-broken lines and is now one.

Recorded as a permanent rule in `AGENT.md` — a new section, "Markdown documentation — one paragraph, one line", covering the one-paragraph rule, one-line list items, which structures keep their line layout, and the single-line metadata blockquote. It notes that it is the Markdown counterpart of the existing `.as` doc-block rule, so the two read as one policy. Also added the same rule to `docs/README.md` as a conventions bullet, so it travels with the docs.

Flagged two things about applying it: existing `.md` files (`doc/setupRBR.md`, `setupHardware.md`, `UPDATE-MECHANISM.md`, the `AI/` files, and most of `AGENT.md` itself) predate the rule and are still hard-wrapped, and the new AGENT.md section says to reflow them as they are touched; and a blanket mechanical reflow is not safe on those files, because `setupRBR.md` uses 4-space-indented code blocks, indented blockquote callouts and nested lists that a simple join would flatten. The three reflowed documents had none of those, so the transform was clean.

Saved the requirement as a durable project fact. Offered the next step: continue with `concept/02-what-rbr-is.md` and `03-a-fitted-house.md`, or reflow the existing `doc/` files first so the whole set behaves the same in Doclet.

## 19:22

I'd like to see the current files reflowed so I can study them more carefully before continuing.

**Assistant**

Scoped it with one question (the scope decision: all repo documentation except the conversation logs, chosen by the user). Reflowed 19 files; `conversation/` left untouched as verbatim records.

Changed — prose paragraphs and list items now one line each: `AGENT.md`; `doc/` (`setupRBR.md`, `setupHardware.md`, `setupIXHUB.md`, `CONTROLLER-FILES.md`, `UPDATE-MECHANISM.md`, `HEATING-DATA.md`, the four `PROPOSAL-allspeak-*.md`, `PROPOSAL-current-measurement.md`, the ESPHome conversion note); `AI/WORKING_RULES.md`; `design/handoff/README.md`, `slices/03-room-row-rest.md`, `slices/08-background.md`; `desktop/README.md`; `resources/as/README.md`.

Already compliant and left alone (about twenty files), because their paragraphs were single lines already: `README.md`, `ALLSPEAK.md`, `AI/ARCHITECTURE.md`, `AI/MAP_FORMAT.md`, `AI/PROJECT_OVERVIEW.md`, `AI/EXAMPLES.md`, `AI/ALLSPEAK_AND_WEBSON.md`, `design/handoff/TOKENS.md`, the remaining slices, `doc/configurator.md`, `RBRNow/README.md`, `tests/setup-spec.md`.

Rather than trust the transform, verified every changed file: fenced code blocks byte-identical before and after; the full sequence of words identical (no prose lost, added or edited); headings, table rows and horizontal rules unchanged in number and text. The only word-level difference anywhere is in `doc/current-measurement.md`, and it is the "> For how this could be built…" line added before this session, not from the reflow.

`doc/setupRBR.md` was the one file needing care, with nested bullet lists and callouts indented inside the numbered steps. Those are preserved and now join correctly. A first attempt misclassified one indented callout as an indented code block; the verification caught it, the tool was fixed and re-run. A second pass changes nothing, so the result is a stable fixed point. Nothing else in the repo was touched. Offered to continue with `concept/02-what-rbr-is.md` and `03-a-fitted-house.md`.

## 19:43

Before you do, something I omitted from my initial brief, that may be appropriate for consideration in Why RBR?
RBR has been under intermittent development since 2020 and has undergone several revision. In about 2021/2 several similar systems started to be heavily advertised, from such as Honeywell and Drayton. However, they are now notably absent. What went wrong? My view is they were too complex, from the point of view of the house owner having to install one. Multiple connections to the wifi router will have been at the top of the list. If this complexity was indeed responsible for the poor take-up, there's a lesson to be learned. RBR is intended to be preconfigured before delivery, and when implemented by a housing association (for example) offers help and even remote management; something the other systems didn't. In the early days of such systems, having someone to ask is important.

**Assistant**

Checked the factual premise before writing, because the document names real companies and goes to the trade. It does not hold: neither Honeywell Home evohome nor Drayton Wiser has been withdrawn — both are still sold in the UK and were refreshed in 2025 (evohome gained a new R9H control module; Wiser launched a 2nd Generation range with Matter). Where "discontinued" listings appear, the cause is the EU Radio Equipment Directive cybersecurity rules retiring older SKUs plus generational refreshes, not a market exit.

The underlying argument, though, is well supported, and by better evidence: Drayton's own installer survey puts hard-to-install products as the commonest cause of job delays (64%), compatibility issues at 44%, and a quarter of installers unable to reach manufacturer support; a DECC study concluded advanced heating controls are often too complex and non-intuitive, with 70% of homes lacking the controls building regulations already recommend; smart thermostat penetration is only about 14-21% after a decade, while 50% of householders say they want room-by-room control.

Asked how to handle the brands; the user chose not to name them and to describe the first wave generically.

Added a new section, "Learning from the first wave", placed between "The path cars took" and "What a workable solution has to do" so that it lands as the bridge into the two bars. Four paragraphs: room-by-room control is not new and the marketing did not produce take-up; the evidence points to friction at installation (installer surveys and government studies agreeing); what is hard is the network rather than the plumbing, and the cost and fiddling land before any benefit because the saving needs every radiator fitted; and the lesson — demand was never the problem, what was missing was a system that arrives ready to work and someone the household can ask.

Also made two smaller edits: trimmed the duplicated "works only until the router is replaced" motif out of "Why it has not happened yet", since the new section now makes that point with evidence; and added the "in development, on and off, since 2020 — through several revisions" line to "Where RBR fits". Verified the document still has every paragraph on a single line and the section order is intact. Noted that the underlying sources exist and can be cited if a more formal register is wanted. Offered to continue with concept/02-what-rbr-is.md and 03-a-fitted-house.md.

## 20:23

That reads very well. It's good to see what I had as a gut feeling confirmed by available evidence.
Yes, please continue with concept/02 and /03

**Assistant**

Wrote both, following the conventions (single-line paragraphs, metadata line, plain words above the technical layer).

`docs/concept/02-what-rbr-is.md` — the product in plain terms: in one sentence; the three parts (the controller computer, the room devices, the app); what it does day to day; what it is not (not new heat, not the wider smart home, not something the household has to run); why it is built this way, with the four choices framed as direct answers to the first-wave lesson (off-the-shelf parts, uses the network that is already there, arrives ready, can be managed from elsewhere); and what happens when a thermometer goes quiet. The two sections I added beyond the obvious outline are deliberate: a scope section ("what it is not") and a failure-behaviour section, because those are the first two questions a trade reader asks — what does it replace, and what happens when it breaks.

`docs/concept/03-a-fitted-house.md` — what it looks like in a property: what the household notices (very little); what is fitted and where; a room at a time (kitchen, bedrooms, spare room, bathroom); what the boiler sees (demand from rooms, not a house-wide call); how a house gets one, separating the retrofit route from the new-build one; and buildings and estates.

Two deliberate restraints. First, mechanical detail is deferred to the installation section rather than invented — I do not have the exact valve hardware in front of me, so the documents say "a powered valve, switched by a relay" and point forward. Second, both documents keep the plain-words rule: no MQTT, AllSpeak, Webson or Zigbee2MQTT.

Updated `docs/README.md`: the map now marks `02` and `03` as drafts, and the status paragraph says four documents are drafted. Verified both new files have every paragraph on a single line and the section order intact. Offered to continue with concept/04 (deployment and roles) and 05 (costs and payback), or to start re-cutting `doc/setupRBR.md` into the installation layer.

## 21:48

Documents /02 and /03 refer to the need to pair devices on installation. Although I haven't done  live test I believe it's possibe to do all the pairing before delivery. On that day, the thermometers, actuators and relays get fitted and wired up, while the controller is connected to the house router, often by a cable so no configuration is needed. The devices can already have been named and the system map set up with those names. The MAC address of the controller will already be known, ready to be input to the PWA on the user's device.

This requires the householder to provide room names beforehand, so we may create an online form to collect this information.

**Assistant**

Treated it as a substantive correction rather than a rewording, and changed the three places that described pairing as on-site work.

`concept/02` — the "It arrives ready" bullet now says the devices can be paired and named, and the rooms and schedules laid out, before the unit is delivered, and that the day itself is mechanical: fit and wire the devices, connect the controller to the router, in most homes by cable, so nothing about the network is settled on site.

`concept/03` — both routes in "How a house gets one" now pre-pair. The retrofit route says the devices can be paired and named before the unit reaches the house, leaving a visit of fitting, wiring and connecting the router. The new-build route says units are paired, named and prepared before delivery. Both now carry the room-name point, using the reasoning given: a room-by-room system needs the room count in any case, so naming them is the natural next step, and it is what the devices are named after. The controller's address is stated as known before delivery, so the app can be pointed at the house straight away.

`appendix/glossary.md` — the "Commissioning" entry now says pairing is usually done before the unit is delivered.

Structural consequence flagged and decided (the user chose option 2): pre-pairing is described in the preparation layer, while the installation layer keeps a pairing step as the fallback for devices that arrive unpaired, which is still what `doc/setupRBR.md` describes today. Reflect accordingly: added `preparation/05-preparing-a-unit.md` (room names in, then pairing, naming and the map — the pre-delivery build) to the document map, retitled the installation pairing row to "Pairing on site, for devices that arrive unpaired", recorded the room names in the prerequisites row, and inserted the new document into the installer reading path.

Two things left open in the reply: the pre-pairing route is untested, so offer to mark it provisional in the document if wanted; and the online room-name form is not asserted in the public documents because it does not exist yet — offer to record it as the intended collection route when `preparation/05` is written.


## 21:50

OK, that's fine for today. I'll resume at the next opportunity and in the meantime study progress so far.

**Assistant**

Session closed. Summarised where the work stands so it can be resumed cleanly: five documents drafted under `docs/` (the landing page, `concept/01`, `concept/02`, `concept/03` and the glossary), the reader-facing tree scaffolded and separated from `doc/` and `AI/`, and the whole existing `.md` set reflowed to one-paragraph-per-line for Doclet. Restated the three decisions taken (layered volumes per reader; no brand names in the first-wave section, with the reason; pre-pairing documented in preparation with an on-site pairing fallback in installation). Restated the two open items to think about: whether to mark the untested pre-pairing route provisional, and whether the planned room-name form should be described as a committed feature. Noted the next steps: `concept/04-deployment-and-roles.md` and `05-costs-and-payback.md`, then the re-cut of `doc/setupRBR.md` into the installation layer. Saved a resumption note as a durable project fact.

## 09:07

Cars, computers and smartphones are products, with consistent and recognisable feature sets. Cars have wheels, engines and seats. Computers have a processor, memory, a screen, a keyboard and a pointing device. Smartphones add haptics.

Human buyers of these products are aware of all these things, but it's not foremost in our minds when we choose which product to buy. We are driven by emotion more than by facts and logic. For a car, it's the brand. BMW, Fiat and Ford present basically the same product, but buyers have an intense preference for one over another. Computers  are recognised as Windows, Apple or Linux; smartphones as IOS or Android. What we see is not just a product; it's a user experience. This can be regarded as the very top layer of the pyramid.

A heating system is a product. A system built now uses essentially the same hardware elements as previous commercial systems that have failed to gather momentum. What matters is not the hardware but the user experience. RBR aims to succeed where others failed, by addressing the user experience, not the hardware. This is done in part by using standard hardware, but mostly by paying close attention to how the user views the system. We avoid the generalist approach of Home Assistant by offering a UI that's specifically matched to the task performed. We use a programming environment that makes it as easy as possible to adapt to changing requirements and fashions. And we use AI, not human coders, because we can move far more quickly to fix issues, add new features and take advantge of new developments.

Can w reframe the 3 documents in line with this?

**Assistant**

Treated it as a spine change rather than a polish: the concept layer previously argued from the hardware up, and now argues from the layer above it. Asked two decisions, both answered.

Decision 1 — how to apply the frame: a short framing document as the new first concept document, with the others reoriented around it. Decision 2 — the AI claim: reframed around the reader's benefit (speed and adaptability) rather than "AI, not human coders".

Wrote `docs/concept/00-the-experience-is-the-product.md`: the car/computer/phone analogies; the pyramid with the hardware taken for granted and the choice made at the top; a heating system is a product, and the hardware layer is now settled (much the same parts as the systems that never gathered momentum); those systems stalled a layer above, asking the household to be its own installer, network administrator and support desk. Added a section the analogies force but the brief did not name — "The awkward part: no brand": the car/computer/phone examples are all brand choices, and a new entrant cannot borrow that, so the experience itself and whoever stands behind it have to take the brand's place. Then RBR's three commitments: an interface built for one job (not a generalist home-automation platform — Home Assistant deliberately unnamed, consistent with the no-competitor-names precedent); a system written to be changed; and built quickly, fixed quickly (AI assistance, stated as the consequence for the buyer).

Reoriented the others rather than rewriting their substance. `02` now runs: what it is like to use — what it is not — why it feels that way (the four choices restated as the experience each buys) — when it cannot sense a room — what is underneath (the three parts, demoted). `03` now leads with what the household notices and a room at a time, and the equipment list moved to a closing "Where the equipment goes" section, narrowed to placement so it no longer duplicates `02`. `01` kept its per-room case and gained a pointer up to the frame plus a line making explicit that the two bars are experience bars.

Updated `docs/README.md`: the frame joins the document map and the industry reading path, and leads the "where to start" note for every reader. Verified: every paragraph still on one line; 44 links resolve; the only unresolved ones are the documents not yet written.

Noted for the user: naming BMW/Fiat/Ford and Windows/Apple/Linux illustratively is fine and is his own framing, whereas the earlier no-names rule was about not asserting a competitor's failure (Honeywell/Drayton) — a different case. Refreshed the resumption fact with the new organising idea.

## 09:14

If it helps, I'm happy to honestly achnowledge that the availability of a common platform could - and probably should - present opportunities for others to compete, in the same way as Windows and Linux on identical hardware. There's no point in claiming RBR has all the answers for all time. Competition is the sign of a healthy market.

**Assistant**

Added it to the framing document as a new section, "A common platform, and the competition it invites", placed after "What RBR does about it" and before "The test this sets". Two paragraphs: that standard parts are a position rather than a procurement convenience, and that this settles where the competition belongs — Windows and Linux on identical hardware, competing on what sits above it, so on much the same parts the argument becomes how each system behaves, how it is fitted and who supports it; and that this is a market worth having competitors in, that RBR does not claim the answers for all time, and that a common platform others can build on differently or better is what a healthy market looks like rather than a lock-in.

Noted in the reply that this pairs with the earlier "The awkward part: no brand" section: those analogies are brand choices, so a newcomer must earn the promise a different way, and because the hardware is deliberately common the competition happens at exactly the layer where that promise is made. Confirmed the section order and that every paragraph is still a single line. Offered the same next steps: concept/04, concept/05, then the installation re-cut.

## 09:38

One small item: In What is underneath
"Underneath, RBR is three things working together, and only one of them has to be in the house."
Both the controller and the controlled items have to be in the house. The UI can be anywhere.

**Assistant**

Corrected it in `docs/concept/02-what-rbr-is.md`: the sentence now reads "the controller and the room devices are in the house, and the app can be anywhere". Searched the rest of `docs/` for the same claim — the other matches are unrelated (01 on the pieces already being in the house; 03 on where the equipment sits), so this was the only place it was wrong. Noted that the error came from an earlier draft phrase, "the only part that has to live somewhere specific", which was about the controller needing a spot near the router and got flattened into a claim about being in the house.

## 09:44

OK, let's do the next section.

**Assistant**

Wrote `docs/concept/04-deployment-and-roles.md`, the next document in the agreed order. Sections: "Five jobs, however they are shared" (preparing the unit, fitting it, commissioning it, operating it, standing behind it); "A single home"; "A provider's stock"; "Where each job lands" (a table assigning each job in each of the two cases); "The one thing the household has to supply"; and where next.

Choices made and why. The document is built around jobs rather than job titles, because in a small job they collapse into one firm, so the roles are defined by what has to happen and not by who is called what. "Standing behind it" is given equal standing with the technical jobs, because it is the job the framing document says has to substitute for a brand. The provider section was deliberately kept to who does what and defers what it is like from the outside to `03-a-fitted-house.md`, which already covers grouping, remote spotting and what the resident may be given — otherwise the two documents would say the same thing twice.

Introduced the term "the supplier" for whoever prepares the unit before delivery (pairs and names the devices, binds rooms, builds the plan, records the address). Flagged it to the user as a naming choice: it is now a term that will recur across preparation, installation and operation, so if another name is preferred it is cheapest to change now.

Consequential consistency fixes: the glossary's "Commissioning technician" entry said the role pairs the devices and configures rooms in the app, which the pre-pairing model had already made wrong — reworded to the on-site check. Added a "Supplier" entry and tightened "Installer". Marked `04` as drafted in `docs/README.md`, and the status line now counts six documents. Verified: every paragraph on a single line, and no links broken (the only unresolved links are documents not yet written).

## 10:03

Concept/04 Is fine. 
"the supplier" and "the installer" are as good as any.
Costs are indeed subjective. I have no historical records, partly because there is no "before" and "after" data for either of the installations. However, some very rough guesses can be made. The easiest is to consider which radiators are likely to be manually turned on and off in a typical household. Some people are more diligent than others, but in most households, particularly in those where there are children, the likeihood is that rooms will frequently be left on during the day even though everyone is out at work or in school. We can guess at somewhere between 10% and 30% of the time, maybe, and apply this to one or two rooms for the most part. The saving also depends on how carefuly the householder adjusts the settings on a conventional timer/thermostat.
What I'm saying is that this has as much to do with human psychology than with measurement. What we can be reasonably sure of, however, is that there is a benefit to be gained. We just can't be sure how big this benefit will be in all cases.
So on with Concept/05.

**Assistant**

Wrote `docs/concept/05-costs-and-payback.md` to match the guidance: the benefit is real, its size is not knowable from the data. Sections: the cost side; where a saving comes from; why there is no figure to quote; what can be said; how a figure would be established; where next.

The document's spine is the point made in the brief. The saving is not a property of the system but of the household — a household that already turns radiators down gains almost nothing, one that does not gains a lot — and installing the system removes the very behaviour it would be measured against, so the counterfactual is unobservable after the fact. There is a second and smaller effect on the plant, which is noted but not leaned on. The 10–30% estimate is used where it belongs: as a statement about the waste (one or two rooms left heated for between a tenth and a third of the day), not as a percentage saving, and the document says outright that anyone quoting one percentage for every home is guessing. Payback is stated as a condition rather than a promise — a comfort purchase at the diligent end of the range, potentially self-financing at the other end. And it sets out what a publishable number would need: matched houses, a control group, a heating season, households not selected for keenness.

Two consequential fixes. `01`'s "What we are not claiming yet" said the running-cost figures were "measured on those two" installations, which contradicted the no-before-and-after position — reworded, and it now points at `05`. And, with the user's agreement, softened the repo `README.md`, which claimed the system costs "about a fifth of the annual running cost" and "can save 10% or more ... pay for itself in the first couple of years": those sentences are replaced with the cost shape (ordinary trade items, fitted like any other controls work, a modest one-off) and the statement that the saving depends on the household and has no single figure, with a link to `05`. Checked the rest of the repository for the same claims — the only remaining mentions are in `05` itself and in this log.

Flagged one thing left alone deliberately: the same README sentence still describes the hardware as "BLE and WiFi-connected modules", which is stale — every new build is Zigbee-only. The user asked for the figures specifically, so it was left, and one word would fix it. Marked `05` as drafted and recorded the concept layer as complete in `docs/README.md`.

## 10:14

A further thought about cost savings and human psychology. Bear it in mind, and if it seems relevant make a nod towards it.
If information is presented prominently about cost (or danger), people often willingly adapt their behaviour to minimise it. For example, I often drive with the averge fuel consumption reading showing on the dash, and this tends to make me drive more steadily, anticipate braking and so on. Similarly, I record my daily and monthly consumption of electricity and this affects my willingness to be profligate. Of course, people vary. The very rich care little about the cost of everyday things; they drive fuel-hungry cars and leave the heating on all the time. But they are not our market. For most of us, the cost of living is an issue, and if the heating system encourages a change in behaviour many will be grateful for the advice given and will adapt accordingly. It's all part of careful, healthy living.

**Assistant**

Judged it relevant and added it to `05-costs-and-payback.md` as a third mechanism in "Where a saving comes from", after the behavioural one and the plant one: cost shown plainly changes what people do — the live fuel-consumption readout, the daily meter reading — so a system that makes a household's own consumption visible turns a quarterly bill into something the household can see itself influencing. A second short paragraph keeps it honest about who does not respond: the households for whom the cost is immaterial, who are not the market, with the point landing on the fact that for most households the cost of living is a live concern and a system that makes consumption visible offers something they can act on — the same instinct as eating sensibly or driving steadily.

Why there: the document already argues the saving is a property of the household rather than the system, so a mechanism that improves the household's behaviour belongs with the others rather than in a section of its own, and it strengthens the argument instead of complicating it.

Two wording restraints. The nod is grounded in the record that already exists — each room's demand and achieved temperature are logged — so it claims a presentational step rather than a new instrument. And it claims visibility of consumption, not of pounds, because turning usage into money needs a price assumption; displaying actual cost room by room is where the planned power-measurement work points. Flagged that connection in the reply.

## 11:21

I have a problem with the kitchen plinth relay disappearing. Originally it was a loose wire, but now, just repowering it brings it back, so there's something else happening. Can we try to find out what?

**Assistant**

Opened the controller's own broker (192.168.1.20:1883 — mosquitto plus the Zigbee2MQTT tree) and measured live rather than inferred.

Findings, over a 40-minute window:

| check | Kitchen-plinth | every working relay |
|---|---|---|
| z2m availability | offline | online |
| commands that timed out | 426 of 430 (99%) | 0-125 of 430 |
| state reports in that window | 0 | 391-580 |
| messages since z2m started (37 h) | 974 | 44,000-47,000 |
| messages exchanged in a separate 10-minute window | 0 | 96-127 |
| last heard | 13.2 h ago (about 21:15 yesterday) | seconds ago |
| heard by anyone in a mesh scan | no | yes |

It is still registered: it has never left the network and its network address has never changed, so nothing needs re-pairing. A direct ZCL attribute read to it times out exactly like the commands. Kitchen-radiator still holds a route entry for its network address (43311) stuck in DISCOVERY_UNDERWAY: the mesh remembers it and cannot reach it.

Ruled out: the map and its names (right friendly name, right IEEE address, commands correctly addressed, simply unanswered); the controller, the bridge and RBR's handling (every other relay in every room is being driven normally, Kitchen is carried by Kitchen-radiator, and RBR is flagging "Kitchen-plinth not responding" as a partial failure, which is correct); any loss of registration; anything model- or firmware-specific, because the plinth is a HOBEIAN ZG-301Z on firmware 0122052017 - byte for byte the same as six other modules on this mesh (Kitchen-radiator, Demand, Bedroom-1, Bedroom-2, Lounge, Sunroom), all of which are fine.

What the two answers point at. Inside the heater's own casing is the worst RF position on the network, and the last neighbour readings z2m holds from the module are all weak: 62 to Kitchen-radiator, 51 to Hall-radiator, 31 to Bedroom-1-radiator, 0 to everything else, and no link to the coordinator at all. A mains module in a metal box at floor level behind a kick plate holds a link only while conditions favour it, and once it loses one it can sit there indefinitely rather than reattaching - a power cycle forces a fresh join, which is exactly the "repowering brings it back" behaviour. It also explains why the loose-wire theory fitted at the time: the same power cycle "fixed" it then too.

Two other candidates stay on the list. The module may simply have wedged: doc/setupRBR.md already records these mains relays wedging with only a re-power clearing it, and two others are doing it right now - Hall-radiator and Office-heater, the two TS011F plugs, failed 29% and 22% of commands in the same window while continuing to report state, the classic "looks healthy, ignores commands" form. The plinth is the harder form of the same fault: it answers nothing at all. Or its 230 V feed is interrupted - the FCU is what is being cycled, so a supply fault gives the identical symptom, and a terminal tightened once can work loose again, with a fan heater in the same casing vibrating.

The test that settles it, and the one thing that cannot be seen from here: next time it goes missing, meter its L and N before touching anything. 230 V present means the feed is fine and the module has hung (replace it); absent means the supply fault is back (suspect the FCU and terminals, not the module).

Second-best and free: a persistent monitor is now watching that device on the broker. Re-power it whenever convenient and it will capture how it returns - the availability flip, the first state report, the link quality it comes back with, and how long it then lasts. Returning at 150+ LQI and dying again means the module; returning marginal (40-70) means the position, and the fix is to get the module out of the metal casing or add a mains router in the plinth area.

Two things worth fixing regardless. zigbee-bridge.py publishes the relay command before it checks whether the device is responsive, so the controller keeps commanding the plinth every cycle: 430 commands in 40 minutes, about 15,600 a day, each holding the coordinator until it times out roughly five seconds later. Moving the responsiveness check ahead of the publish, or letting the controller skip a relay it already knows is down, would take that traffic off the mesh and make the failure counts mean something. And the mesh as a whole is thin: the coordinator's links to the mains relays are 117-192 with nothing above 200, and the routers' links to each other are far worse (0-97). Given step 5 of setupRBR.md (the dongle against metalwork, and the thousands of failed commands a day that followed), the coordinator's placement is worth another look; Bedroom-1-thermometer is at LQI 88 with a 34-minute reporting gap, close to the 45-minute staleness gate.

Offered to take a fresh mesh scan the moment the device returns, which would give its live neighbour table rather than the stale one and confirm or kill the placement story.

## 11:29

I've repowered it.

**Assistant**

Caught the return: z2m flipped it to online at 11:22:51, within seconds of the FCU going back on. Its first reports came in at link quality 140, 144, 176, settling at 156-164; every command has been answered since - 38 commands and 0 failures in the six minutes after (it was 426 of 430 timing out before), 78 state reports (it was zero), and its message counter went 974 to 1033. It resumed its existing registration: same network address 43311, same IEEE, no re-interview, no leave event, no address change. Nothing needs re-pairing.

The fresh mesh scan taken at 11:28 changes one of my earlier conclusions, so it should be said plainly. When the module is alive its radio link is fine: its own neighbour table has the coordinator at LQI 158, and the coordinator has it at 76. It is a direct child of the coordinator, not routed through anything. Its links to the other mains routers are weak (0-62), but that is the shape of this whole house - Kitchen-radiator itself hears the other routers at only 21-90. So the "it is just in a bad RF spot inside the casing" story does not survive the reading: the position is workable and every command lands in about fifty milliseconds. The one caveat is that the coordinator-side link of 76 is the weakest of all the mains relays (the others are 128-196), so the casing may be shaving margin without being fatal.

That leaves the failure as a hard stop of the module, not a gradual fade, and two candidates that this data cannot separate: the module hangs (its application stops dead, a re-power restarts it - the wedge already recorded in setupRBR.md, in its hardest form), or its 230 V is interrupted (a re-power also "restores" that, which is why the symptom looks identical). Both fit every measurement taken so far.

Natural experiment, and a negative result worth recording: the dead plinth was not the cause of the other relays' trouble. Before the re-power Hall-radiator was failing 125 of 430 commands (29%) and Office-heater 96 of 430 (22%); in the six minutes after, Hall-radiator logged 14 failures and Office-heater 8 - the same rate per minute. So the continuously timing-out plinth was not starving the coordinator, and those two plugs (both TS011F, a different model) are independently flaky: they are the documented wedge in its usual form, reporting state happily while ignoring roughly a quarter of their commands. That is a separate thread, and /health's setFailures is the diagnostic for it.

Ranked next steps. (1) At the next dropout, meter L and N before touching anything: 230 V present means the feed is fine and the module hung, absent means the supply fault is back. (2) Alternatively, at the next dropout do not re-power it at all - leave it an hour. If it never returns, it is a stop (module or supply); if it comes back by itself, it was never a stop, and the link or route is the story after all. (3) The most promising lead is the trigger: it went silent at about 21:15 on 20 September, an evening when the kitchen may well have been heating. The per-cycle heatlog will say whether it was - /data/rbr-heating/Kitchen/2026/09/20.csv - and if dropouts line up with the plinth heater running, the trigger is the load (heat or switching transients inside the casing) and the fix is to get the module out of the metalwork, or replace it. (4) The swap test stays the cheapest decisive test for the module itself.

The monitor is still running, so if it drops again the exact second of silence is captured and can be set against the same heatlog for that day. One product-level note while it is in mind: RBR's safety story assumes the relay obeys. When a module wedges closed, nothing in the system can open it - only the physical supply - which is worth a line in the concept documents about what "when it cannot sense a room" does and does not cover.

## 11:39

I've just repowered it again.

The device is in a plastic box at the back of the cupboard, above and slightly behind the plinth heater itself. I've been thinking of moving it to be alongside the heater, on the front of the plinth, where its external indicator neon (powered with the heater) will be visible without opening the cupboard door. It's a move of about 60cm towards the hub. Will that help?

**Assistant**

Corrected the siting note: a plastic box at the back of the cupboard, above and slightly behind the heater - not inside the heater's casing, so the metalwork framing from earlier is dropped. The user confirmed this second cycle was a test, not prompted by a fault, and the monitor agrees: reporting continuously from 11:22:51, every command confirmed, LQI steady at 156-164, messages 974 to 1204, no availability flip. The only blip in the record is a 13-second stretch at 11:30:45 when two plinth commands went unconfirmed and several other relays also timed out - a mesh-wide stall rather than a plinth event.

Reworked the link numbers against both scans, and the previous message's claim was wrong: the plinth is mid-pack on both directions, not worst. Coordinator hears it at 76 (fleet 49-106, and the plinth is better than Lounge 60, Hall 54, Office 51, Bedroom-2 49); it hears the coordinator at 158 (fleet 91-219). So on the evidence it is not in a weak spot - and it is comfortably better linked than Hall-radiator and Office-heater, the two devices that actually do lose about a quarter of their commands.

Answer on the move: 60 cm at 2.4 GHz is a fraction of a dB, and the link is already adequate, so the move will not measurably improve the RF and should not be expected to fix the fault. It is still worth doing for the non-RF reasons and as an experiment: out of the cupboard and away from the heater's chassis, airflow and wiring (heat and switching noise are the two plausible triggers for a hang, and warm air collects at the back of a cupboard above a heater), the visible indicator, and a before/after scan that settles the position question either way.

One addition to the plan while the wiring is open: put the indicator on the module's own supply rather than with the heater. A neon on the heater side says the relay is closed, which is the "is it heating" light wanted; a neon across the module's permanent L and N turns the one unanswered question into a glance - lit and silent means the module has hung, out means the supply fault is back (FCU, terminal, wiring). Both if both are wanted. Also keep it clear of the heater's warm-air discharge and fan, off the mains loom, and protected at the front of the plinth where a mop and a foot reach.

Noted why the test cycle left no trace, which is worth knowing generally: z2m's active availability check runs on a 10-minute interval with backoff and up to 30 seconds of jitter, so a dropout of seconds or a couple of minutes never becomes "offline" anywhere - not in the frontend, not in the app. The traces are the command failures, which RBR's bridge counts: curl to localhost:8889/health, or allspeak diagnose.as, gives the plinth's setFailures count and the age of the last one, dating the failure exactly.

Corrected the earlier "wedge" framing of the two plugs as well: Hall-radiator fails 2-4 commands in every single minute (29%) and Office-heater 22%, steadily all day, not in bursts that clear - so it is a per-command loss rate on the two worst-linked devices, not a wedge that a power cycle clears. One coherent finding underneath: the mesh's margins are generally thin (coordinator-side links 49-106 across the fleet), the two plugs sit at the thin end and lose commands, and the plinth - better linked than both - is instead the one device that stops completely. Its link is not what stops it.

Offered to re-scan after the move and to keep the monitor running, with the heatlog correlation for the moment it next goes silent.

## 11:55

I can check with a voltage sensor, but I think it's extremely unlikely to be an upstream power failure.

**Assistant**

Agreed with the judgement and gave the reasoning back in a stronger form. Trimmed the reliability argument to the four things that bear on the decision:

The voltage check only counts if it is made at the moment of failure, at the module's own terminals: a reading while it is running proves nothing, and anything measured elsewhere on the circuit - even the same spur - proves only that the circuit is live. So the permanent version (a neon or sensor across the module's L and N) is worth more than a retrospective meter reading.

The record says this has happened before: conversation-004.md (22 August) records the same device as "exists in z2m but not responding - never reported since bridge start", and it was still unresponsive when that session closed. That one was attributed to the loose wire, so it may have been the power fault rather than a hang; either way the plinth has been the problem device since the build.

Why not to tolerate the cycles: a hung module keeps its relay where it was, and the dangerous direction is the one the power-cycle routine hides. If it is commanding heat when it hangs, the heater runs and nothing in RBR can stop it - the staleness gate, the room status and the demand logic all assume the relay obeys. The asymmetry is the point: if it loses its mains the relay drops open (which is why the device has power_on_behavior: previous - it re-applies the last state when power returns), but if it hangs the contact stays closed. So the failure mode being tolerated is the one that can leave a 2-3 kW fan heater running under a kitchen unit with no control.

The user then chose the replacement: no spare ZG-301Z to hand, so a smart socket identical to the ones in the Hall and Office (TS011F plug, _TZ3210_fgwhjm9j).

Answered with the measurement upside and two cautions. Upside: those plugs publish power, energy, current and voltage, so the plinth heater's consumption becomes visible - it would say directly whether the heater was running at a future stop, and it covers one of the clamp sites in the current-measurement plan. Cautions: (1) the two plugs are currently the worst relays in the system - Hall-radiator fails 2-4 commands every minute (29%) and Office-heater 22%, steadily all day, against 0-7% for the seven ZG-301Z modules - though their links are also the two worst in the mesh (coordinator hears them at 54 and 51 against the plinth's 76), so model and position are not yet separable; the plinth is better linked, and the swap gives exactly that comparison. (2) Check the plug's rating against the heater's load, since it is a 13 A appliance connector replacing fixed wiring.

Setup notes given: pair it and rename it to Kitchen-plinth exactly, because the bridge addresses devices by friendly name and the map then needs no change; remove the old module's z2m entry afterwards, or it lingers, as Hall-thermometer-old and Outside-thermometer-old still do with retained availability topics; set power_outage_memory to off rather than restore (both plugs are on restore), since on a heater restore means a power cut can bring the heater back on by itself; and keep the supply indicator as planned, because the plug's own LED is on the wrong side of the relay to answer the power question.

Closed on the point that the swap is still the test: a socket behaving normally in the plinth position means the old module was the fault; misbehaviour there implicates the position or the load.

## 11:57

It's a hydronic heater, so no power issues.
The Hall and Office sockets are also the ones most distant from the hub.

**Assistant**

Took both points and retracted what they invalidate, rather than restating them more weakly.

The hydronic correction retires three things from the previous message. The safety argument goes: with a wet coil and a fan, the electrical load is a fan, and the water side is governed by the boiler's own controls, so a hung-closed relay costs comfort and a fan left running, not a fire risk - it is a control-integrity problem, not a fire one. The switch rating and inrush caution goes, since a fan is a trivial load for either device. The power_outage_memory note is downgraded: restoring a fan to on after a power cut is cosmetic, and the controller re-commands OFF within a cycle anyway, so off is tidier but not a safety matter. It also removes load and switching transients from the candidate triggers, which leaves the unit itself (its MCU/radio stack or its internal supply) or the local heat dose - the module sits in the cupboard above a hydronic coil where warm air collects.

The distance point retires the plug caution. Hall and Office are the two most distant from the hub, which is exactly what their two worst links say (coordinator hears them at 54 and 51, against the plinth's 76), so the 29% and 22% are a link-margin effect rather than a weak model. That turns the swap into a clean prediction: at the plinth's better-linked position the socket should land near the ZG-301Z's 0-7%, and if it does, the old module was the fault and the position is fine.

Also noted the August recurrence is only a counter-example to the heat theory if it was not the loose wire - which is what it was attributed to at the time, so it may be nothing of the kind.

Revised plan, short: fit the socket and rename it to Kitchen-plinth, remove the old module's z2m entry, move it to the front of the plinth away from the coil and the trapped warm air, keep the supply indicator, and let the swap be the test. One bonus from the plug: with a fan load its power reading is direct evidence that the fan actually ran when commanded, which is switching evidence RBR otherwise lacks - so a real ON while the monitor is running would let a stop be correlated against the heater actually running, which is the one trigger question still open. If the far-end sockets are worth fixing in their own right, a cheap mains router at that end (or the dongle-placement check in setupRBR step 5) is the lever, and that is separate from this fault.

Offered the after-swap measurement: the new device's command-failure rate against the 29%/22% baseline for the same model at the far end, plus its link quality in the new position.

## 12:53

Ive done the changeover. Can you check again?

**Assistant**

Checked the mesh and the command stream. The system side of the changeover is clean: Kitchen-plinth is now the TS011F socket (IEEE 0xa4c1382abf92c418, interviewed, online, network address 43266), the old ZG-301Z entry is gone from zigbee2mqtt with no stale or -old leftover, the friendly name still matches the map, and RBR is addressing it - 36 commands in the six minutes after the changeover, all OFF because the kitchen is not calling for heat.

Numbers, same position, six minutes (the user confirmed the socket went in the same spot, so this is a device-only change):

| at the same spot | ZG-301Z module (to 12:46) | TS011F socket (from 12:46) |
| coordinator's direct link to it (neighbour table) | 76 | 10 |
| its link to the coordinator | 158 | 96 |
| linkquality in its own state messages | 156-164 | 88-152, median 96 |
| commands unanswered | 0% while alive (99% while stopped) | 3 of 36, 8% |
| devices it can hear | Coordinator 158, Hall 51, Kitchen-radiator 62, Demand 44, Bedroom-1 39, Sunroom 31 | Coordinator 96, Demand 44, Bedroom-1 40, Sunroom 31, Bedroom-2 29, Lounge 0, Kitchen-radiator 0 |
| supply reading | none | 244 V steady |

Read: the socket answers most commands, and 8% is far better than the same model's 22-29% at the far end (Hall and Office), which bears out the distance explanation - same device, better position, a third of the losses. But it is not as clean as the module was when alive (0%), and the reason is visible in the link numbers: at that spot the socket's radio is materially weaker than the module's - the coordinator's direct link to it is 10 against 76, and it cannot hear Kitchen-radiator at all where the module heard it at 62. So in that plastic box the module had the better antenna and the socket is leaning on being routed through something else. That makes the move to the front of the plinth more worthwhile than the earlier estimate, and it is now a same-device before/after, which is a cleaner experiment than the device swap was.

Verdict on the original fault stays open, and it is days not minutes: the module ran 84 minutes today after 13 hours silent. If the socket now misses the occasional command but stays reachable, that is the signature of a link-limited but healthy device and the hard stop should be gone; if it drops off entirely, the difference is that a working stack re-establishes its route by itself, so no power cycle should be needed.

Socket extras noted: voltage steady at 244 V, so any future stop will have a supply reading immediately before it; power, current and energy all zero because every command is OFF and the fan is idle - when the kitchen first calls for heat we will see the fan's watts, which is both the switching evidence and the datum for correlating a future stop against the heater actually running. Also noted the network scan took about six minutes to answer, the coordinator having been slow with them today.

Offered to keep measuring and to re-report after the move.

## 13:52

It's a little odd that the plinth can't hear the radiator. The distance between them is about 5m. However, betwen them in a direct line is a line of kitchen cabinets, and a washing machine. Perhaps that's what is blocking the signal. What if I were to put a USB signal repeater where they both have a direct line of sight?

**Assistant**

Took the observation back to the scans and found that most of the missing link is the new device, not a new obstruction. At the same spot, the module heard Kitchen-radiator at 62 and Kitchen-radiator heard the module at 59 (post-repower scan, 11:28). With the socket, neither hears the other: the socket records 0 for Kitchen-radiator, and Kitchen-radiator's own neighbour table does not list the socket at all. And it is not just that pair - the socket reads about 60 points below the module from every direction: it hears the coordinator at 96 against 158, and the coordinator hears it at 10 against 76. Who does hear it: coordinator 10, Bedroom-1-radiator 15, Hall-radiator 33. So the cabinetry and washing machine are probably why that path was marginal in the first place, but the swap is what closed it - the socket brought a weaker radio into a marginal position.

On the repeater: yes, sensible, with four refinements. (1) It has to be a Zigbee router - a USB-powered Zigbee repeater or any mains router that joins zigbee2mqtt as type Router; a USB or WiFi extender does nothing for Zigbee. (2) Place it for clearance, not for line of sight: at 2.4 GHz the win is a path around the cabinet run through open room space (on the worktop, or at the open end of the run) rather than pointing through carcass and washing machine, and it wants a strong backhaul - at the edge of good coverage with a healthy link to the coordinator or to Kitchen-radiator - so it shortens the last hop into the cupboard instead of repeating a bad signal. A router sitting in the dead spot makes things worse. (3) Zigbee parent choice is sticky: after fitting it the socket has to be power-cycled before it will take the new parent, and the scan is what confirms the relationship changed. (4) Expect a margin gain and measure the miss rate rather than assume one: in this system the plugs' misses do not map cleanly onto link quality, Hall-radiator losing 29% with a better direct link than the plinth socket's 10.

Sequencing advice: do the free thing first. Move the socket to the front of the plinth, which takes it out of the enclosure, and measure; the move is likely worth more here than a repeater. Then add the router and measure again. Counting commands against misses and scanning at each step tells us what each change bought.

Also flagged where a repeater would pay best: the far end, not the kitchen corner. Hall and Office lose about a quarter of their commands all day against 8% here, so one good router on that side of the house is worth more than one beside the plinth, and it is the same measurement exercise.

Retired the earlier framing of the plinth's missing 66 points of link being about Kitchen-radiator specifically: it was going to be the device, and the scans now say so.

## 13:58

I'm looking at a Sonoff ZBMicro ZigBee USB adapter, to be placed midway between the two devices and diagonally offset by 2.5m. The adapter will also be roughly half way between the hub and the Hall unit (although still with walls between). Does adding 1 or more such devices generally improve coverage?

**Assistant**

Checked the ZBMicro against its documentation rather than assuming, then answered the general question and the placement.

General answer: yes, provided the devices are routers - mains or USB powered and always listening - because a router relays other devices' traffic and adds alternative paths, so the mesh can hop around an obstruction or a dead parent. Battery devices never route, and neither do "extenders" of the WiFi kind. The caveats: placement dominates count (the standard target is every device within range of at least two routers, not routers in every room), the gain flattens as you add them, and a router parked in the dead spot is worse than none because it advertises itself and then cannot serve what joins it. Putting one at the edge of good coverage, where it has a strong backhaul and shortens the last hop, is the shape that works.

The ZBMicro specifically: it is a genuine router - zigbee2mqtt's device page describes it as a Zigbee USB repeater plug and states outright that the device is a Zigbee router - built on an EFR32MG21, USB-A, needing only 5 V. Three practical points. Enable rf_turbo_mode, which is what the device is partly sold on. Update the firmware to at least 1.0.5: the early firmware was extremely chatty (ZDO match-descriptor requests about every 15 seconds) and was reported to upset some hubs; 1.0.5 cuts that by more than an order of magnitude and is available as an OTA through zigbee2mqtt. And zigbee2mqtt warns that it does not clear stale entries from its routing table, which can generate address broadcasts if a child is force-removed - the fix is a factory reset. Power it from its own 5 V charger rather than a port whose power might be switched, and do not put the coordinator's dongle behind it. Nothing in RBR needs to know it exists: it is not in map.json, so it stays infrastructure and no room gains a relay.

On the placement: the diagonal offset is the right instinct, since it gets the path off the cabinet-and-washing-machine line. But bias the final position towards the plinth rather than the true midpoint. The pair is asymmetric: the coordinator hears the socket at 10, while the socket hears the coordinator at 96 - the socket is the weak transmitter in that conversation, so a router has to be somewhere it can actually hear the socket. A couple of metres with a clear run out of the cabinets is worth more than a geometrically fair 3.5 m. Whether the same unit also helps the hub-to-Hall path is a bonus, and it is measurable: after fitting, the scan shows whether the new router hears Hall-radiator and whether Hall-radiator lists it.

Measurement plan offered: fit it, power-cycle the plinth socket so it can take the new parent (Zigbee parent choice is sticky), then scan and count missed commands for the plinth, Hall and Office before and after. And not to expect the 8% to disappear: if two are bought, the second buys more at the far end, where Hall and Office lose about a quarter of their commands against 8% here.

Sources cited: zigbee2mqtt's ZBMicro device page, the CNX Software review, and the Home Assistant and Hubitat community threads on the device.

## 14:06

Actually, I have some more spare smart sockets of the type I just used. It would be easy to plug one in now and see what difference it makes. I assume a repeater still needs to be paired, just not identified to RBR.

**Assistant**

Went back through the monitor log for the changeover window and found the event that had been missed: the module failed again while the changeover was being done, and this time it took two other relays with it.

Timeline, all from the monitor. 11:22:51, the re-power, module clean for 49 minutes. 12:16, its last report; from 12:17 every command to it times out - a second stop, about fifty minutes after the power cycle and with the kitchen calling for no heat. 12:18, Kitchen-radiator and Demand begin failing too, 100% of commands, in lockstep, and stay unreachable until about 12:43 - twenty-five minutes - recovering by themselves shortly before the changeover. 12:46, the socket takes over; no failures since. Rates now: plinth socket about 4% of commands unanswered over the last hour, Hall-radiator about 11%, Office-heater about 3%, everything else at or near zero.

So the failure is not confined to one room's relay. The scans had the parent chain as Coordinator, then Demand, then Kitchen-radiator, so those two sit downstream of a single path, and a router dying in the mesh breaks the coordinator's source routes to them until they are rediscovered - the ROUTE_ERROR_MANY_TO_ONE_ROUTE_FAILURE messages seen earlier in the day are the same phenomenon. That is very likely why this has been so hard to pin down: one dying module shows up as other relays failing, half an hour at a time, and RBR's diagnostics point at whatever was commanded during the outage.

A correction was owed here, and given: the earlier report that the module "has answered every command since 11:22:51" was true of the window checked at 11:46, and then read the 318 failures in the before/after tally as the earlier outage rather than a second one. The log says otherwise, and the finding is now recorded properly.

Verdict restated with the new evidence: two stops in ninety minutes - one after thirteen hours dead, one after forty-nine minutes alive - each silent, each permanent until a power cycle, each taking two other relays down for about twenty-five minutes. A dying unit, now out of the circuit, which is the right outcome.

Answered the two socket questions. Pairing: yes, it must be joined to zigbee2mqtt to act as a router; identification to RBR: no, and it must not be in map.json. Two specifics worth knowing. The relay state is irrelevant - a mains router keeps its radio and routes while powered, on or off, so it can sit switched off with no load and simply report zero power and energy. And it wants a name no room can bind to, e.g. Mesh-repeater-1, because it will appear in the z2m device list and in the UI's device picker, and if it were ever bound to a room it would work as that room's relay; label it physically as well, since map.json will not record it. The one constraint is that a socket needs a 13 A outlet where it is wanted, which is the flexibility the ZBMicro's USB form factor buys.

Measurement notes for the trial: power-cycle the plinth socket after adding the router, because parent choice is sticky; compare rates over hours rather than minutes, since today contains twenty-five-minute stretches where every command to three relays failed, so a ten-minute before/after would lie - baseline being used is 12:50 to 14:04, with the socket at about 4%, Hall about 11%, Office about 3% and the rest near zero; and I will re-measure the same way plus a scan of the parent relationships afterwards. One mesh-stability angle recorded: the plinth socket's direct link to the coordinator is LQI 10, the weakest router on the network, and today showed what a router dropping out costs - which makes improving that link (the move, then possibly a turbo-mode router) a matter of protecting the mesh rather than one device.

## 14:16

Kitchen-repeater is in place; not ideally positioned but on a power socket that's out of the previous line of sight. Plinth is re-powered.

**Assistant**

Confirmed the repeater on the mesh and that RBR ignores it correctly. Kitchen-repeater is paired as type Router (TS011F, IEEE 0xa4c138f77f52b51e, network address 60146), online from 14:09:30. In a 100-second command sample, 18 commands went to Kitchen-plinth and none to Kitchen-repeater, so nothing in map.json needs touching and no room can be driven by it by accident.

Baseline to beat, from the hour before the repeater existed: plinth socket 4% of commands unanswered, Hall-radiator 11%, Office-heater 3%, everything else at or near zero. The ten minutes that include the pairing look like the best of the afternoon (plinth 3, Hall 8, Office 1 failures) but most of that window precedes the repeater coming up, so it proves nothing yet.

The measurement that answers the question is the scan, because it shows whether anything has chosen the repeater: whether the plinth socket is now a child of it, and whether it appears in the parent chain (Coordinator, then Demand, then Kitchen-radiator). That scan is pending - the coordinator has taken two to eight minutes to answer them today - and will be reported when it lands.

Expectation set: the socket's own reported link quality has ticked up marginally (median 104 against 92-104 before), which is within noise at this stage. Parent choice is sticky, so re-powering the plinth was the right move - a fresh rejoin is the moment a device picks a new parent. If the scan still shows it parenting to the coordinator at LQI around 10, the repeater is in the wrong place to help that pair, as suspected, and the front-of-plinth move remains the lever; if it shows the socket behind the repeater, the miss rate should fall over the next few hours.

Two housekeeping notes given for transparency. The original monitor's MQTT connection died at 14:13:52 after about three hours and has been restarted with a reconnect handler and a one-minute heartbeat, so there is a trivial gap in the record. And its health summary line had been reading the removed module's IEEE address, so the "plinth messages" figure it printed froze at the changeover - the socket's own counts come from the per-device captures instead. Also noted that Hall-radiator remains the constant: 8 to 16 failures every ten minutes all afternoon, untouched by the re-power, the socket swap or the repeater, which makes it the device with the most to gain and the one to watch for the trial's answer.

## 14:19

How do you tell what a device is using as its parent?

**Assistant**

Explained the method, using the freshly landed post-repeater scan as the worked example.

Method: request the network map (zigbee2mqtt/bridge/request/networkmap with {"type":"raw","routes":true}), which replies on bridge/response/networkmap - that is why a scan takes minutes, since each device's neighbour and routing tables are read separately. Then read the relationship field on each link. In this output 0 means the source is the parent of the target (the parent's own neighbour-table entry), 1 means the source is a child of the target (the device's own table naming its parent), and 2 is a sibling - heard, no parent/child relation. So a device's parent is the target of the rel=0 link that names it as a child, or, for a sleepy device, the target of its own rel=1 entry. Both sides agree where both exist, which is the check that the convention is right.

Two caveats that matter in practice. Routers record every neighbour as a sibling, including their own parent, so for a router the reliable side is who claims it as a child - the parent's table. And the map is a snapshot taken device by device over minutes, so it is a photograph, not a live view. Parent choice is also re-made on rejoin, which is exactly why re-powering a device is the way to make it reconsider.

Separately, routes (the Mgmt RTG lists in the same payload) give destination, next hop and status - ACTIVE or DISCOVERY_UNDERWAY - which is how paths, as opposed to parents, are read. That is what showed the old plinth module's route stuck in DISCOVERY_UNDERWAY this morning. The z2m frontend's Map tab is the same data drawn for humans.

Then the findings from the 14:16:48 scan. Parent edges: Coordinator is parent of Demand (129), Sunroom-radiator (97), Office-heater (45) and Kitchen-repeater (51); Sunroom-radiator is parent of Lounge-radiators (57), Hall-radiator (54) and Bedroom-2-radiator (56); Demand is parent of Kitchen-radiator (157); Kitchen-radiator is parent of Bedroom-1-radiator (88); and Bedroom-1-radiator is parent of Kitchen-plinth (24). End devices claim: the four thermometers to the Coordinator, Hall-thermometer to Sunroom-radiator, Outside-thermometer to Office-heater, Kitchen-thermometer and Bedroom-2-thermometer to Bedroom-1-radiator.

What it says about the trial, which is the useful part. The repeater has healthy links of its own (it hears the coordinator at 154, Bedroom-1-radiator 97, Demand 68, Kitchen-radiator 57) but nothing has chosen it: the only claim on it is the coordinator's, so it is a child of the coordinator and not yet a parent of anything. The plinth socket did re-parent when it was re-powered, but to Bedroom-1-radiator rather than to the repeater: the socket hears the repeater at 33 and Bedroom-1-radiator at 42, and Zigbee takes the better candidate. So the repeater is not close enough to the socket to win, which matches the "not ideally positioned" assessment. Consequence for measurement: the socket's numbers from now on test a different arrangement (a slightly better link but a longer path, plinth to Bedroom-1 to Kitchen-radiator to Demand to coordinator), not the repeater's effect, so the two things to watch are whether the miss rate improves on the new parent and whether anything ever claims the repeater as a child - that is how it earns its place.

Offered to print this parent table on demand, and noted that a "who parents to whom" section in diagnose.as would be a genuinely useful addition, given how much of this hunt it would have shortened.

## 14:30

I could really use a commnd-line tool that displays the current mesh information as above.

**Assistant**

Wrote `zigbee-mesh.py` at the repo root, verified it against the live broker, and wired it into the shipped controller file set (the user chose shipping over repo-only).

What it does: asks zigbee2mqtt for a raw network map and renders the mesh as a parent tree plus a per-device table (parent, link quality on that edge, best and worst links, number of neighbours, last-seen, model), then a weak-link list, then - with --failures - a live count of relay commands that went unanswered. Read-only: it publishes one request and subscribes, sends no device commands. Flags: --failures [SECS], --json, --from FILE (render a saved scan), --broker/--port/--username/--password/--tls, --timeout, --config. It reads zigbee-config.json like zigbee-bridge.py and falls back to localhost:1883.

Two bugs found and fixed during the work: the rel=0 parent edge was inverted (the map writes it from the parent's side, so the child is the link's target), and the failure-report tuple was malformed. Also refactored the two MQTT client constructions into one helper after noticing the failure watch would have ignored a TLS setting from the config.

Verification: live run against 192.168.1.20 (map plus a 60-second failure watch) and an offline render of a saved scan; --json output parsed and checked; python3 -m py_compile and bash -n deploy.sh clean. No unit test added: the hyphenated module name does not fit the repo's <module>_test.py convention, and neither zigbee-bridge.py nor zigbee-pair.py has one - --from covers reproducibility instead, since a saved scan renders identically.

Shipping plumbing: added to deploy.sh twice (CONTROLLER_FILES and the zip file list) and to rbr-updater.py's TARBALL_FILES, plus doc/CONTROLLER-FILES.md, a line in doc/setupRBR.md step 11, and doc/UPDATE-MECHANISM.md's tarball listing.

Three findings surfaced rather than silently fixed. doc/UPDATE-MECHANISM.md claimed the tarball contains "exactly these files" but its list was missing diagnose.as and heatlog.py; corrected to match deploy.sh. rbr-updater.py's TARBALL_FILES omits rbr-watchdog.sh and rbr-mapbackup.py even though deploy.sh ships both, so they are shipped but not required - left alone, flagged as possibly deliberate. And zigbee-config.json is tracked in git and contains the broker password (confirmed with git ls-files) - worth rotating or ignoring if the repository is public.

What the live run showed: the plinth socket's parent is Bedroom-1-radiator at lqi 24 (weak), Kitchen-repeater is a child of the coordinator at lqi 51, seven weak links in the mesh, and in a 20-second watch Hall-radiator missed 1 of 3 commands. Short samples swing a lot, which is what --failures 60 (or longer) is for.

## 14:38

Remind me how to force a password request when logging in over SSH

**Assistant**

Answered as a short reminder (off the RBR thread, but tied back to getting the new tool onto the controller).

Client side, the one that matters is turning key authentication off, or the client satisfies the login from your key or agent and never prompts:

    ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password user@host

Four refinements. If the server offers the password through PAM keyboard-interactive rather than plain password auth (common on Debian and Ubuntu), use -o PreferredAuthentications=keyboard-interactive,password, or add -o KbdInteractiveAuthentication=yes. If your ~/.ssh/config or a wrapper script sets BatchMode yes, prompts are suppressed entirely - override with -o BatchMode=no. With an agent running, -o IdentityAgent=none (or IdentitiesOnly=yes with a chosen -i) stops it offering keys. NumberOfPasswordPrompts defaults to three; raise it only if you keep failing.

Server side, if the prompt never appears at all, /etc/ssh/sshd_config needs PasswordAuthentication yes and, on modern OpenSSH, KbdInteractiveAuthentication yes - password logins usually travel through PAM, so the second is the one people forget. Check what the daemon actually thinks with sshd -T | grep -i passwordauth, remembering that Ubuntu images often override the file from a drop-in under /etc/ssh/sshd_config.d/. Then sudo systemctl reload ssh.

Noted that the controller is already advertising password auth, since an earlier automated attempt was refused with "Permission denied (publickey,password)" - so only the client side needs telling. Closed with the one-line scp form for copying zigbee-mesh.py to the controller.

## 14:52

Thank you. That will be most useful. I can move things around and check the effect.

**Assistant**

Closed with a short recipe for measuring the move. Before touching anything: run the tool with --failures 120 into mesh-before.txt and write down four numbers - the plinth socket's parent and its link quality (Bedroom-1-radiator at 24), the plinth-to-repeater link, the weak-link count (7), and Hall-radiator's miss rate. After the move, power-cycle the socket, since a rejoin is the only thing that makes a device reconsider its parent, then wait five to ten minutes and run the same command again.

What would count as the move working: the parent edge changing to Kitchen-repeater, the plinth's link quality climbing out of the twenties, the weak-link count falling, and the miss rate dropping below the 4-6% it has been running at. Hours rather than minutes for the miss rate, because parents and routes settle slowly and short samples swing hard (Hall read 33% and 0% in successive short windows).

Three things left on the list rather than lost: nothing has claimed Kitchen-repeater yet, so if the move produces no child on it the position is the answer and the next lever is moving the repeater nearer or accepting it as a general mesh node on the strength of its own good links (coordinator 152, Bedroom-1-radiator 97); the plinth socket's path is now four hops (plinth, Bedroom-1, Kitchen-radiator, Demand, coordinator), which is a slightly better link bought with a longer path; and the two tooling loose ends, whether TARBALL_FILES ought to require rbr-watchdog.sh and rbr-mapbackup.py, and the broker password tracked in zigbee-config.json.

## 15:04

I've moved the repeater but not changed anything else yet. There are a couple more locations to try.

**Assistant**

Ran the tool itself against the broker after the move (14:58 scan, plus a detail scan a few minutes later) and compared with the 14:16 baseline.

The move did what it was meant to do for the pair in question: the Kitchen-plinth to Kitchen-repeater link went from 33/33 to 51/51 in both directions. The cost is in the repeater's other links - Bedroom-1-radiator 97/75 down to 42/24, Sunroom-radiator 59/39 down to 0/0, Demand 68/51 to 60/39, Kitchen-radiator 57/42 to 53/27 - while its link to the coordinator is unchanged at 150/51. So it is now a plinth-and-hall router rather than a bedroom-1 one, which is the right trade for serving the plinth, though its Bedroom-1 backhaul is now poor.

The plinth socket has not changed parent, as expected: moving the repeater cannot make the socket rejoin. It is still a child of Bedroom-1-radiator with an edge of 18, and its own table now has Bedroom-1 at 42 against the repeater at 51 and the coordinator at 86 - so the repeater is now its strongest router link, stronger than the parent it chose before the move. A re-power is therefore a fair test of whether it takes it, though parent choice belongs to the device and its coordinator link is stronger still.

Command misses over a 120-second watch: plinth socket 0 of 21, Hall-radiator 3 of 21 (14%), Office-heater 1 of 21 (5%). The 0% is the best the socket has shown, on a thin sample.

Two tool improvements came out of doing this comparison by hand. Added --device NAME, which prints one device's links in both directions, since a neighbour table only records what its owner hears and a placement decision needs both sides. And fixed the weak-link list, which had been reporting whichever direction it happened to iterate first: it now reports the weaker direction with the reverse value in brackets, because the asymmetry is the point - the pair that read "7 Coordinator <-> Kitchen-plinth" was the coordinator failing to hear the socket, while the socket heard the coordinator at 86. lqi 0 entries, which mean recorded-but-not-heard, are now counted separately rather than flooding the list. doc/setupRBR.md step 11 mentions --device.

Next step given: re-power the socket and re-run the tool with --device for both devices, looking for the parent edge to become Kitchen-repeater; and for the remaining candidate locations, compare the plinth-to-repeater pair against the repeater's own backhaul to the coordinator, which is currently a healthy 150/51 and should be kept above roughly 100.

## 15:12

How do I get a thermometer to re-parent?

**Assistant**

Answered with the rule first, then the two ways to force it, then the data from a fresh scan.

The rule: a sleepy end device picks its parent at join and only at join. Nothing in zigbee2mqtt or Zigbee can tell it to move, and while its current parent keeps answering it has no reason to look for another - so the only way to change the parent is to force a fresh join.

Two ways. Remove and re-pair, which is the controlled one: python3 zigbee-pair.py --remove Kitchen-thermometer, then python3 zigbee-pair.py for interactive pairing and put the sensor into pairing mode, then rename it back to exactly Kitchen-thermometer with python3 zigbee-pair.py --rename <new-name> Kitchen-thermometer (-/-rename takes the IEEE address too). RBR needs no change, because it binds by friendly name, and while the sensor is out the room reads stale and the controller holds that relay off, which is the safe direction. Or take the current parent away for long enough that the device notices and does an orphan rejoin - but for a sleepy sensor noticing can take up to an hour, the outcome is not guaranteed because it may re-attach to the same parent when it comes back, and if the parent is a room relay that room loses its relay meanwhile. Fine for a repeater, poor for a relay in service.

A scan was taken with --device for four thermometers. Kitchen-thermometer is on Bedroom-1-radiator at lqi 34, Outside-thermometer on Office-heater at 36 (both weak, and both showing 50-56 minutes since their last report, i.e. sitting at the controller's 45-minute staleness gate), Bedroom-2-thermometer on Bedroom-1-radiator at 80 and Hall-thermometer on Sunroom-radiator at 59, both usable. The three thermometers on the coordinator (Lounge 190, Office 151, Sunroom 233) have nothing to fix.

A caveat that shapes the method: these ZTH05 sensors list only their parent in their own neighbour table, and nothing else in the mesh records hearing them, so the map cannot show what they would choose instead. The rejoin is the experiment. What can be done first is to put a strong candidate in range - which is what the new Kitchen-repeater does for the kitchen sensor - and then re-pair so it is chosen. Afterwards, zigbee-mesh.py --device Kitchen-thermometer confirms the parent edge, remembering that the parent's own table is the authoritative side.

## 15:17

How about if I just take it way out of range?

**Assistant**

Yes, that works, because the trigger that matters is the device failing to reach its parent - but with three caveats worth knowing before doing it.

It is slow. A sleepy sensor only discovers the loss when it next tries to transmit, and these ZTH05s report on a roughly sixty-minute heartbeat, which is what the 44-56 minute seen ages in the scan are. So budget up to an hour, not minutes. It can be shortened: a temperature change makes the sensor report straight away, so waving it over a radiator (or by an open window) provokes the transmission whose failure is what starts the parent search. Bringing a sensor back after a battery change is the same situation the network already handles, so an hour or two away is structurally harmless.

It does not guarantee a different parent. On rejoin the device takes the best parent it can hear by its own rules, and if the old one is still the strongest option it will happily re-attach to it. To bias the outcome, do the excursion where the intended parent is the strongest thing in range - or better, bring the sensor back beside the candidate router first and let it rejoin there.

The room is held off while it is away: a stale reading makes the controller force that room's relay off and the UI shows the warning. Fine for an hour in the kitchen, but it is a consequence rather than a free experiment.

Two cheaper equivalents offered. There is no need to go far - the far end of the house, or a sealed metal tin over the sensor, breaks the parent link just as effectively, because all that is needed is a failed transmission. And where the parent is a plug, unplug the parent instead: Office-heater is the parent of Outside-thermometer and can simply be taken out for the duration, leaving the sensor untouched to re-parent on its own next attempt. Either way, keep the re-pair recipe ready as the fallback in case it has not reattached within an hour or two, and verify afterwards with zigbee-mesh.py --device, expecting the old parent's table to keep a stale child entry for a while - which is what the quiet-pairs line counts.

## 15:28

Let's move on to the next document.

**Assistant**

Wrote `docs/preparation/01-prerequisites.md`, the first document of the preparation layer. Sections: "Before anything is ordered" (the four conditions — a heating system that can be told heat is wanted, power where things are fitted, a router with a spare port and a cable route, and a spot for the controller that is clear of metalwork); "What has to be decided before the unit is prepared" (the room names and count, rooms with more than one emitter, rooms that are not heated, where the controller lives, who operates it); "What is not needed"; "The survey list" (a check-and-why table); and where next.

Grounded it in the repository rather than inventing: the demand relay and the boiler's demand input from `doc/setupRBR.md`, mains relays from the same document's warning that mains relays can wedge, the cable connection and the unused Wi-Fi credentials from `02-what-rbr-is.md`, and the dongle-siting lesson quoted from the install guide (moving the dongle off a steel bracket doubled link quality and took failed relay commands from thousands a day to virtually none).

Flagged to the user that this document is largely new: the repository has no prerequisites list, so the site conditions are inferred from what the installation actually implies, and the electrical provisions in particular want their eye. The bill of materials is where the exact provision per device belongs.

Corrected a convention of my own: the "plain words above the technical layer" rule in `docs/README.md` had banned implementation names from the preparation and installation layers, which is unworkable — those documents are for the people doing the work and must name the tools they ask the reader to use. The rule is now scoped to the concept layer, with the rule for the lower layers being that a tool is explained in a clause when it first appears. Added prerequisites to the industry reading path, since a specifier needs it before the concept layer's cost document, and removed the now-redundant `.gitkeep` from `docs/preparation/`.

Asked how the next document, `02-bill-of-materials.md`, should handle parts, since the repo names device classes but no models or suppliers. The user chose to write it by class, with the buying criteria that matter, and no SKUs.

## 15:40

One point: some households are averse to trailing cables and would prefer to buy ZigBee TRVs that do both control and temperature sensing. We haven't yet integrated one but I don't foresee any particular problems. So the requirement for mains power at each location may not be universal.

**Assistant**

Asked how far the variation should propagate, and the user answered "wherever is necessary to acknowledge that different kinds of hardware can be accommodated" — which is a broader and better framing than the device detail alone, so it was applied as that: RBR supplies the layer above the parts, and is therefore not tied to one arrangement of them.

Changes. `preparation/01-prerequisites.md`: the "Power where it is needed" paragraph now makes the requirement depend on the hardware chosen per room — the split arrangement needs a supply at the radiator, a valve that senses and switches by itself needs no cabling — and the survey rows were adjusted to match (mains at each point a relay is fitted; a room served by a self-contained valve needs no supply; the radiator row became "the valve there is driven by the system" rather than assuming a powered valve). `concept/02-what-rbr-is.md`: "The room devices" now describes two devices or one, and the "Anything can be replaced" bullet became "The hardware is not fixed", carrying the flexibility as a property rather than an accident. `concept/03-a-fitted-house.md`: the equipment list now allows the sensor to be built into the radiator's valve and the valve to be self-contained with no wiring. `appendix/glossary.md`: Thermometer, Relay and Radiator valve actuator each acknowledge both arrangements, and the Commissioning entry no longer says "thermometer and relays". `concept/00-the-experience-is-the-product.md`: one paragraph added to "A common platform, and the competition it invites" making the point the user's answer implies — because the system supplies the layer above the parts, it accommodates different hardware, including whatever replaces today's.

One judgement call flagged to the user: `01-prerequisites.md` says plainly that the self-contained route "has not yet been fitted in a live installation". The user's chosen wording did not ask for a marker, so this is offered as removable — but it is the same honesty the documents apply to the pre-pairing route, and it is the one place a reader might specify hardware on the strength of it.

## 15:43

I'm expecting my colleague to buy at least one battery-powered TRV when he updates from the previous RBR-Now system. If we encounter any problems we can update the documentation at the same time as fixing the problems.

**Assistant**

Treated it as a note about sequencing rather than a request for edits, and did the one thing that makes the future update cheap: recorded the exact touchpoints, so that when the trial happens the documentation pass is mechanical rather than a search.

Confirmed the marker in `preparation/01-prerequisites.md` stays as written ("That second route has not yet been fitted in a live installation"), noting that it is phrased to be struck the moment the trial succeeds rather than left to age into a false statement. Listed the five reader-facing places that name the self-contained route: the 'A common platform' paragraph in `00`, 'The room devices' and 'The hardware is not fixed' in `02`, the valve bullet under 'Where the equipment goes' in `03`, the three device entries in the glossary, and 'Power where it is needed' plus the mains survey row in `01-prerequisites`.

Raised the two knock-on items the trial will settle, which belong to documents not yet written. Naming: the convention in `doc/setupRBR.md` is `<room>-<device>` with names like `Kitchen-radiator` and `Kitchen-thermometer`, and a self-contained valve is neither, so it needs its own rule in `preparation/03-naming-and-network.md`. Commissioning: step 10 sets 'Relay type' and switches on 'Sensor controls relay', neither of which applies to a valve that senses and closes by itself, so the installation layer needs two routes through commissioning. Noted also that `02-bill-of-materials.md`, next up, should carry the buying criteria for both arrangements. Saved the touchpoints as a project fact.

## 15:52

Good. On with the next document.

**Assistant**

Wrote `docs/preparation/02-bill-of-materials.md` by class with the buying criteria, as chosen, and with the two routes as its spine. Sections: what this list is; the controller; the coordinator; room temperature sensors; relays; radiator actuators; the valve body underneath; what is not bought; the two routes, priced differently; where next.

Choices made. Each part is described by what it must do and what to check when buying, with no models named, for three reasons given in the opening: it stays true as suppliers change, an installer can buy locally, and a household can replace one part years later. The document opens by quoting the product's own interface text — "works with off-the-shelf relays, TRVs and thermometers; build the system exactly as you want it" — which is the hardware-flexibility argument in the product's own words. Each part carries the failure mode an installer will actually meet, not just a specification: the coordinator's extension lead and the metalwork lesson, and mains relays wedging and needing a re-power, both as callouts reused from the install guide.

The two routes are priced against each other in a closing table (the self-contained route removes the relays, the room sensors and all the cabling at the radiators, and puts the money into the heads instead), with the note that which is cheaper depends on what a cable to each radiator would cost to run.

Verified one external specification rather than guessing, because an installer would order against it: M30 x 1.5 mm is the connection almost every smart head uses, with an 11.5 mm pin under EN 215, and most modern UK and European valve bodies take such a head directly, with adapters for the legacy exceptions — the Danfoss family especially, where the RA and the two RAV/RAVL sizes differ, plus Caleffi, Giacomini, M28 fittings, Oventrop and Vaillant. The document says to measure rather than assume, and notes that a smart head is larger than the manual one it replaces, so window-sill clearance matters.

Added one honest trade-off and flagged it to the user: a self-contained head measures the temperature at the radiator, where the reading commonly runs a degree or two high, so a room may settle slightly cooler than the target unless an offset or a separate sensor is used. That is from TRV vendor guidance rather than from RBR's own experience, it is a real reason the split arrangement exists, and the user may want it foregrounded or softened.

Marked `02` as drafted in `docs/README.md` and moved the status line to "preparation is half drafted". Verified: every paragraph on a single line, headings intact, and all links resolve except the documents not yet written.

## 16:00

You're quite right to highlight the issue of sensor placement in a self-contained valve, so no need to soften it. Another issue is the need to change batteries, versus a model with recharegeable battery. I don't know if such a thing exists - the Shelly one I bought years ago is Wi-Fi.
The only other point I'd make is to avoid computers that run on SD cards. SSD is greatly to be preferred on grounds of reliability.

**Assistant**

Kept the sensor-placement point as written, on instruction. Added both new points to `docs/preparation/02-bill-of-materials.md`, and checked the battery question rather than guessing at it.

The battery finding is worth having, because it overturns the obvious assumption. Ordinary rechargeable cells are usually the wrong answer for these heads: makers specify 1.5 V alkaline and warn against rechargeable cells, which deliver around 1.2 V and fall below the device's operating window, so the valve misbehaves rather than simply running down. The rechargeable answer is a head with a built-in battery charged over USB, and that does exist — the best-known is Shelly's, at roughly two years per charge and about five hours to charge — but it is unusual, it is Wi-Fi rather than Zigbee in its original form, and the mainstream Zigbee heads are all cell-powered. So the document now says plainly that this route buys freedom from cabling at the price of a round of batteries once a year or so, with the specified chemistry taken seriously and a head that reports its battery level preferred. Reporting interval is named as the main lever on battery life, for both heads and sensors.

The self-contained route's caveats were expanded from two to three and given as bullets, since they are now of equal weight: measuring at the radiator, fitting the valve body, and servicing the batteries.

Added the storage criterion to the controller as the one reliability choice worth being firm about: not a microSD card. The reasoning given is that the controller writes continuously — the plan, the heating records, the incoming readings — and cards wear out under that, with a failure taking the whole system down and able to leave the plan unreadable mid-write. That connects to the map keeper that already exists for exactly that failure mode. An SSD or built-in storage is preferred; where a card is unavoidable it should be high-endurance and the plan backed up regardless.

Flagged one departure from the no-names habit: Shelly is named in the battery paragraph. It is the user's own reference and it answers the question they asked (whether a rechargeable head exists), rather than being a critical reference to a competitor, so it seemed the right call — but it is flagged as removable.

## 16:12

I'll bookmark the RAM disk issue and deal with it optimally in a separate session.

**Assistant**

Treated it as a deferral and cleared the ground so the separate session starts from the recorded position rather than re-deriving it. Updated the storage fact to record the deferral explicitly, so a future session does not mistake the recommendation for something already settled.

Noted the one consequence for the documents: the bill of materials' storage bullet now promises that `04-controller-computer.md` "covers how", so if the separate session lands on a different recommendation, that is the single sentence in the tree to revisit — the pointer makes the provisional part cheap to correct rather than a hunt.

Confirmed that nothing else in the tree depends on the storage question. `03-naming-and-network.md`, the next document, is entirely independent of it. And when we reach `04-controller-computer.md`, it will be written with the storage section left as the one open item rather than pre-empting the separate session. Offered to carry on with `03`.

## 16:15

go

**Assistant**

Wrote `docs/preparation/03-naming-and-network.md`. Sections: why the names matter; the convention; the demand relay; renaming; a device that is neither a relay nor a thermometer; the network; where next, with a naming table (`<room>-thermometer`, `<room>-radiator`, `<room>-plinth`, `<room>-trv`, and the demand relay).

The spine is that a device's name is not a label but the only link between the hardware and the plan, and that a mismatch is therefore silent — a relay that never switches or a thermometer that reads unknown, indistinguishable from a fault, with nothing reporting a naming error. Case is called out explicitly. Renaming is split into the two cases that behave differently: renaming a room is cosmetic and leaves the devices alone, while renaming a device breaks every room that refers to it and is really a re-pairing exercise. The self-contained valve gets its convention (`<room>-trv`, one name for one device doing two jobs), with an honest note that how such a device is bound to its room in commissioning is not settled because none has been fitted yet.

The network half is grounded in what `rbr-setup.sh` actually writes rather than in generalities: one connection to the router and it is a cable; the rooms on their own radio, so no household Wi-Fi credentials are needed and a device-heavy house does not add clients to the router; per-installation generated network key and identifier (`network_key: GENERATE`, `pan_id: GENERATE`), so neighbouring installations are not on the same network; channel 15 chosen deliberately to sit in the gaps between the Wi-Fi channels a household router normally uses, with the note that it is the setting to change only after the coordinator's position has been dealt with, since that is the commoner cause; and mains-powered relays acting as mesh routers, which is why a house with a relay in most rooms generally needs no repeaters.

Discovery folded back into the bill of materials: the setup writes the Ember driver, so a coordinator of that family is the path of least resistance and anything else means changing one line and checking support. That is a concrete buying criterion the document did not previously carry.

Flagged one inconsistency found while checking: the install guide says the boiler relay is "conventionally `Demand`", while the repository's own `map.json` has `request = "Request-relay"` — legacy RBR-Now naming. Checked whether it is a trap for new installers and it is not, because the shipped controller pack contains no map file at all, so nothing ships a name to copy. The document states the rule (whatever the plan's `request` field says is what the device must be called, and a copied plan wins) and gives `Demand` as the guide's convention, so it is correct either way; the two are a house-style question for the user, not a defect in the tree.

Marked `03` as drafted and moved the status line to "preparation is nearly drafted".

## 16:33

No comments needed on that one, so do the next. It's quite likely I'll want implement volatile storage for volatile data. Refreshing the SSD hourly removes a lot of saves, and a power outage during that time is rarely serious. So let's just assume the system will be optimised as the best compromise between minimising wear and losing data.

**Assistant**

Took the storage principle as settled rather than parked, and wrote `docs/preparation/04-controller-computer.md` with it stated. Sections: the machine; getting the software onto it; the radio: plug it in first; storage: what must survive, and what need not; if the controller has a display; coming back after a power cut; where next.

The storage section sorts the writing into the two kinds the guidance implies. What must survive a power cut is small and changes rarely — the plan, its history, and the rooms' heating records — and belongs on persistent storage, which is the reason for the SSD. What need not: the readings as they arrive, the running summary the terminal dashboard draws from, and the logs, all regenerated within minutes or of no lasting value. The compromise is stated as the user put it: keep the volatile data in volatile storage, refresh to persistent storage periodically with hourly as the working assumption, and accept that a power cut loses at most that window — which for readings and logs is unimportant. The plan is named as the exception and should stay as it is: written deliberately to persistent storage with its history beside it, never buffered, because it is the one artefact representing somebody's work and it changes rarely.

Two findings from rbr-setup.sh folded into the document and one into the bill of materials. First, the coordinator must be plugged in before the setup runs, because the script derives both the stable device name and the Zigbee software's port from what it finds. Second, that stable name is created only for the coordinator the script expects — a Silicon Labs CP210x device at USB 10c4:ea60 — so any other coordinator is pinned to whichever serial device it is given, which can change between reboots and presents as the heating mysteriously failing to start after a restart. That is now a buying criterion in the bill of materials and explained in full in 04. Flagged to the user that the udev rule is the line to generalise if other coordinators are to be supported. Also recorded that the setup prefers a dedicated partition at /data/rbr-heating for the heating records, falling back to a symlink into the controller user's home so that the configured path is identical on every machine and adding a real partition later is a move rather than a change.

Flagged that 04 is the first document in the tree to use a fenced code block, for the two bootstrap commands — so it is the one place to check if the Doclet converter handles fences differently from the rest of the tree.

Marked `04` as drafted and moved the status line to "preparation is complete bar its last document". Verified paragraphs, headings and links; the one wrap warning was a false positive from code inside the fence.

## 16:43

I'd rather not refer to IXHUB. It's a pretty terrible computer. It comes with Android so there's no BIOS, limiting the choice of Linux to what they offer, which is rarely up to date. Mini-PCs are now becoming very inexpensive, offering better reliability and value for money than Raspberry Pi and its equivalents.

**Assistant**

Treated it as a change of recommendation rather than a name to drop, and rewrote the parts of the tree that carried it.

`docs/preparation/04-controller-computer.md`: the "If the controller has a display" section is gone, replaced by a mini-PC recommendation at the top of "The machine" — that once a single-board computer has been given a case, a power supply and storage, the mini-PC usually costs less, and arrives with the two things the document itself depends on: an SSD rather than a card, and ordinary firmware with the power-loss setting. The no-BIOS point was then given real work rather than left as an aside: it now appears at the end of "Coming back after a power cut", explaining that a panel or appliance board booting a vendor operating system has no such setting and so cannot be relied on to return after an outage, quite apart from limiting which Linux you can run. The conclusion is left to the reader — a built-in screen is not worth that.

`docs/preparation/02-bill-of-materials.md`: the controller section now steers to a mini-PC and says why, and the display bullet says a screen is a convenience rather than a requirement, since the interface runs in any browser. The repository `README.md` no longer says the controller is designed for an Orange Pi Zero 2.

Asked what to do with the references outside the docs tree, and the user chose to mark the guide superseded and correct the AI notes. `doc/setupIXHUB.md` now carries a superseded note at the top giving the reasons in the user's own terms — Android means no ordinary BIOS, so the Linux choice is limited to what the maker offers and rarely kept current, and there is no firmware setting to restore after power loss; a mini-PC now costs less than a Raspberry Pi and its equivalents once cased and given storage. The guide's content is kept for machines already in service. `AI/ARCHITECTURE.md` and `AI/PROJECT_OVERVIEW.md` (two lines) no longer say the controller runs on an IXHUB. Checked whether anything links to the guide before editing: nothing does, so the superseded note is self-contained.

Remaining mentions of IXHUB are the guide itself and the two historical ESPHome research notes in doc/, which are a dated record and were left alone.

## 16:46

To confirm: the fenced code blocks render perfectly in Doclets.

**Assistant**

Closed the flag and recorded the confirmation in the Doclet fact, so a later session does not re-raise it or avoid fences. The convention already allowed them; nothing in the tree needed changing.

Then wrote `docs/preparation/05-preparing-a-unit.md`, the last preparation document. Sections: what this stage is for; what has to be settled first; pairing and naming the devices; building the plan; recording what the household will need; what is left for the site visit; a pre-delivery checklist; where next.

Choices made. The document opens by explaining why preparing before delivery works at all, since that is the question an installer will have: the devices join the controller's radio network, and that network's key and identity are generated for the installation and live with the controller, so a device paired at the bench stays paired when it is fitted in the room it was named for — moving a device does not disturb the network, only moving it to a different network would. Rather than marking the route as untested, the on-site fallback is presented as the answer for the cases that need it (a replacement, or a device arriving after the unit), which makes the document true either way. Two pairing habits are given because they are the ones that go wrong: one device at a time, since a device joining while another is being named is a device that will be mis-named, and naming on join rather than leaving it for later. The checklist carries the two entries that cost the most if missed — the demand relay's name matching the plan's `request` field, and a record of any device named off-convention, because that is the list somebody needs three years later when a part is replaced. Schedules are set now where the household has said, and a sensible pattern where it has not, on the grounds that a pattern is quicker to correct than to invent on a doorstep.

Flagged a structural consequence to settle before the installation layer is written: under the pre-pairing model, running the setup script — currently scoped to `installation/01-installing-the-controller.md` — is bench work, not site work. Either that document's software-install content belongs in preparation, or installation/01 becomes the on-site bring-into-service document. 05 deliberately does not duplicate it.

Marked `05` as drafted and recorded in `docs/README.md` that the concept and preparation layers are now complete. Verified: paragraphs, links, and the tree state — 13,870 words across twelve documents plus the landing page.
