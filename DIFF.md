# 2026-11-17 — controller crash loop, blank-screen wedge, doctor probe

**Action:** `./deploy.sh` publishes the changed files (`controller.allspeak`, `rbr-watchdog.sh`, `rbr-doctor.py`). Without `--release` the version stamp does not change, so a running controller will not notice — restart it yourself to try the fix (`sudo systemctl restart controller`). `./deploy.sh --release` when customers should take it; their updater applies the tarball on its next hourly run and the controller restarts to load the new code. No database or map change, and nothing to clear.

## The crash loop (`controller.allspeak`)

`ProcessTrvState` converted the TRV's `last_seen` with `multiply TrvSeen by 1000`, which turns text into a number with `int()`. The bridge writes `last_seen` as a float epoch (`1794857533.0439382`), and a decimal is a string in AllSpeak, so the conversion raised and stopped the process — 73–74 seconds into every session, about 45 times an hour. On 16 Nov the journal has 1,014 session starts; every hour of the 15th and 16th has 45–46. It has been going since the block was added on 26 Oct.

The conversion is now `put TrvSeen scale 1000 into TrvSeen`, the decimal-safe operator `ConvertTempToInt` already uses. The routine always uses the once-a-minute `zigbee-trv.json` load, so the first failure came a minute after each start — that is why sessions lasted 74 seconds rather than dying immediately.

`tests/unit/trv_state_test.py` extracts `ProcessTrvState` from the controller and runs it against a fractional `last_seen`, an old integer one, a stale one (46 minutes), a missing one and a non-heat/idle value. With the old `multiply` line it reproduces the live error verbatim.

## The blank screen (`rbr-watchdog.sh`)

The controller was the one service with no health probe (`probe_controller() { return 0; }`), so a process that was alive and subscribed but had never run its start-up was restarted by nobody: 107 minutes on 16 Nov, over 70 on the 17th. The probe now reads the unit's recent log for `Subscribed to topic` with no `Load the system map` after it, and restarts when that has stood for more than two minutes. The grace keeps a normal start (seconds) and the 5-second restart gap out of it.

`tests/unit/watchdog_probe_test.py` runs the real script with fake `systemctl`/`journalctl`/`logger`, and checks that a healthy start, a session still starting and an empty journal do not restart, while a subscribed-but-never-started session does.

## The doctor's round trip (`rbr-doctor.py`)

The probe published bare JSON, which the AllSpeak MQTT runtime drops ("WARNING: ignoring unframed payload"), so `ROUND TRIP [FAIL]` fired on a healthy controller too. It now sends `!last!1 ` plus the body, and reassembles a chunked reply (a full map is split at 1024 bytes) before reporting. `tests/unit/doctor_test.py` pins both.

## Not fixed here

The wedge itself is a runtime defect: a connect event that arrives before `on mqtt connect` is registered is never delivered, and `is_first_connect` never comes back. That change belongs in AllSpeak; the row is in `REQUESTS.md`. The watchdog is the safety net until the runtime on the boxes is updated.

`ProcessTrvState`'s doc block still lacks its `@hash`/`@verified`/`!!!` tail and its prose is read as part of the previous block (`asdoc-check` reports `doc-after-code`). Left as found; the code comment here is short enough not to depend on it.

## What the box should look like afterwards

`journalctl -u controller | grep -c 'Load the system map'` should stop growing faster than the restarts, and `Arithmetic error in multiply: … '17….'` should stop appearing. The controller will then run until the next version update instead of dying every 79 seconds, so `systemctl status controller` should show a rising uptime rather than a five-minute one. The UI's toggle stays connected for the same reason.
