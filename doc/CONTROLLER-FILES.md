# Files needed on the RBR controller #

This is the definitive list of files a controller computer needs in order to run RBR. It was arrived at empirically by deleting everything from a working controller except the essential files and restoring whatever the running system complained about.

The controller directory does NOT need any of the repo's folders (`new-ui/`, `desktop/`, `tests/`, `doc/`, `docs/`, `design/`, `AI/`, `conversation/`, ...) — every runtime component is a plain file in the directory root. Extra files are harmless, but this list is the minimum.

## Essential — required for the controller to run ##

| File | Purpose | Updated by |
|---|---|---|
| `controller.allspeak` | Main AllSpeak program | auto (rbr-updater.py) |
| `deviceControl.allspeak` | Device module — drives the Zigbee relays through the local bridge | auto (rbr-updater.py) |
| `zigbee-bridge.py` | HTTP↔MQTT bridge daemon (port 8889), writes `zigbee-temperatures.json` | manual |
| `zigbee-pair.py` | Tool for pairing Zigbee devices | manual |
| `zigbee-mesh.py` | Shows the Zigbee mesh as the coordinator sees it — each device's parent, link quality, weak links, and (with `--failures`) which relays are failing to acknowledge | manual |
| `rbr-dashboard.py` | Terminal dashboard renderer (reads `/tmp/rbr-dashboard.json` written by the controller) | manual |
| `eventlog.py` | Append-only writer for the controller event journal (see `EVENT-JOURNAL.md`) | auto (rbr-updater.py) |
| `dashboard.txt` | Dashboard column headers — read by `rbr-dashboard.py` | manual |
| `rbr-updater.py` | Applies code updates pulled from `rbrheating.com/heat/` (installed as an hourly timer) | auto (rbr-updater.py) |
| `rbr-watchdog.sh` | 15-minute health check — restarts any core service that is down or unresponsive, and runs the heating check | auto (rbr-updater.py) |
| `heatwatch.py` | Heating check — restarts all four core services when a scheduled room has not warmed for an hour; called by `rbr-watchdog.sh` | auto (rbr-updater.py) |
| `rbr-mapbackup.py` | Keeps the last 10 valid `map.json` revisions and repairs a truncated map (2-minute timer) | auto (rbr-updater.py) |
| `rbr-backup.py` | Writes the monthly archive of the plan, credentials and Zigbee2MQTT data, and emails it when the Backups sheet has it enabled (monthly timer) | auto (rbr-updater.py) |
| `rbr-restore.py` | Restores one of those archives onto a fresh install — run by hand after setup | auto (rbr-updater.py) |
| `credentials` | MQTT and mail credentials — created by `rbr-setup.sh` on first install and never overwritten by a re-run | generated |
| `.mqtt_password` | Stored MQTT password — created by `rbr-setup.sh` | generated |
| `.mac_override` | Controller MAC (MQTT topic identity) — created by `rbr-setup.sh` | generated |
| `.version` | Local version stamp, compared against the `VERSION` inside `rbrheating.com/heat/rbr-controller.tar.gz` | auto (rbr-updater.py) |
| `map.json` | Room/schedule data — read AND written by the controller, and written only when the plan changes (the readings are stripped from the copy that reaches the disk) | live data |
| `map-last-good.json` | Newest valid `map.json`, written by `rbr-mapbackup.py` — restored over a damaged map | live data |
| `map-history/` | Rolling copies of the last 10 valid maps, written by `rbr-mapbackup.py` | live data |
| `backup/` | Monthly archives written by `rbr-backup.py`; the newest 12 are kept | live data |
| `journal-root` | One line: the event-journal data root. Optional — absent, a machine with `heatlog-root` uses `<heatlog-root>/events` | generated |
| `journal-max-bytes` | Optional one-line absolute journal cap, e.g. `1G` or `1073741824`; default 1 GiB, `0` disables | generated |
| `journal-max-free-percent` | Optional one-line cap as a percentage of the filesystem's free space; default 10, `0` disables | generated |
| `backup-config.json` | The Backups sheet's email toggle and the registered address; written by the controller | live data |
| `backup-status.json` | The last backup's result, for the Backups sheet; written by `rbr-backup.py` | live data |
| `<journal-root>/` | Daily event files and content-addressed map snapshots; delete old days freely | live data |
| `volatile-root` | One line: the directory holding the regenerable files below. `rbr-setup.sh` writes `/run/rbr`, which is a tmpfs and is emptied on every reboot. With no such file the paths stay plain names in this directory (what a test machine gets) | generated |
| `thermometers.json` | Temperature readings — created on first run. In the volatile directory | volatile |
| `zigbee-temperatures.json` | Zigbee readings written by the bridge, merged by the controller. In the volatile directory | volatile |
| `zigbee-trv.json` | TRV setpoint/mode, reported local and external temperatures, and the selected temperature source, written by the bridge for the controller's dial-change sync. In the volatile directory | volatile |
| `heatlog-state.json` | Per-room last-logged target/actual/mode, so a restart does not re-log the current state. In the volatile directory | volatile |
| `heat-watch-state.json` | Per-room demand baseline and the restart cooldown for the heating check. In the volatile directory | volatile |
| `rbr-setup.sh` | The installer itself — shipped in the tarball so an existing controller can re-run the current one; the updater replaces it but never runs it | auto (rbr-updater.py) |

Everything marked **volatile** is regenerated within minutes and is deliberately lost on a reboot (`rbr-dashboard.json`, the terminal dashboard's state, is another member of that set and is written only when the dashboard is on; `heat-watch-state.json` is the heating check's baseline and cooldown, so a reboot starts its next window clean). Nothing needs backing up from there.

## Optional — only if you need these features ##

| File | Needed when |
|---|---|
| `simulator.allspeak` | Simulation mode — only if a file named `sim` exists (see `controller.allspeak` init) |
| `zigbee-config.json` | Optional — the bridge works without it, falling back to `localhost:1883` / port 8889. `rbr-setup.sh` creates it with broker details. |
| `server.allspeak` | Running the AllSpeak dev server on the controller: `allspeak server.allspeak [port]`, or `allspeak viz [port]` to open the visualiser as well. `server.allspeak` must be kept current — a copy from before 2026-10-12 answers `503 Server handler not ready` to every request and reports nothing; refresh it with `curl -fsS https://allspeak.ai/code/server.allspeak -o server.allspeak` |
| `.htaccess` | Only if Apache serves this directory (ignored by `http.server`) |

## NOT needed on the controller ##

| File | Why it's there / where it belongs |
|---|---|
| `version` (no dot) | Nothing on a controller reads it — the updater uses `.version`. Leftover from the in-controller `CheckForUpdate`. |
| `.chat-version` | Chat is a server-side web app |
| `.gitignore`, `.stignore` | Repo hygiene for the dev machine |
| `.venv/` | Services use the system `python3`; not required |
| `deploy.sh`, `index.html`, `new-ui/`, `.htaccess`, `auth.php`, `credentials.php` | Cloud server (pushed by `deploy.sh`) |
| `tests/`, `doc/`, `docs/`, `desktop/`, `design/`, `AI/`, `conversation/`, `node_modules/` | Dev machine |

## Backups ##

`rbr-backup.py` runs from `rbr-backup.service` + `rbr-backup.timer` on the first of every month at 03:00, with `Persistent=true` so a machine that was off catches up on its next boot. It writes one ZIP into `backup/`, prunes to the newest 12, and records the outcome in `backup-status.json`. The archive holds the controller's own state (`map.json`, its history, `credentials`, `zigbee-config.json`, `.mac_override`, `.mqtt_*`, the root markers and `backup-config.json`) and all of Zigbee2MQTT's data directory — `configuration.yaml` with the network key, a consistent snapshot of `database.db`, `coordinator_backup.json` and external converters. Code is not included: a fresh install gets that from rbrheating.com.

The archive therefore contains the secrets that let a rebuilt controller rejoin the mesh. Archives are written mode 0600 and should be treated as sensitive.

Email is opt-in from the app's **Menu → Backups** sheet. The sheet writes `backup-config.json` with `enabled` and the registered address, so the timer can send its copy with no browser open. The recipient falls back to the address the cloud holds for this controller (via `.mqtt_token`) and then to `mail_to` in `credentials`. Mail itself uses the `mail_*` settings in `credentials`, which `rbr-setup.sh` asks for when it writes the file (skipping them leaves the placeholder SMTP server, which keeps the local archive intact and reports the failure in `backup-status.json`, which the sheet shows).

To restore after a fresh install:

```sh
sudo python3 rbr-restore.py rbr-backup-YYYYMMDD-HHMMSS.zip
```

It verifies the manifest and every checksum, refuses paths that would escape the destination, snapshots what is already there under `pre-restore-<timestamp>/`, restores ownership and permissions, and restarts the services. `--dry-run` lists the files without changing anything.

## How updates work today ##

1. **Auto-updated (the controller runtime):** the standalone updater, `rbr-updater.py`, is driven by an hourly systemd timer. It fetches `https://rbrheating.com/heat/rbr-controller.tar.gz`, compares the `VERSION` stamp inside it with the local `.version`, and if the remote is newer swaps in the changed files and restarts the services they belong to. The controller also watches `.version` (about once a minute) and exits when it changes, so a supervised controller relaunches onto the new code.
2. **Trigger:** on the dev machine, `./deploy.sh --release` rebuilds the tarball and the install pack with a bumped version stamp and publishes `/heat/` on the site. `./deploy.sh` without `--release` uploads the files without publishing them (for smoke-testing).
3. **The old in-controller `CheckForUpdate` is gone.** It has been replaced by the standalone updater described in [UPDATE-MECHANISM.md](UPDATE-MECHANISM.md); the `.allspeak` sources are still published to `/heat/` beside the tarball, but nothing on a controller pulls them individually any more.
