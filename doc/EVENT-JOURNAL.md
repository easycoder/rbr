# Event journal

The controller records **events**, not only outcomes. The heating CSV in
`doc/HEATING-DATA.md` is a projection of this journal: it samples target,
actual and mode whenever they change. The journal keeps the inputs and
decisions that produced those rows, so a day can be replayed as a Scenario
Studio scenario instead of reconstructed from guessed causes.

## Where it lives

```
<journal-root>/<YYYY>/<MM>/<YYYY-MM-DD>.jsonl
<journal-root>/maps/<sha256>.json
```

All events for a local day share one append-only JSONL file, in event order.
`<journal-root>` is the one-line content of a `journal-root` file in the
controller's working directory. If that file is absent, a machine with
`heatlog-root` gets `<heatlog-root>/events`, so event recording starts with
the same release and no extra setup. If neither exists, the journal is off
and the controller says so at startup.

The root should be on the data partition (the same one as `heatlog-root` on
a controller) rather than the RAM directory. Old day files can be deleted or
compressed freely; nothing in the controller reads them back.

Map snapshots are stored once under `maps/` and referenced by `mapHash` from
the event line. A session-start snapshot is taken after the first control
cycle, and a `plan.snapshot` is taken after a request that changes the plan
(`System Name`, `Request Relay`, `Add Room`, `Update Rooms`, `Select
Profile`, `Update Profiles`, `Room Override`, `Backup`). Identical maps share
one file.

## Event envelope

Every line is one JSON object:

```json
{"v":1,"tsMs":1788177603421,"seq":10421,"boot":1788177000000,
 "type":"sensor.reading","data":{"room":"Kitchen","sensor":"Kitchen-thermometer",
 "temp":1840,"sourceTsMs":1788177588000,"source":"zigbee","humidity":58,"battery":90},
 "ts":"2026-11-06T07:12:03.421+00:00","tzOffsetMinutes":60}
```

| Field | Meaning |
|---|---|
| `v` | Journal schema version (`1`). |
| `tsMs` | Controller wall clock, epoch milliseconds. |
| `seq` | Monotonic within a boot. Together with `boot`, gives event order even when timestamps collide. |
| `boot` | Controller start instant; distinguishes a restart from a continuous run. |
| `type` | Event type (below). |
| `data` | Type-specific payload. |
| `ts` | Local ISO timestamp, added by `eventlog.py`. |
| `tzOffsetMinutes` | Local offset at `tsMs`, added by `eventlog.py`. The path's date and the controller's schedules both use local time. |

## Event types currently written

| Type | When | Principal fields |
|---|---|---|
| `session.start` | Startup, after the first control cycle | `version`, `system`, `profile`, `profileIndex`, `journalRoot`, `map` (stored as `mapHash` + `mapBytes`) |
| `session.stop` | Before the controller exits for an update | `reason` |
| `day.rollover` | Local date changes | `from`, `to` |
| `profile.change` | Calendar or UI changes the active profile | `from`, `to`, `toName` |
| `ui.first` | A UI asks for its first map | `client` |
| `ui.request` | A `uirequest` arrives, before it is applied | `client`, `action`, `payload` (the whole message), `source` (the PWA's provenance), `room` |
| `sensor.reading` | A changed reading, including a repeated value with a new source `ts` | `room`, `sensor`, `temp`, `sourceTsMs`, `source`, `humidity`, `battery` |
| `room.state` | A room's control/status plane changes | `room`, `profile`, `profileIndex`, `mode`, `target`, `period`, `advance`, `advanceuntil`, `until`, `prevmode`, `boostperiod`, `relay`, `status`, `statusMessage`, `relayMessage`, `relaysFailed`, `relaysTotal`, `relayfails`, `trvrunning`, `trvsetpoint`, `trvfails` |
| `plan.snapshot` | A plan-changing request was applied | `reason` (`ui:<Action>`), `profile`, `profileIndex`, `map` (stored as `mapHash` + `mapBytes`) |
| `request.relay` | The demand relay's own state changes | `name`, `state` |

`room.state` deliberately omits `temperature`, `humidity`, `battery` and
`sensorAge`. The first three arrive as `sensor.reading`; `sensorAge` changes
every five-second cycle, and including it would write a line per room per
cycle. Status messages and relay decisions are included because the page
shows them.

The PWA attaches a `Source` object to every outgoing request. It records the
screen, control and gesture that produced it, and the room when one is
involved:

```json
"Source":{"app":"pwa","screen":"home","control":"advance","gesture":"tap","room":"Office"}
```

`ui.request.data.source` is that object. The controller stores it unchanged;
it does not interpret it. A request from an older page, or from a probe,
simply has no `source`.

## How a batch is written

AllSpeak's `save` truncates, and spawning a process per event would be far
too expensive. The controller therefore buffers events in memory and flushes
a batch:

1. Write the batch to `<volatile-root>/journal-<boot>-<n>.json` (or the
   working directory when no `volatile-root` is configured).
2. Run `python3 eventlog.py --root <journal-root> --batch <file> --quiet`
   synchronously. It is a short append, and waiting keeps the lines of
   successive batches in order; a background writer would let a later batch
   overtake an earlier one.
3. `eventlog.py` splits the batch by each event's local date, appends compact
   lines with one `O_APPEND` write per day file, extracts map snapshots, and
   deletes the batch.

Flushes happen once a minute, immediately after a UI request, and before a
restart. A batch file left behind by a killed controller is harmless; it is
not replayed automatically, so a gap in the journal is a real gap. The
`seq` field is the authoritative order if a reader ever sees lines from a
manual replay interleaved with live traffic.

## Watching it grow

```bash
python3 tools/event-journal-report.py /data/rbr-events
watch -n 10 python3 tools/event-journal-report.py /data/rbr-events
```

The report prints bytes and events per day, a breakdown by event type and
the busiest rooms, the map-snapshot size, and a linear 30-day projection.
`--json` gives the same data for a script.

A useful first measurement: a house with N rooms and one sensor per room
produces at most about `N × 1440` `sensor.reading` events per day, because
the controller merges the bridge's readings once a minute. A repeated
reading with a new bridge `ts` is deliberately kept: it is what makes
staleness and heartbeat scenarios possible. `room.state` is change-driven, so
a steady room is nearly silent. UI requests are rare, but an `Update
Profiles` payload can carry every schedule, so a save can be tens of
kilobytes while a mode tap is a few hundred bytes.

A synthetic worst case — 20 rooms, one reading per room per minute, 1,200
room-state changes, 120 UI requests and five plan snapshots — measured
**7.9 MiB for the day**: 7.3 MiB of `sensor.reading`, 402 KiB of
`room.state`, 187 KiB of `ui.request`, and 13 KiB of map snapshots. At that
rate 30 days is about 237 MiB. Gesture provenance is inside the request line
and is negligible; the sensor stream is what dominates. If that is too much,
the first lever is to record a `sensor.reading` only when the value changes
rather than on every new bridge `ts`, at the cost of the staleness/heartbeat
detail.

## Importing and generating a scenario

RBR Studio carries two stdlib-only tools. `tools/rbr-studio/journal_import.py` copies one day and the map snapshots it references into a transport-neutral bundle from a local directory or mounted share. `tools/rbr-studio/journal_to_scenario.py` turns a bundle (or a raw day plus `--map`) into an ordinary scenario JSON for the existing runner. Both accept a window with `--from`/`--to`, and the converter drops repeated sensor readings and duplicate room states, seeds the state that existed before the window, and writes controller steps plus visible expectations. It does not replay recorded UI requests as taps; their controller effects are included, but the gesture itself is not recoverable from the controller's side.

The Studio's **Import journal…** button runs `tools/rbr-studio/journal_ingest.py`, which accepts a bundle, a raw day or a local journal root, chains the importer and converter, and adds the result to the **Journal** group. Everything reads local files; no SSH or other network access to the controller is needed.

The `room.state` change detector uses a hash of the serialised record. The first version compared the JSON text directly, but AllSpeak normalises a JSON-looking string when it is stored in a dictionary, so every cycle looked different and wrote another identical row. A 25-minute live sample showed the difference clearly: 3,350 room-state rows became roughly one per room per minute once the comparison was hash-based. Existing journal files keep their duplicates; the converter suppresses them, and a controller running the fixed code stops writing them.

### Retention limits

`eventlog.py` keeps the journal under an absolute cap and a share of the filesystem's free space. The defaults are **1 GiB** and **10% of current free space**, whichever is smaller. After each flush it deletes the oldest complete day files until the journal fits, but always keeps the day just written; it then deletes map snapshots that no remaining day references. A current day larger than the cap is kept anyway, with a warning, because losing the day being written is worse than exceeding the limit.

Two optional one-line files in the controller's working directory override the defaults: `journal-max-bytes` accepts `1G`, `512M`, a byte count, or `0` to disable the absolute cap; `journal-max-free-percent` takes an integer percentage, or `0` to disable the free-space share. Both are machine-specific, git-ignored and included in the backup of configuration files. The writer prunes before and after appending, so a nearly full disk is relieved even when the batch itself is small.

At the synthetic worst case of 7.9 MiB/day, 1 GiB holds about 130 days. The free-space share usually binds first on a small disk: with 4 GB free, 10% caps the journal at about 400 MB, or roughly 50 days; with 1 GB free it caps at about 100 MB, or roughly 12 days.

## Daily export

`journal-export.py` runs on the controller and makes one compact bundle per day:

    python3 journal-export.py --day 2026-11-06

It reads `<journal-root>/<YYYY>/<MM>/<day>.jsonl`, drops `sensor.reading` events whose temperature, humidity and battery are unchanged, copies the map snapshots the kept events reference, and writes `<journal-root>/exports/<system>-<day>.tar.gz` in the same format as the Studio importer. The default mode is `scenario`; `--mode full` keeps every event, and `--mode summary` drops the sensor stream entirely. `--keep` controls how many archives are retained (default 14, newest first).

When heat logging is enabled, the bundle also carries the day's `<heatlog-root>/<room>/<YYYY>/<MM>/<DD>.csv` files under `reports/heatlog/`, and `manifest.reports` lists them with their rooms, sizes and hashes. `--heatlog-root` names the root; otherwise the `heatlog-root` file is read, and a journal root named `events` uses its parent. The day's outcomes therefore travel with the events that produced them, so one archive serves both RBR Studio and the statistics role. `journal_import.py --heatlog-root` does the same for a local import; the Studio's inbox keeps the extracted `reports/` tree beside the bundle. The manifest also records the controller's `mac` from `.mac_override`, which is what lets a mail filter and the Studio tell several systems apart.

`rbr-journal-export.timer` runs it daily at 03:30 local time. `rbr-setup.sh` installs the service and timer when `journal-export.py` is present. A manual run is safe and does not touch the journal.

The PWA's **Send journal now** row under the hamburger sends a `Journal Now` request. The controller flushes the journal buffer first, then runs `journal-export.py --now --email-now` in the background. `--now` exports today's file as it stands, writes `<journal-root>/exports/requests/<system>-<day>-<HHMMSS>.tar.gz` (separate from the daily exports), and records `partial`, `label` and `requestedAt` in the manifest; the email subject gains the time. RBR Studio imports a partial bundle as its own Journal scenario rather than treating it as a duplicate of the full day. This is the quick evidence path for a bug report.

Email delivery is opt-in, because the bundle carries room names, schedules and the exact UI payloads the user sent. `rbr-setup.sh` asks during Step 6e and writes `journal-export-config.json`:

```json
{"enabled": "yes", "address": "owner@example.com"}
```

With the file absent, or `enabled` not on, the bundle stays local. `--email-now` sends one bundle regardless of the toggle, `--no-email` never sends, and `--to` overrides the recipient. The recipient is the config's `address`, then the address the cloud holds for this controller (via `.mqtt_token`), then `mail_to` in `credentials`. Mail uses the same `mail_*` settings as the backup, through the shared `rbr_mail.py`; a send failure is printed to stderr (the systemd journal) and does not remove the archive or mark the timer failed. The subject is `RBR journal <MAC> <YYYY-MM-DD>`, so a filter can match the system's MAC and direct that system's bundles to its own folder. The attachment is the same `.tar.gz` the exporter writes.

RBR Studio scans a mail-filter folder at startup with `journal_inbox.py`. The folder is `~/RBR-journal` by default, or the path in `studio-config.json` (written by `configure-studio.py`) or a one-line `fixtures/local/journal-inbox` file. The scan includes per-system subfolders such as `~/RBR-journal/00:e0:27:5b:31:40/`, so one filter rule per MAC can keep several systems apart. `studio-config.json`'s `systems` map gives a MAC a useful name (`./run-studio.sh` or `configure-studio.py --system 00:e0:27:5b:31:40=Home`); the name labels the scenario, while the MAC remains the stable folder key. Every unseen `.tar.gz` is extracted into `fixtures/local/journal/<MAC-or-system>-<day>/`, converted into a whole-day scenario and added to the **Journal** group. `fixtures/local/journal/inbox-seen.json` records each archive's SHA-256, so a rescan is a no-op; a corrected bundle has a new hash and is picked up. The same scanner runs by hand with `python3 journal_inbox.py --scan --inbox DIR`.

## Configuration, privacy and retention

- `journal-root` is machine-specific and git-ignored. On a controller with
  `heatlog-root`, the default is `<heatlog-root>/events`.
- The journal contains room names, sensor and relay ids, schedules, occupancy
  patterns and the exact UI payloads the user sent. Keep it local. Do not
  include it in AI prompts or remote drafts without redaction; the Scenario
  Studio prompt deliberately excludes device ids.
- `rbr-backup.py` backs up the `journal-root` *pointer* but not the journal
  itself. A month of events can be much larger than the plan; archive or
  delete day files on whatever schedule suits the installation.
- `eventlog.py` is shipped in the controller release and listed in
  `doc/CONTROLLER-FILES.md`. If it is missing, the controller disables the
  journal with a clear log line rather than failing every flush.

## Tests

- `tools/rbr-studio/tests/journal_check.py` — local import, bundle archive round-trip, mail-inbox import and deduplication, duplicate suppression, value formatting and scenario validation.
- `tests/unit/journal_export_test.py` — daily export modes, retention, bundle compatibility, the `reports/heatlog` rows and the email opt-in, flag overrides and attachment.
- `tests/unit/eventlog_test.py` — the writer: local date paths, midnight and year boundaries, compact JSONL, cross-midnight batches, map content addressing, skipped invalid events and batch deletion.
- `tests/unit/journal_test.py` — extracts the controller's Journal* block and runs it through AllSpeak with a real `eventlog.py`, proving the event order, the provenance field, the map snapshot and the batch writer together.
- `tests/unit/controller-compile-check.sh` — the controller, with the journal routines, must compile.
