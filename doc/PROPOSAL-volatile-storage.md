# Proposal: volatile storage on a RAM disk

**Status:** implemented 2026-10-16 — both halves. What was built, and the four things deliberately left open, are recorded in §10. **Author:** RBR project (Graham) **Date:** 2026-10-16 **Related:** [04-controller-computer.md](../docs/preparation/04-controller-computer.md) ("Storage: what must survive, and what need not"), [02-bill-of-materials.md](../docs/preparation/02-bill-of-materials.md), [CONTROLLER-FILES.md](CONTROLLER-FILES.md), `controller.allspeak`, `deviceControl.allspeak`, `zigbee-bridge.py`, `heatlog.py`, `rbr-mapbackup.py`, `rbr-setup.sh`

## Motivation

The controller writes constantly, and most of what it writes is not worth keeping. [04-controller-computer.md](../docs/preparation/04-controller-computer.md) already sorts the two kinds apart and states the intended compromise — keep the volatile data in volatile storage while the system runs, refresh it to persistent storage periodically, and accept that a power cut loses at most the window since the last refresh — but it describes no mechanism, and no mechanism exists. The RAM disk that an earlier generation of RBR did run on was lost in the rewrite.

This proposal recovers it. It records what the previous iteration actually did, what the current code does instead, and what reinstating it involves — including the one question the docs leave open: what happens to the *current status* if power is removed without warning. It also carries a second change that belongs in the same piece of work: retiring the last non-Zigbee device support, RBR-Now (§9), which edits the same `map.json` schema and so is a migration better done once.

## What the previous iteration did

The Orange Pi / Linaro generation kept the controller's entire live working directory on a 1 MB tmpfs mounted at `/mnt/data`, created at boot (`reboot.sh`, and the `@reboot` entry in `cronroot.txt`):

```sh
mount -t tmpfs -o size=1M tmpfs /mnt/data
mkdir /mnt/data/sensors; chmod a+w /mnt/data/sensors
```

The controller set `put /mnt/data/ into RamDisk` once at start and then wrote practically all runtime state there: `map.json`, `status.json`, `logs.json`, `advance.json`, `systemdata.json`, `mijia.json`, `config.json`, `mac`, `name`, `profile`, `version`, `lock`, `uptime`, `network-errors`, `channel`.

Exactly one thing was written through to the card, and only when it changed (`PostSensorData`):

```
if Changed save prettify Map to `../map.json`     ! card, on change only
save prettify Map to RamDisk cat `map.json`       ! RAM, every time
```

and the reverse at boot: RAM map absent → `load Map from ../map.json` → save back into `/mnt/data`. A daily `backup.sh` line gave the plan a second net on disk (`cat /mnt/data/map > /home/linaro/backup/map-$(date +%Y%m%d).txt`).

Two properties of that design matter more than the mechanics:

1. **There was no RAM-to-disk refresh at all.** Readings, status, logs and the Advance state lived only in RAM and simply vanished on any reboot. The old answer to "what does a power cut cost" was *cold start*: everything except the plan was regenerated. The plan was the only artefact deemed irreplaceable, and it was persisted on every change.
2. **Some of the volatility came from the image, not the app.** The old boot log shows `/tmp`, `/var/log`, `/run` and `/dev/shm` all on tmpfs (`4 tmpfs /var/log mode=0755,nosuid,nodev`). The logs were volatile because the distribution mounted them so, not because the controller asked.

The counter-example in the same code is worth recording: `advance.json` lived only in `/mnt/data`, so pressing Advance and then pulling the plug lost the decision. That is the trap any RAM-disk design must avoid — anything a person authored must never exist solely in volatile storage.

## What the current code does

No tmpfs appears anywhere in the current tree outside the documentation. Every writer targets the install directory; one targets `/tmp`.

| File | Written by | Cadence | Durability today |
|---|---|---|---|
| `/tmp/rbr-dashboard.json` | `controller.allspeak`, the dashboard block in `MainLoop` | every loop | volatile only if `/tmp` happens to be tmpfs |
| `map.json` (whole file, ~24 KB) | `controller.allspeak`, the once-a-minute block at the end of `HandleMessages` | every 60 s, unconditional | persistent |
| `thermometers.json` | same block | ~once a minute | persistent |
| `heatlog-state.json` | same block, when dirty | on change | persistent |
| `zigbee-temperatures.json` | `zigbee-bridge.py`, `_update_temperatures_file` | every temperature MQTT message, whole file, atomic replace | persistent |
| `map-history/`, `map-last-good.json` | `rbr-mapbackup.py` | every 2 min, distinct revisions only | persistent |
| `<root>/<room>/<YYYY>/<MM>/<DD>.csv` | `heatlog.py` | on change, one `O_APPEND` line | persistent |
| controller log lines | `controller.allspeak` `log` → systemd journal | continuous | on disk whenever `/var/log/journal` exists |

Two consequences stand out.

- **`map.json` became the single persistent carrier of live state.** A room entry now holds the plan (`periods`, `events`, `mode`, `target`, `advance`, `until`, `relayType`, `linked`, `protect`) *and* the readings and derived state (`temperature`, `humidity`, `battery`, `status`, `statusMessage`, `relayMessage`, `relaysFailed`, `relaysTotal`, `timestamp`, `sensorAge`, `relay`). Because `timestamp` is stamped from `now` on every pass, the 60-second save is effectively unconditional: about 1,440 whole-file rewrites a day onto the SSD, most of them carrying data the docs themselves call not worth keeping.
- **`zigbee-bridge.py` is the heaviest writer of all.** It rewrites `zigbee-temperatures.json` on every temperature message from every device. With a dozen thermometers that is the largest single consumer of write cycles in the system, for data that is pure ephemeral reading.

The one part of the old idea that did survive is worth noting as an improvement already in hand: `advance` now lives on `Room` and so is persisted in `map.json`, where the old code kept it in RAM only.

## 1. Classifying the data

Everything above sorts into three classes, and the class decides the storage.

| Class | Data | Storage |
|---|---|---|
| **Irreplaceable, must survive** | the plan (`map.json`) and its history (`map-history/`, `map-last-good.json`); the rooms' heating records (`heatlog` CSVs) | persistent — unchanged by this proposal |
| **Regenerable within minutes** | `zigbee-temperatures.json`, `thermometers.json`, `heatlog-state.json`, `/tmp/rbr-dashboard.json`, the journal | volatile (RAM) |
| **Must survive, but is derived** | the command state that decides what the relays do after a restart: `mode`, `target`, `until`, `advance`, boosts, `prevmode`, `protect` | persistent — see §6, this is the awkward class |

The first class is already safe and needs nothing. The second is the target of the move. The third is what §4 is about.

## 2. The RAM disk itself

A dedicated tmpfs, installed the same way as everything else — a unit or a `tmpfiles.d` drop-in written by `rbr-setup.sh`, not a `mount` line in a cron entry.

- **Where:** `/run/rbr` (or `/var/lib/rbr-volatile`). `/run` is already a tmpfs on the target distributions, so a dedicated mount adds nothing to boot and keeps RBR's volatile data in one nameable place.
- **Size:** a few MB is ample. `map.json` is 24 KB, `thermometers.json` 3.4 KB, `zigbee-temperatures.json` 2 KB, the dashboard JSON smaller. The old 1 MB was sized for a much larger map; 8 MB leaves headroom for the bridge's temp files without inviting a runaway writer to fill RAM.
- **Options:** `mode=0750,nosuid,nodev`, owned by the controller user (every writer runs as that user, so the old `chmod a+w` is unnecessary). Do **not** set `noexec` — it buys nothing here and forecloses moving the bridge's script there later.
- **Watch:** the RAM disk is wiped on *every* reboot, clean or not, so anything that must survive a reboot cannot live there without a refresh step (§5).

## 3. What must not move

`map.json`, `map-history/` and `map-last-good.json` (the plan and its history) and the heating-records root named by `heatlog-root`. These are the artefacts the docs already place on persistent storage, and they are the reason to choose an SSD over a card in the first place.

The journal is the one judgement call. The docs name "the logs" as volatile, and the controller's `log` output is a systemd journal, so making them volatile means configuring journald (`Storage=volatile`, sending it to `/run/log/journal`) or a drop-in that caps the on-disk journal — not changing the controller. The trade-off is real: a volatile journal vanishes in exactly the incident where the last few lines are most wanted. `controller.service` already runs unbuffered so the lines reach the journal promptly; if the journal is made volatile, that property becomes the only thing standing between a crash and no evidence at all. Recommended, but as its own decision.

## 4. What is actually at risk on a power cut

The question the docs leave open is what an abrupt power loss costs once the volatile data is in RAM. The answer is "almost nothing", but only because of a property that should be stated rather than assumed.

- **The irreplaceable data is never in RAM.** The plan and the heating records stay on the disk, written on change, with `rbr-mapbackup.py` validating every revision and repairing a truncated map. Nothing this proposal moves to RAM is unregenerable.
- **Cold start is already safe.** If the RAM disk is empty after a power cut, the controller treats each volatile file as absent — `if file X exists load ... else reset` throughout — and rebuilds. `Thermometers` empty means `Thermometers has entry Sensor` is false for every room, which sets that room's status to `fail` and forces its relay off until fresh readings arrive. The system fails *safe*, not *stale*: a reading left over from before the outage cannot be acted on as current, because `sensorAge` is recomputed as `now - thermometer.ts` on every pass.
- **`heatlog-state.json` is the mildest loss of all.** It is a change-detection baseline; losing it re-logs the current row at worst, and `heatlog.py` already skips a row identical to the file's last line, so a restart cannot duplicate it.
- **The one thing genuinely at risk is the command state**, and it is at risk only if it, too, is moved to RAM. After power returns the controller must resume controlling as it was: which rooms are calling for heat, their modes and targets, any `until` that had not expired, an engaged Advance. That state is derived from the plan and the clock, so it re-derives — but anything set recently survives only because it is written to `map.json` every minute today. **This is the constraint that shapes the whole design, and the reason the command state must not be numbered among the volatile data.**

## 5. Options for preserving continuity

Once the classification in §1 is accepted, the volatility of the second class costs only continuity — the UI's view, the graphs, the "no report for N min" counters — not correctness. The options, in increasing cost:

1. **Accept cold start.** What the previous iteration did. Nothing to build; the volatile set rebuilds within minutes and nothing important is at stake.
2. **Periodic refresh, restored on boot.** A small timer (5–15 min; the docs' "hourly is workable") copies the RAM disk into a persistent shadow directory, and a unit ordered before `controller.service` copies it back at boot when the RAM disk is empty. This is the compromise the docs already describe — "lose at most the window". It must distinguish "empty because we rebooted" from "empty because there is no data", which is trivial, and the controller's `if file X exists` pattern means a wrong guess costs only a reading that is minutes stale.
3. **Flush on clean shutdown.** A systemd `ExecStop` on `controller.service` (and the bridge) that copies the RAM disk out. Covers reboots and graceful power-offs; a hard cut still falls back to (2) or (1).
4. **Keep the command state on non-volatile storage at all times** (recommended). Only the genuinely worthless data — raw readings, the dashboard, the logs — is fully volatile; everything the system needs in order to resume is written through on change. A hard cut then loses at most a few minutes of readings, never a decision.

Options (2) and (4) compose; (4) is the one that answers the question in the Motivation, because it removes the only class of data whose loss would change what the heating does.

## 6. The obstacle: `map.json` conflates the plan with the readings

Option (4) cannot be implemented without splitting `map.json`, and that split is the real work in this proposal. Today the minute-tick write is unconditional in practice because the saved `Map` carries eleven derived fields — `temperature`, `humidity`, `battery`, `status`, `statusMessage`, `relayMessage`, `relaysFailed`, `relaysTotal`, `timestamp`, `sensorAge` and `relay` — beside the plan. A naive "save only when `MapHasChanged`" gate does not help: `timestamp` changes on every pass, so the flag would be set continuously anyway.

The split is by field, not by file:

- **Plan and command fields** — `periods`, `events`, `mode`, `target`, `until`, `advance`, `prevmode`, `protect`, `linked`, `relays`, `sensor`, `name`, and the profile/room structure — remain in `map.json` on disk, written on change. (`relayType` is in this list too, but §9 retires it rather than carrying it through the split.) `MapHasChanged` already tracks the flips that matter (freshness flips and relay-state flips set it), so the gate is nearly in place.
- **Reading and derived fields** — `temperature`, `humidity`, `battery`, `status`, `statusMessage`, `relayMessage`, `relaysFailed`, `relaysTotal`, `timestamp`, `sensorAge`, `relay` — become RAM-only, sourced from the RAM-disk copies of `thermometers.json` / `zigbee-temperatures.json` and the bridge, exactly as they are sourced today.

Done this way the disk sees a handful of `map.json` writes a day instead of 1,440, the readings never touch it at all, and nothing the system needs to resume is ever only in RAM. Simulation mode writes `map-sim.json` instead of `map.json` and must be kept coherent with the split.

## 7. Migration order

1. Install the tmpfs (§2) in `rbr-setup.sh`, and move `thermometers.json`, `heatlog-state.json`, `zigbee-temperatures.json` and (optionally) the dashboard JSON onto it. The bridge's atomic write creates its temp file in `script_dir`, so the temp file and the target must move together onto the same filesystem.
2. Verify cold start with an empty RAM disk: every room should come up `fail` with its relay off until fresh readings arrive, and the dashboard should regenerate.
3. Split `map.json` by field (§6), gate the minute write on `MapHasChanged`, and move the reading fields to RAM. This is the step that removes the 1,440 daily writes and is worth validating on its own. Do the field sweep of §9 in the same pass — it is the same migration.
4. Retire RBR-Now (§9), in the code-first order that section sets out.
5. Decide the journal question (§3).
6. Add a refresh-and-restore step (§5, option 2 or 3) only if continuity across a reboot turns out to matter in practice.

## 8. Consequences elsewhere

- [CONTROLLER-FILES.md](CONTROLLER-FILES.md) lists `thermometers.json`, `zigbee-temperatures.json` and `map.json` as living in the controller directory; three of them move or change status and that table needs updating, along with the "live data" annotations.
- [04-controller-computer.md](../docs/preparation/04-controller-computer.md) is the natural home for the mechanism once it exists — the mount, the split, and the refresh policy — replacing the current statement of intent. It is also where the "logs are volatile" claim should be qualified with how the logs are actually made volatile.
- `rbr-watchdog.sh` and `rbr-mapbackup.py` both read `map.json` and are unaffected as long as the plan stays on disk.
- The `--no-dashboard` service flag means a headless controller only ever writes the dashboard JSON, never paints a terminal; the file's location matters more than its latency, so moving it to the RAM disk is safe and tidy.

## 9. Coupled change: retiring RBR-Now

The RAM disk and the removal of RBR-Now are best done together, because both edit the same map schema — so the schema migration happens once rather than twice, with one revision of `CONTROLLER-FILES.md`, one of `rbr-setup.sh` and one of the map fixtures. This section records what the removal covers, where it genuinely simplifies the storage design, and the field sweep that falls out of doing them together.

It is worth being clear first about where the coupling is *not*. **RBR-Now contributes no disk writes at all** — `deviceControl.allspeak` contains no `save` anywhere, only a `load` — so the write volume this proposal addresses is entirely Zigbee-side (`map.json`, `thermometers.json`, `zigbee-temperatures.json`). The removal simplifies the *design* in three places, and none of them is about write volume:

- **The readings get a single origin.** `Thermometers` is fed today by two paths: the once-a-minute merge from `zigbee-temperatures.json`, and `RecordThermometer`, which parses Mijia BLE announcements out of RBR-Now relay replies during room processing. Remove the second and the bridge file is the sole source *and* the sole writer, so the volatile set is exactly one file for readings, with nothing repopulating it in-process from a relay's reply.
- **The fail-safe argument in §4 loses its only caveat.** The safety override that keeps a room's relay off regardless of mode exists precisely because "an RBR-Now relay [could report] its own temperature when the configured thermometer is dead", which could keep `TempNow` populated past the staleness gate. With RBR-Now gone the staleness gate is the single path, and "empty readings → `fail` → relay off" becomes unconditional — which is the exact claim cold start rests on.
- **One fewer persistent file, and a startup wart with it.** `config.json` sits in the controller directory only because `deviceControl.allspeak` loads it unguarded; `rbr-setup.sh` STEP 5c creates an empty one on a Zigbee-only machine purely so the service does not crash-loop. Both go — one fewer row in the classification table of §1.

### What the removal covers

| Where | What goes |
|---|---|
| `deviceControl.allspeak` | the `load Config from config.json` master lookup (`SetupDeviceController`), `MessageESPDevice`, and the `relayType` dispatch branch (line 119) |
| `controller.allspeak` | `RecordThermometer` with its Mijia/BLE parsing, the ESP reply parsing in `ProcessReply`, and `relayType` in the `RoomSpec` packet (line 827) |
| `config.json` + `rbr-setup.sh` STEP 5c | the whole file, and the step that creates it |
| `new-ui` | the RBR-Now/Zigbee pill in `device-editor.allspeak`, and the default at line 283 that reads an empty `relayType` as `RBR-Now` |
| `RBRNow/` | the ESP32 MicroPython firmware (repository only — not shipped to controllers) |
| `resources/allspeak/config.allspeak` | the legacy UI's RBR-Now provisioning screen, still deployed by `deploy.sh` |
| docs | `doc/configurator.md` (13 mentions), `doc/setupHardware.md`, `AI/MAP_FORMAT.md`, `AI/PROJECT_OVERVIEW.md`, `docs/installation/06` Step 5c, and `docs/README.md` item 7, which links to `docs/technical/07-legacy-rbr-now.md` — a page that was never written |

What it does **not** reach is MQTT. The controller's MQTT is the UI transport (`ServerTopic` / `SenderTopic`, pushing the map and messages to the connected PWAs), and the same broker fronts `zigbee2mqtt`, so `credentials`, `.mqtt_password`, `.mac_override` and `mosquitto` all stay.

### The field sweep

Two fields are RBR-Now's; the sweep for other dead fields found six more. Retirement and sweep are one migration.

| Field | Evidence | Verdict |
|---|---|---|
| room `relayType` | read by the dispatch, `controller.allspeak:827`, `diagnose.allspeak:194`, the new UI and the legacy UI | **retire** — with RBR-Now gone it distinguishes nothing |
| room `ssid` | `deviceControl.allspeak:143` reads `ssid` from the *config.json device*, never from the room | **retire** — already vestigial |
| map `address`, `extenders`, `controller-ssid`, `controller-password`, `user-password` | zero references anywhere in the current system | **retire** |
| map `ssid`, `password`, `email` | read as map fields only by `resources/allspeak/*` (the legacy UI). The controller and the new UI use those words for MQTT and registration credentials, never as a map entry (no `of Map` reference resolves to any of them) | **retire** |
| map `message` | the legacy UI's banner; the controller's `message` is EasyCoder messaging (`entry message of ReceivedMessage`), a different thing | **retire** |

Kept, and not RBR-Now: `linked` (line 1033 — `linked: no` is the real "drive the relay by mode rather than by target/temperature" feature), `advance`, `prevmode`, `until`, `period`, `periods`, `events`, `relays`, `sensor`, `protect`, `ptemp`, and the map's `name`, `profile`, `profiles`, `calendar`, `calendar-data`, `background-temp`, `overrides`, `request`. Note that `relayfails` (the per-relay failure list, line 947) and `relaysFailed` / `relaysTotal` (the summary counts, lines 1194–1195) are all live and are easy to mistake for each other.

One finding that is **not** part of this change and deserves its own look: the controller never reads `protect` or `ptemp` — zero references in `controller.allspeak`. They are written by the new UI's frost sheet and read by the legacy room editor, so they are UI-owned rather than dead, but as far as the controller is concerned frost protection currently has no effect.

### Sequencing and cautions

- **"Blank means Zigbee" must be explicit before `relayType` goes.** The live map has 21 rooms tagged `Zigbee` and three blank; all three blank ones are benign today (they are `Outside`, with `relays: []`, so the dispatch loop never runs), but the rule has to be stated and the device editor's default changed from `RBR-Now` to `Zigbee` — line 570 already uses `Zigbee` for a new room, so the file contradicts itself as it stands.
- **Order against the updater.** The versioned tarball ships `controller.allspeak` and `deviceControl.allspeak` automatically, so a controller can take the new code while its `config.json` is still absent or stale. Remove the unguarded `load Config from config.json` in the same release as STEP 5c and the file — never delete the file first.
- **Fixtures to regenerate:** `map-sim.json` still holds 24 RBR-Now rooms (and `events`), and `map-new.json`, `map-clean.json`, `new-ui/demo-map.json`, `resources/json/defaultmap.json` and `resources/json/newroomspec.json` all carry retired fields.
- **The tooling already exists.** This is the same shape as `migrate-periods.allspeak` and `cleanup-map.allspeak` — read `map.json`, write a new file, inspect, diff, then move it into place — so the field sweep rides along with the plan/readings split of §6 rather than needing new machinery.

## 10. What was implemented

Both halves were built on 2026-10-16. Three decisions taken while implementing differ from what the sections above sketch, and each is recorded here rather than left to be rediscovered.

**The volatile directory is `/run/rbr`, created by a `tmpfiles.d` drop-in — not a mount.** `/run` is already a tmpfs on any systemd distribution, so the directory is volatile by construction: no fstab entry, no mount unit, no ordering to get wrong, and nothing to size. `rbr-setup.sh` writes `/etc/tmpfiles.d/rbr-volatile.conf` and the one-line `volatile-root` file that names the path. Four files moved into it: `thermometers.json`, `heatlog-state.json`, `zigbee-temperatures.json` and `rbr-dashboard.json` — the last because the controller rewrites it on every loop cycle, which made it a heavier writer than the map.

**The path is configurable, not hard-coded.** `volatile-root` is one line naming an absolute directory, the same pattern `heatlog-root` already uses. `controller.allspeak`, `diagnose.allspeak`, `zigbee-bridge.py` and `rbr-dashboard.py` all resolve it, and with no such file every one of them falls back to plain names beside the code — so a dev machine and the test suite keep behaving exactly as before.

**The map keeps its readings in memory and drops them on the way to the disk.** §6 proposed splitting the plan and the readings by field, and the implementation does that at write time rather than by tracking which fields changed: `PrepareMapForDisk` builds a copy of the map with those eleven fields deleted, and the tick writes only when that text differs from the text it last wrote. `relayfails` is deliberately kept — it is stable while the relays are answering, and losing it to a restart would delay the next fault being noticed. This reaches the same end as the section's field split (the readings never reach the disk, and the file is written only when the plan changes) without needing to enumerate every mutation site, which is where the risk would have been.

One AllSpeak trap was established in the process and is worth remembering: **assigning one json variable to another aliases them**, so `put Map into MapDisk` followed by `delete entry … of MapDisk` would delete the field from the live map. The copy idiom that does work is `put prettify X into T` and then `put json T into Y`. The behaviour was confirmed against the runtime before the code was written.

### Verified by running it

The full loop was run against a local MQTT broker and a stub stand-in for the Zigbee bridge — the first time this code has executed end to end, and it earned its keep twice.

- **`LastMapDiskText` was not initialised, and the controller died at its first minute tick.** AllSpeak refuses to compare an unset variable with anything ("Both items must have a value for comparison"), and the guard in `HandleMessages` compares that variable on its first run. Under `controller.service` (`Restart=always`) this would have been a crash loop every sixty seconds — run for a minute, die, restart, die again, indefinitely. Fixed by initialising it to empty in the startup block, where empty is exactly right: no map text can equal it, so the first tick always writes.
- **A pre-existing bug on the same path: with no `.version` file the controller stopped about a minute after every start.** The version watch loads `.version` and then `replace`s in it unguarded; on a machine with no `.version` — one installed by hand rather than through `get-controller.sh` — the load left the variable unset and the `replace` raised. The read is now guarded like everything else on that path. This was not part of this work; it was found by doing the work.

With both fixed, a run of several minutes produced no errors at all, and the behaviour is what the design claims:

- the controller logged `Volatile data in /tmp/e2e/ram/` and wrote **`thermometers.json` into the volatile directory**, having read `zigbee-temperatures.json` from it — both halves of the volatile path, in a real run;
- `map.json` was written once, at the first tick, and **not rewritten at the second** — identical mtime and identical md5 — which is the write the whole change exists to remove;
- the written map holds the plan and `relayfails`, and **none of the eleven derived fields**, checked field by field in the file that was actually produced;
- the RBR-Now-free device module drove the stub bridge successfully, so the rewritten transport is exercised rather than merely compiled.

What is still not verified is real hardware: no relay or thermometer has driven this, and no power cut has been staged.

### Also done in the same pass

- **The journal is volatile.** `rbr-setup.sh` STEP 5d writes `/etc/systemd/journald.conf.d/rbr.conf` with `Storage=volatile` and `RuntimeMaxUse=64M`, so the log lives in `/run/log/journal` and never reaches the card or the disk. The trade-off is stated in the script itself, with the one-line revert: a volatile journal disappears in exactly the incident where the last few lines are wanted, and what makes it acceptable is that `controller.service` runs unbuffered, so its lines reach the journal as they are written.
- **The RBR-Now firmware and toolchain are gone**, not archived in place: `RBRNow/` (26 files of ESP32 MicroPython), the legacy configurator `resources/allspeak/config.allspeak` (orphaned — nothing loaded it), and `flash-device.allspeak`, which existed only to flash `RBRNow/` onto a device and could not work without it. All three are in git history. `doc/configurator.md` and `doc/setupHardware.md` are kept as the only description of how the hardware worked, with banners saying plainly that nothing in them can be run any more.
- **The tracked map fixtures were swept**: `map.json`, `map-clean.json`, `map-new.json`, `map-sim.json`, `resources/allspeak/map.json` and `resources/json/newroomspec.json` no longer carry `relayType`, the room `ssid` or the nine legacy map-level fields.

### Left open

1. **The legacy UI's own RBR-Now screens.** `resources/allspeak/{roomedit,roomtools,rbr,mode}.allspeak`, `resources/webson/getdevices.json` and a stale copy of the device module at `resources/allspeak/deviceControl.allspeak` still offer a relay-type choice and carry the ESP transport. They are inert — the controller ignores the field, and nothing loads the stale device module — and `resources/` is the legacy UI, which is itself due to be deleted, so editing its screens now would be throwaway work.
2. **Nothing is verified on real hardware.** The loop was run end to end against a local broker and a stub bridge (see below), but no real relay or thermometer has driven it, and no power cut has been staged.

## Open questions

- Should the RAM disk survive a clean reboot? If continuity across an ordinary planned restart is wanted, the refresh step stops being optional — but the plan and the command state are already on disk, so what is recovered is only the UI's view.
- When `resources/` is deleted, does `doc/configurator.md` and `doc/setupHardware.md` go with it? They are the only description of the RBR-Now hardware, and they survive only for installations built before the retirement.
- Frost protection: are `protect` / `ptemp` meant to be controller-side, or is the new UI's local computation the whole design? Nothing in this proposal depends on the answer, but the sweep turned it up.
