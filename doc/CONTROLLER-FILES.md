# Files needed on the RBR controller #

This is the definitive list of files a controller computer needs in order to run RBR.
It was arrived at empirically by deleting everything from a working controller except
the essential files and restoring whatever the running system complained about.

The controller directory does NOT need any of the repo's folders (`resources/`,
`new-ui/`, `tests/`, `doc/`, `RBRNow/`, `rbrchat/`, `design/`, `AI/`, `conversation/`,
`plugins/`, ...) — every runtime component is a plain file in the directory root.
Extra files are harmless, but this list is the minimum.

## Essential — required for the controller to run ##

| File | Purpose | Updated by |
|---|---|---|
| `controller.as` | Main AllSpeak program | auto (CheckForUpdate) |
| `deviceControl.as` | Device module — Zigbee relays + RBR-Now devices | auto (CheckForUpdate) |
| `zigbee-bridge.py` | HTTP↔MQTT bridge daemon (port 8889), writes `zigbee-temperatures.json` | manual |
| `zigbee-pair.py` | Tool for pairing Zigbee devices | manual |
| `rbr-dashboard.py` | Terminal dashboard renderer (reads `/tmp/rbr-dashboard.json` written by the controller) | manual |
| `dashboard.txt` | Dashboard column headers — read by `rbr-dashboard.py` | manual |
| `rbr-updater.py` | Applies code updates pulled from rbrheating.com (installed as an hourly timer) | auto (CheckForUpdate) |
| `rbr-watchdog.sh` | Hourly health check — restarts any core service that is down | auto (CheckForUpdate) |
| `rbr-mapbackup.py` | Keeps the last 10 valid `map.json` revisions and repairs a truncated map (2-minute timer) | auto (CheckForUpdate) |
| `config.json` | RBR-Now device config — read by `deviceControl.as` to find the master device | manual (machine-specific) |
| `credentials` | MQTT broker credentials — created by `rbr-setup.sh` | generated |
| `.mqtt_password` | Stored MQTT password — created by `rbr-setup.sh` | generated |
| `.mac_override` | Controller MAC (MQTT topic identity) — created by `rbr-setup.sh` | generated |
| `.version` | Local version stamp compared against `rbrheating.com/version` | auto (CheckForUpdate) |
| `map.json` | Room/schedule data — read AND written by the controller | live data |
| `map-last-good.json` | Newest valid `map.json`, written by `rbr-mapbackup.py` — restored over a damaged map | live data |
| `map-history/` | Rolling copies of the last 10 valid maps, written by `rbr-mapbackup.py` | live data |
| `thermometers.json` | Temperature readings — created on first run | live data |
| `zigbee-temperatures.json` | Zigbee readings written by the bridge, merged by the controller | live data |
| `rbr-setup.sh` | The installer itself — keep it so setup can be re-run | manual |

## Optional — only if you need these features ##

| File | Needed when |
|---|---|
| `simulator.as` | Simulation mode — only if a file named `sim` exists (see `controller.as` init) |
| `zigbee-config.json` | Optional — the bridge works without it, falling back to `localhost:1883` / port 8889. `rbr-setup.sh` creates it with broker details. |
| `asedit.as`, `asedit.json`, `edit.html`, `server.as` | Running the AllSpeak editor on the controller (`allspeak server.as`) |
| `.code-version` | Used by `server.as` for the editor's own update check — keep it if you run the editor |
| `index.html`, `favicon.ico` | Only if you serve the web UI locally from this directory (e.g. `python3 -m http.server`) |
| `.htaccess` | Only if Apache serves this directory (ignored by `http.server`) |

## NOT needed on the controller ##

| File | Why it's there / where it belongs |
|---|---|
| `version` (no dot) | Nothing reads it — `CheckForUpdate` uses `.version` only. Leftover. |
| `.chat-version` | Chat is a server-side web app |
| `.gitignore`, `.stignore` | Repo hygiene for the dev machine |
| `.venv/` | Services use the system `python3`; not required |
| `deploy.sh`, `resources/`, `new-ui/`, `.htaccess`, `auth.php`, `credentials.php` | Cloud server (pushed by `deploy.sh`) |
| `tests/`, `doc/`, `design/`, `AI/`, `conversation/`, `RBRNow/`, `rbrchat/`, `plugins/`, `node_modules/` | Dev machine / firmware / other projects |

## How updates work today ##

1. **Auto-updated (the `.as` files):** the controller's `CheckForUpdate` routine runs
   hourly from the main loop. It fetches `https://rbrheating.com/version`, compares it
   with the local `.version`, and if the remote is newer downloads
   `controller.as`, `deviceControl.as` and `simulator.as`, moves them into place,
   records the new version, and relaunches itself.
2. **Trigger:** on the dev machine, `./deploy.sh --release` uploads the `.as` files and
   bumps the version stamp. `./deploy.sh` without `--release` uploads files without
   publishing them (for smoke-testing).
3. **Everything else** (Python daemons, `dashboard.txt`, `rbr-setup.sh`) used to
   be manual — copy the file from the repo to the controller and restart the
   affected service. As of the standalone updater (Option B+C), the Python
   daemons and the `.as` files are all shipped in a versioned tarball and
   applied automatically by `rbr-updater.py` — see [UPDATE-MECHANISM.md](UPDATE-MECHANISM.md).
