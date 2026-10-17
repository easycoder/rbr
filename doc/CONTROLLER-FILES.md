# Files needed on the RBR controller #

This is the definitive list of files a controller computer needs in order to run RBR. It was arrived at empirically by deleting everything from a working controller except the essential files and restoring whatever the running system complained about.

The controller directory does NOT need any of the repo's folders (`resources/`, `new-ui/`, `tests/`, `doc/`, `rbrchat/`, `design/`, `AI/`, `conversation/`, `plugins/`, ...) — every runtime component is a plain file in the directory root. Extra files are harmless, but this list is the minimum.

## Essential — required for the controller to run ##

| File | Purpose | Updated by |
|---|---|---|
| `controller.allspeak` | Main AllSpeak program | auto (rbr-updater.py) |
| `deviceControl.allspeak` | Device module — drives the Zigbee relays through the local bridge | auto (rbr-updater.py) |
| `zigbee-bridge.py` | HTTP↔MQTT bridge daemon (port 8889), writes `zigbee-temperatures.json` | manual |
| `zigbee-pair.py` | Tool for pairing Zigbee devices | manual |
| `zigbee-mesh.py` | Shows the Zigbee mesh as the coordinator sees it — each device's parent, link quality, weak links, and (with `--failures`) which relays are failing to acknowledge | manual |
| `rbr-dashboard.py` | Terminal dashboard renderer (reads `/tmp/rbr-dashboard.json` written by the controller) | manual |
| `dashboard.txt` | Dashboard column headers — read by `rbr-dashboard.py` | manual |
| `rbr-updater.py` | Applies code updates pulled from `rbrheating.com/heat/` (installed as an hourly timer) | auto (rbr-updater.py) |
| `rbr-watchdog.sh` | Hourly health check — restarts any core service that is down | auto (rbr-updater.py) |
| `rbr-mapbackup.py` | Keeps the last 10 valid `map.json` revisions and repairs a truncated map (2-minute timer) | auto (rbr-updater.py) |
| `credentials` | MQTT broker credentials — created by `rbr-setup.sh` | generated |
| `.mqtt_password` | Stored MQTT password — created by `rbr-setup.sh` | generated |
| `.mac_override` | Controller MAC (MQTT topic identity) — created by `rbr-setup.sh` | generated |
| `.version` | Local version stamp, compared against the `VERSION` inside `rbrheating.com/heat/rbr-controller.tar.gz` | auto (rbr-updater.py) |
| `map.json` | Room/schedule data — read AND written by the controller, and written only when the plan changes (the readings are stripped from the copy that reaches the disk) | live data |
| `map-last-good.json` | Newest valid `map.json`, written by `rbr-mapbackup.py` — restored over a damaged map | live data |
| `map-history/` | Rolling copies of the last 10 valid maps, written by `rbr-mapbackup.py` | live data |
| `volatile-root` | One line: the directory holding the regenerable files below. `rbr-setup.sh` writes `/run/rbr`, which is a tmpfs and is emptied on every reboot. With no such file the paths stay plain names in this directory (what a test machine gets) | generated |
| `thermometers.json` | Temperature readings — created on first run. In the volatile directory | volatile |
| `zigbee-temperatures.json` | Zigbee readings written by the bridge, merged by the controller. In the volatile directory | volatile |
| `heatlog-state.json` | Per-room last-logged target/actual/mode, so a restart does not re-log the current state. In the volatile directory | volatile |
| `rbr-setup.sh` | The installer itself — keep it so setup can be re-run | manual |

Everything marked **volatile** is regenerated within minutes and is deliberately lost on a reboot (`rbr-dashboard.json`, the terminal dashboard's state, is the fourth member of that set and is written only when the dashboard is on). Nothing needs backing up from there.

## Optional — only if you need these features ##

| File | Needed when |
|---|---|
| `simulator.allspeak` | Simulation mode — only if a file named `sim` exists (see `controller.allspeak` init) |
| `zigbee-config.json` | Optional — the bridge works without it, falling back to `localhost:1883` / port 8889. `rbr-setup.sh` creates it with broker details. |
| `asedit.allspeak`, `asedit.json`, `edit.html`, `server.allspeak` | Running the AllSpeak editor on the controller: `allspeak server.allspeak [port]`, or `allspeak viz [port]` to open the visualiser as well. `server.allspeak` must be kept current — a copy from before 2026-10-12 answers `503 Server handler not ready` to every request and reports nothing; refresh it with `curl -fsS https://allspeak.ai/code/server.allspeak -o server.allspeak` |
| `index.html`, `favicon.ico` | Only if you serve the web UI locally from this directory (e.g. `python3 -m http.server`) |
| `.htaccess` | Only if Apache serves this directory (ignored by `http.server`) |

## NOT needed on the controller ##

| File | Why it's there / where it belongs |
|---|---|
| `version` (no dot) | Nothing on a controller reads it — the updater uses `.version`. Leftover from the in-controller `CheckForUpdate`. |
| `.chat-version` | Chat is a server-side web app |
| `.gitignore`, `.stignore` | Repo hygiene for the dev machine |
| `.venv/` | Services use the system `python3`; not required |
| `migrate-periods.allspeak`, `cleanup-map.allspeak`, `retire-rbr-now.allspeak` | One-shot map migrations — run on the dev machine, or copied over for a single run when an existing map needs rewriting |
| `deploy.sh`, `resources/`, `new-ui/`, `.htaccess`, `auth.php`, `credentials.php` | Cloud server (pushed by `deploy.sh`) |
| `tests/`, `doc/`, `design/`, `AI/`, `conversation/`, `RBRNow/`, `rbrchat/`, `plugins/`, `node_modules/` | Dev machine / firmware / other projects |

## How updates work today ##

1. **Auto-updated (the controller runtime):** the standalone updater, `rbr-updater.py`, is driven by an hourly systemd timer. It fetches `https://rbrheating.com/heat/rbr-controller.tar.gz`, compares the `VERSION` stamp inside it with the local `.version`, and if the remote is newer swaps in the changed files and restarts the services they belong to. The controller also watches `.version` (about once a minute) and exits when it changes, so a supervised controller relaunches onto the new code.
2. **Trigger:** on the dev machine, `./deploy.sh --release` rebuilds the tarball and the install pack with a bumped version stamp and publishes `/heat/` on the site. `./deploy.sh` without `--release` uploads the files without publishing them (for smoke-testing).
3. **The old in-controller `CheckForUpdate` is gone.** It has been replaced by the standalone updater described in [UPDATE-MECHANISM.md](UPDATE-MECHANISM.md); the `.allspeak` sources are still published to `/heat/` beside the tarball, but nothing on a controller pulls them individually any more.
