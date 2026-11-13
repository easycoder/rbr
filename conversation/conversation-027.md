# 2026-11-12

## 10:05

My colleague is having trouble with his system and lacks the knowledge of how to diagnose it.The UI appears to start up and show its background but not populate it, indicating a loss of data connection. He's sent me screenshots that make little sense to me; they're at various/screenshots/ - the images starting with 261112-0. See if you can get anything useful from them.

If we don't already have something similar, I think we need a diagnostic tool for the controller PC, that checks the running state of all the services and gathers any other information that might be useful, then outputs a report that can be redirected to a file. If this is new, let's call it rbr-doctor.py.

**Assistant**

## What the screenshots show

**The UI half is healthy.** The browser console shows the client connecting, subscribing to `40:b0:34:33:22:11/reply-545718` at QoS 1, and logging `Requesting map: first` at 06:41:32. No reply arrives, so the page stays on "Reconnecting…" over an empty background.

**The controller half is not.** `systemctl status controller` shows it active since 04:15:18 (2h 31min, PID 1429914, `NRestarts=69`). Its last visible log lines are `Run Controller`, `AllSpeak version 2610142212`, `MAC address is …`, `Client … connected`, `Subscribed to topic: 40:b0:34:33:22:11` — and then nothing. `Start` begins with `gosub to LoadMap`, whose first action logs `Load the system map`; that line is absent. That combination is the signature of a controller that connected and subscribed but never entered its main loop. systemd sees a live process so it does not restart it; the UI sees a healthy broker connection so it does not fall back; both sit there.

Three things that make this harder to see than it should be:

- The `journalctl … No entries` output is a permissions artefact, not silence. `rbr` is not in `adm` or `systemd-journal`, so `journalctl` refuses for every unit. `systemctl status` still shows the last few lines via PID1. Read the journal with `sudo journalctl -u controller`.
- `systemctl list-timers` listed only `rbr-watchdog.timer`; the hint says `--all` would show loaded-but-inactive timers. So the updater/backup/journal-export timers are not active; whether they are missing or merely stopped needs `--all` or `systemctl status`. That matters because the running AllSpeak runtime is `2610142212` (14 Oct), well behind the `2611091537` in this repo — and that is the runtime, not the controller release.
- `NRestarts=69` under `Restart=always` means it has crash-looped before; the current 2.5-hour process is the one that went quiet. The watchdog cannot catch this state: `rbr-watchdog.sh`'s `probe_controller` is `return 0`, so "active but wedged" always passes. That is a separate gap worth closing.

**Immediate action:** the last screenshot already types `sudo systemctl restart controller`. Do that and watch `sudo journalctl -u controller -f` for `Load the system map`. If it appears, the UI will populate. If it recurs, it is a start-up failure — runtime/controller-code mismatch, unreadable `map.json`, or credentials — not a network problem.

Caveat: this is read from the last ~10 lines `systemctl status` exposes and from a journal `rbr` cannot open. The doctor below proves it by asking the controller directly.

## The tool

Nothing existing covered this: `rbr-preflight.py` is a pre-install check, and `diagnose.allspeak` covers bridge health and room state. Neither inspects running services, timers, the controller journal or proves a broker round-trip. So `rbr-doctor.py` (Python rather than `.sh`, as you allowed: it parses the JSON files, uses the bridge's own `paho` for a real MQTT probe, and keeps the report structured; it is still one copyable file).

`sudo python3 rbr-doctor.py > rbr-doctor.txt`

Options: `--json` for machine-readable, `--no-probe` to skip the round-trip, `--probe-timeout`, `--dir`. Exit 1 if anything is `[FAIL]`.

It reports: install dir and identity/MAC; release, installed runtime and the runtime the running process reports; every service's active/enabled state, restarts, memory, unit file and working directory, plus local port/health probes; every timer's active state and next/last fire, plus the updater's last result; a controller-journal analysis for "Subscribed with no Load the system map", compiler/credential errors, MAC/topic mismatch, code newer than the process, and wrong working directory; `map.json` validity and room/profile counts, thermometers/dashboard age, journal root, disk and inodes; the Linux environment (systemd state, failed units, pending reboot, swap, zombies, duplicate controller processes, cron + systemd double-launch, established broker sockets, interface errors, wireless default route, error-priority journal lines filtered to RBR/hardware/OOM); broker DNS and TCP on 1883/443; and a real `first` request from a throwaway sender, reporting connect failure, publish denial, no reply and empty reply distinctly; Zigbee dongle and z2m config. No passwords are printed or stored; the sender expires from the controller after 100 s.

It is wired into the release: `deploy.sh` (tarball, zip and `/heat`), `rbr-updater.py`'s required-file list, `doc/CONTROLLER-FILES.md`, `doc/UPDATE-MECHANISM.md`, `doc/setupRBR.md` and `AGENTS.md`. After the next `./deploy.sh --release`, his box can `curl -O https://rbrheating.com/heat/rbr-doctor.py`; for now copy the file.

Tests: `tests/unit/doctor_test.py` pins the journal signature and the paho callback contract; it is in `run-unit-tests.sh`. The full suite is green (145 Python tests, the AllSpeak tests, and the whole-controller compile).

Run it on his box first, as root, and send `rbr-doctor.txt`. If the signature holds, its first `[FAIL]` will say so directly; if the controller answers the probe, the report will point at whatever else is wrong.

## 10:20

or rbr-doctor.sh

**Assistant**

Noted — I kept the implementation in Python (`rbr-doctor.py`) because it needs to parse the JSON map and credentials, drive paho for the round-trip probe, and keep both text and `--json` reports structured. It is still a single copyable file with a shebang, so it can be run as `./rbr-doctor.py` or `python3 rbr-doctor.py`; no shell wrapper is needed.

## 10:22

The doctor should also check the Linux environment for anything untoward.

**Assistant**

Added a `LINUX HEALTH` section: `systemctl is-system-running` and every failed unit, pending reboot, inode usage, swap, zombie processes, duplicate controller processes, cron-plus-systemd double-launch, live established broker sockets, interface receive/transmit errors, a wireless default route with signal strength, and error-priority system-journal lines filtered to RBR, hardware, storage, USB and OOM. Those are in addition to the existing disk, memory, clock/NTP, CPU temperature, throttling and kernel-message checks in `SYSTEM`.

## 10:41

I ran it on my system and this is the report. What should I do about the missing JSON update?

RBR doctor — QED6 — 2026-11-12 10:33:24 GMT
install: /home/qed6/rbr (release 2611121029)
run as root (root)


== SYSTEM ==
------------
[ OK ] Debian GNU/Linux 13 (trixie) (kernel 6.12.107+deb13-amd64)
[note] hostname QED6
[ OK ] up 25 d 20 h
[ OK ] clock: Thu 12 Nov 10:33:11 GMT 2026 Europe/London, NTP synchronised
[ OK ] memory available: 3080 MB
[note] load average: 0.51 0.52 0.47
[note] CPU temperature: 35.0 °C
[ OK ] no storage/USB errors in the recent kernel log

== IDENTITY ==
--------------
[ OK ] install directory: /home/qed6/rbr
[ OK ] default route on enp2s0 (00:e0:27:5b:31:40)
[ OK ] .mac_override: 00:e0:27:5b:31:40
[ OK ] credentials present (/home/qed6/rbr/credentials)
[ OK ] volatile data in /run/rbr

== VERSIONS ==
--------------
[ OK ] installed release (.version): 2611121029
[WARN] installed AllSpeak runtime: allspeak not found on PATH or in the usual ~/.local/bin
[ OK ] latest published release: 2611121029

== SERVICES ==
--------------
[ OK ] controller: active — running, up 39 s
[note] controller has restarted 1 time(s) since the unit was loaded
[note] controller main PID 2405504, memory 42 MB
[note] controller unit: /etc/systemd/system/controller.service
[note] run as qed6 in /home/qed6/rbr
[ OK ] mosquitto: active — running, up 3 d 21 h
[note] mosquitto main PID 187428, memory 4 MB
[ OK ] zigbee2mqtt: active — running, up 3 d 21 h
[note] zigbee2mqtt main PID 187443, memory 127 MB
[ OK ] rbr-zigbee-bridge: active — running, up 3 d 21 h
[note] rbr-zigbee-bridge main PID 187453, memory 17 MB
[ OK ] mosquitto listens on 127.0.0.1:1883
[ OK ] zigbee2mqtt frontend answers on 127.0.0.1:8080 (HTTP 200)
[ OK ] rbr-zigbee-bridge /health answers, 18 known device(s)
[WARN] the bridge reports device failures: {'Kitchen-plinth': {'count': 1149, 'last': 1794479542.2382998, 'age': 50}, 'Office-heater': {'count': 242, 'last': 1794453115.0764449, 'age': 26477}, 'Hall-radiator': {'count': 3828, 'last': 1794479414.0631866, 'age': 178}, 'Lounge-radiators': {'count': 26, 'last': 1794425818.4919605, 'age': 53773}, 'Bedroom-2-radiator': {'count': 121, 'last': 1794437807.1395724, 'age': 41785}, 'Demand': {'count': 1, 'last': 1794173214.3745084, 'age': 306377}, 'Kitchen-radiator': {'count': 5, 'last': 1794319923.2342317, 'age': 159669}, 'Sunroom-radiator': {'count': 9, 'last': 1794386796.924029, 'age': 92795}, 'Bedroom-1-radiator': {'count': 10, 'last': 1794411250.7261734, 'age': 68341}}

== TIMERS ==
------------
[ OK ] rbr-updater.timer: hourly code updates — without it the box stays on its install release
[ OK ] rbr-watchdog.timer: 15-minute service and heating watchdog
[ OK ] rbr-backup.timer: monthly controller + Zigbee backup
[ OK ] rbr-journal-export.timer: daily journal export and email
[ OK ] last updater run: success

== LINUX HEALTH ==
------------------
[ OK ] systemd reports the system running normally
[ OK ] no failed systemd units
[ OK ] inode usage: 1%
[ OK ] swap: 0% used (0 MB of 1906 MB)
[ OK ] no zombie processes
[ OK ] one controller process running
[ OK ] no cron entry launching the controller
[ OK ] 3 established MQTT connection(s): [::1]:1883
[ OK ] enp2s0: no receive/transmit errors (drops: 1110/4)
[note] system journal: no journal entries for the system journal

== CONTROLLER ==
----------------
[ OK ] the controller reached its main loop after connecting
[note] a new release was applied during the last session: 2611071517 -> 2611121029
[note] last controller log line: 2026-11-12T10:32:33+00:00 QED6 allspeak[2405504]: 10:32:33.866581:Controller:3867->Event journal enabled, root /data/rbr-heating/events
[note] running: /usr/bin/python3 /home/qed6/.local/bin/allspeak controller.allspeak --no-dashboard
[note] process started 40 s ago
[note] the controller log is quiet by design: at normal running the only start-up lines are 'Run Controller', 'MAC address is ...', 'Client ... connected' and 'Subscribed to topic: ...'. A healthy session also has 'Load the system map' immediately after the subscription.
[note] last 20 controller log lines:
[note]   2026-11-12T10:32:32+00:00 QED6 systemd[1]: controller.service: Scheduled restart job, restart counter is at 1.
[note]   2026-11-12T10:32:32+00:00 QED6 systemd[1]: Started controller.service - RBR Controller.
[note]   2026-11-12T10:32:33+00:00 QED6 allspeak[2405504]: AllSpeak version 2610142212
[note]   2026-11-12T10:32:33+00:00 QED6 allspeak[2405504]: Loading MQTT module
[note]   2026-11-12T10:32:33+00:00 QED6 allspeak[2405504]: Loading email module
[note]   2026-11-12T10:32:33+00:00 QED6 allspeak[2405504]: Compiled Controller: 4115 lines (13688 tokens) in 450 ms
[note]   2026-11-12T10:32:33+00:00 QED6 allspeak[2405504]: Run Controller
[note]   2026-11-12T10:32:33+00:00 QED6 allspeak[2405504]: AllSpeak version 2610142212
[note]   2026-11-12T10:32:33+00:00 QED6 allspeak[2405504]: Compiled DeviceControl: 183 lines (480 tokens) in 16 ms
[note]   2026-11-12T10:32:33+00:00 QED6 allspeak[2405504]: Run DeviceControl
[note]   2026-11-12T10:32:33+00:00 QED6 allspeak[2405504]: 10:32:33.729446:DeviceControl:32->Set up the device controller
[note]   2026-11-12T10:32:33+00:00 QED6 allspeak[2405504]: 10:32:33.729634:DeviceControl:35->Device controller is ready
[note]   2026-11-12T10:32:33+00:00 QED6 allspeak[2405504]: 10:32:33.731972:Controller:399->Controller version 2611121029
[note]   2026-11-12T10:32:33+00:00 QED6 allspeak[2405504]: 10:32:33.735564:Controller:437->MAC address overridden to 00:e0:27:5b:31:40
[note]   2026-11-12T10:32:33+00:00 QED6 allspeak[2405504]: Client 94213dc7-ac81-4586-abe3-ae6e57d9c0ca connected
[note]   2026-11-12T10:32:33+00:00 QED6 allspeak[2405504]: Subscribed to topic: 00:e0:27:5b:31:40 with QoS 1
[note]   2026-11-12T10:32:33+00:00 QED6 allspeak[2405504]: 10:32:33.749404:Controller:935->Load the system map
[note]   2026-11-12T10:32:33+00:00 QED6 allspeak[2405504]: 10:32:33.758120:Controller:517->Volatile data in /run/rbr/
[note]   2026-11-12T10:32:33+00:00 QED6 allspeak[2405504]: 10:32:33.762006:Controller:544->Heat logging enabled, root /data/rbr-heating
[note]   2026-11-12T10:32:33+00:00 QED6 allspeak[2405504]: 10:32:33.866581:Controller:3867->Event journal enabled, root /data/rbr-heating/events

== STATE FILES ==
-----------------
[ OK ] map.json: 14 KB, 8 room(s), 3 profile(s), modified 2 h 32 min ago
[ OK ] thermometers.json: modified 55 s ago (temperature readings from the Zigbee bridge)
[FAIL] rbr-dashboard.json: modified 9 d 17 h ago (terminal/companion dashboard snapshot)
[note] event journal enabled but no bundle written yet
[ OK ] disk: 48.2 GB free of 51.9 GB

== ZIGBEE ==
------------
[ OK ] serial device(s): /dev/ttyUSB0
[ OK ] /dev/zigbee-dongle symlink present
[ OK ] Zigbee2MQTT config: /opt/zigbee2mqtt/data/configuration.yaml
[ OK ] coordinator port: /dev/zigbee-dongle
[ OK ] Zigbee2MQTT MQTT server: mqtt://localhost:1883
[ OK ] CP210x coordinator on USB (10c4:ea60)

== MQTT CONFIG ==
-----------------
[ OK ] local bridge config: /etc/mosquitto/conf.d/rbr-local.conf
[note]   address rbrheating.duckdns.org:8883
[note]   remote_username rbr
[note]   topic # both 1
[note]   bridge_protocol_version mqttv311
[note] remote password is present (not printed)
[ OK ] port 1883 listening
[ OK ] port 8080 listening
[ OK ] port 8889 listening

== BROKER ==
------------
[ OK ] controller broker: localhost:1883
[note] UI broker: localhost:1883 over WebSocket (from credentials.port)
[ OK ] DNS: localhost -> 127.0.0.1, ::1
[ OK ] localhost:1883 reachable (::1)
[ OK ] UI WebSocket port 1883 reachable (::1)

== ROUND TRIP ==
----------------
[note] sending a 'first' map request as sender 00:e0:27:5b:31:40/doctor-<pid> and waiting up to 12 s
[WARN] the round-trip probe could not complete: too many values to unpack (expected 2)

==================================================================
1 failure(s), 3 warning(s)

What this points at
  * The rbr-dashboard.json file has not changed for 9 d 17 h. The controller writes it once a minute when the bridge has data, so check the bridge and the Zigbee mesh, not the UI.

Next steps
  * Re-run with sudo for the full journal: sudo ./rbr-doctor.py > rbr-doctor.txt
  * Failed units: sudo systemctl --failed; errors this boot: sudo journalctl -p 3 -b
  * Watch the controller while it starts: sudo journalctl -u controller -f
  * Services: sudo systemctl status controller mosquitto zigbee2mqtt rbr-zigbee-bridge
  * Send rbr-doctor.txt with any report — it contains no passwords.

**Assistant**

`rbr-dashboard.json` is a red herring — nothing is broken. The service starts the controller with `--no-dashboard` (your report's `running:` line shows it), and the controller only writes that file when the flag is absent. It is the terminal dashboard's snapshot, read only by `rbr-dashboard.py`; neither the UI nor the controller needs it. The 9-day-old file in `/run/rbr` is a leftover from a run with the dashboard enabled (or from before `--no-dashboard` was added to the unit). Delete it or leave it — `/run` is a tmpfs, so it disappears at reboot. The doctor's `[FAIL]` was a false positive; I've fixed it to treat a stale or absent dashboard file as expected when the flag is present. You don't need to touch the file.

The more important thing in the report is that the ROUND TRIP check didn't run: `too many values to unpack (expected 2)` was a bug in the doctor, not your system. `mqtt_probe()` returned a bare dict on success but `(None, reason)` on a skip, and the caller unpacked two values. It now always returns a pair, and a test pins that. Re-run with the updated file:

`sudo python3 rbr-doctor.py > rbr-doctor.txt`

It should now say `the controller replied in … (N bytes, full map, …)`. Everything else in the report already says the controller is healthy: it logged `Load the system map`, there is one controller process, three established MQTT connections, all four timers are active, the release is current, and the bridge and Zigbee are up.

Two smaller corrections in the same update:

- `allspeak not found on PATH…` was a lookup miss: run directly as root, `HOME` is `/root` and `SUDO_USER` is unset, so it missed `/home/qed6/.local/bin/allspeak`. It now checks the install directory owner's home too, and will report the running runtime (`2610142212`).
- `system journal: no journal entries` now reads `no error-priority system log lines this boot`, which is what it meant.

One real item worth looking at, unrelated to the JSON:

- The bridge reports recent unacknowledged relay commands: **Hall-radiator** 3828 (last 178 s ago) and **Kitchen-plinth** 1149 (last 50 s ago); the other counts are older (Office-heater last 7 h ago, etc.). Counts are cumulative since the bridge started, so the recent `last` is the part that matters. If those rooms are heating normally, watch the counts; if they are not, power-cycle the relays — a wedged mains relay stays on the network and looks healthy while ignoring commands. The doctor now ranks recent failures first and only shows the power-cycle hint when there is one.
- The AllSpeak runtime is `2610142212` (14 Oct) while the controller release is current. The controller is working on it, so I would leave it alone unless you are chasing something else.

So: no action on `rbr-dashboard.json`; replace the doctor and re-run it once to get the round-trip result; then look at Hall-radiator and Kitchen-plinth if those rooms are misbehaving.

## 10:48

I re-ran it and all looks OK. At the bottom of the report is
Next steps
  * Re-run with sudo for the full journal: sudo ./rbr-doctor.py > rbr-doctor.txt

Isn't this what I just did?

**Assistant**

Yes — that is exactly what you did, and the line was wrong. The footer was boilerplate: it printed the same next steps whether the report had been run as root or not, and whether the journal was readable or not. It is now conditional.

A root run with no failures now ends like this:

    Next steps
      * No failures. Review the [WARN] lines above; they are advice, or a degradation that has not stopped the system.
      * Send rbr-doctor.txt with any report — it contains no passwords.

There is no sudo line, and no service or journal commands unless something actually needs them. If you run it as a non-root user and the journal really is unreadable, the "Re-run as root…" line still appears. The suggested command is also `sudo python3 rbr-doctor.py > rbr-doctor.txt`, not `./rbr-doctor.py`, so it does not depend on the executable bit.

The header now says `run as root` instead of `run as root (root)`. Replace `rbr-doctor.py` with the updated copy and re-run; the footer will match what you have already done. Your report is otherwise fine — the only open items are the bridge's recent relay failures (Hall-radiator, Kitchen-plinth) and, if you care, the old AllSpeak runtime.

## 20:17

The system is currently behaving but the doctor reports the following. Can you comment.

RBR doctor — hvac01 — 2026-11-12 19:44:16 GMT
install: /home/rbr/rbr (release 2611121049)
run as root


== SYSTEM ==
------------
[ OK ] Debian GNU/Linux 13 (trixie) (kernel 6.12.113+deb13-amd64)
[note] hostname hvac01
[ OK ] up 10 d 23 h
[ OK ] clock: Thu 12 Nov 19:44:02 GMT 2026 Europe/London, NTP synchronised
[ OK ] memory available: 2507 MB
[note] load average: 0.17 0.20 0.18
[ OK ] no storage/USB errors in the recent kernel log

== IDENTITY ==
--------------
[ OK ] install directory: /home/rbr/rbr
[ OK ] default route on enp1s0 (40:b0:34:33:22:11)
[ OK ] .mac_override: 40:b0:34:33:22:11
[ OK ] credentials present (/home/rbr/rbr/credentials)
[ OK ] volatile data in /run/rbr

== VERSIONS ==
--------------
[ OK ] installed release (.version): 2611121049
[WARN] installed AllSpeak runtime: allspeak not found on PATH or in the usual ~/.local/bin
[ OK ] latest published release: 2611121049

== SERVICES ==
--------------
[ OK ] controller: active — running, up 14 s
[WARN] controller has restarted 80 time(s) since the unit was loaded
[note] controller main PID 1795625, memory 41 MB
[note] controller unit: /etc/systemd/system/controller.service
[note] run as rbr in /home/rbr/rbr
[ OK ] mosquitto: active — running, up 17 h 28 min
[note] mosquitto main PID 1372846, memory 6 MB
[ OK ] zigbee2mqtt: active — running, up 17 h 28 min
[note] zigbee2mqtt main PID 1372851, memory 107 MB
[ OK ] rbr-zigbee-bridge: active — running, up 17 h 28 min
[note] rbr-zigbee-bridge main PID 1372861, memory 16 MB
[ OK ] mosquitto listens on 127.0.0.1:1883
[ OK ] zigbee2mqtt frontend answers on 127.0.0.1:8080 (HTTP 200)
[ OK ] rbr-zigbee-bridge /health answers, 10 known device(s)

== TIMERS ==
------------
[ OK ] rbr-updater.timer: hourly code updates — without it the box stays on its install release
[ OK ] rbr-watchdog.timer: 15-minute service and heating watchdog
[ OK ] rbr-backup.timer: monthly controller + Zigbee backup
[ OK ] rbr-journal-export.timer: daily journal export and email
[ OK ] last updater run: success

== LINUX HEALTH ==
------------------
[ OK ] systemd reports the system running normally
[ OK ] no failed systemd units
[ OK ] inode usage: 25%
[ OK ] swap: 0% used (0 MB of 707 MB)
[ OK ] no zombie processes
[ OK ] one controller process running
[ OK ] no cron entry launching the controller
[ OK ] 3 established MQTT connection(s): [::1]:1883
[ OK ] enp1s0: no receive/transmit errors (drops: 0/0)
[ OK ] no error-priority system log lines this boot

== CONTROLLER ==
----------------
[ OK ] the controller reached its main loop after connecting
[note] last controller log line: 2026-11-12T19:43:57+00:00 hvac01 allspeak[1795625]: 19:43:57.547080:Controller:2193->No request relay
[note] running: /usr/bin/python3 /home/rbr/.local/bin/allspeak controller.allspeak --no-dashboard
[note] process started 15 s ago
[note] the controller log is quiet by design: at normal running the only start-up lines are 'Run Controller', 'MAC address is ...', 'Client ... connected' and 'Subscribed to topic: ...'. A healthy session also has 'Load the system map' immediately after the subscription.
[note] last 20 controller log lines:
[note]   2026-11-12T19:43:48+00:00 hvac01 systemd[1]: Started controller.service - RBR Controller.
[note]   2026-11-12T19:43:49+00:00 hvac01 allspeak[1795625]: AllSpeak version 2610142212
[note]   2026-11-12T19:43:49+00:00 hvac01 allspeak[1795625]: Loading MQTT module
[note]   2026-11-12T19:43:49+00:00 hvac01 allspeak[1795625]: Loading email module
[note]   2026-11-12T19:43:50+00:00 hvac01 allspeak[1795625]: Compiled Controller: 4115 lines (13688 tokens) in 632 ms
[note]   2026-11-12T19:43:50+00:00 hvac01 allspeak[1795625]: Run Controller
[note]   2026-11-12T19:43:50+00:00 hvac01 allspeak[1795625]: AllSpeak version 2610142212
[note]   2026-11-12T19:43:50+00:00 hvac01 allspeak[1795625]: Compiled DeviceControl: 183 lines (480 tokens) in 23 ms
[note]   2026-11-12T19:43:50+00:00 hvac01 allspeak[1795625]: Run DeviceControl
[note]   2026-11-12T19:43:50+00:00 hvac01 allspeak[1795625]: 19:43:50.296219:DeviceControl:32->Set up the device controller
[note]   2026-11-12T19:43:50+00:00 hvac01 allspeak[1795625]: 19:43:50.296489:DeviceControl:35->Device controller is ready
[note]   2026-11-12T19:43:50+00:00 hvac01 allspeak[1795625]: 19:43:50.299990:Controller:399->Controller version 2611121049
[note]   2026-11-12T19:43:50+00:00 hvac01 allspeak[1795625]: 19:43:50.304982:Controller:437->MAC address overridden to 40:b0:34:33:22:11
[note]   2026-11-12T19:43:50+00:00 hvac01 allspeak[1795625]: Client d5ecf07c-1b5b-4495-bfed-6160e0ba7044 connected
[note]   2026-11-12T19:43:50+00:00 hvac01 allspeak[1795625]: Subscribed to topic: 40:b0:34:33:22:11 with QoS 1
[note]   2026-11-12T19:43:50+00:00 hvac01 allspeak[1795625]: 19:43:50.319902:Controller:935->Load the system map
[note]   2026-11-12T19:43:50+00:00 hvac01 allspeak[1795625]: 19:43:50.326993:Controller:517->Volatile data in /run/rbr/
[note]   2026-11-12T19:43:50+00:00 hvac01 allspeak[1795625]: 19:43:50.331380:Controller:544->Heat logging enabled, root /data/rbr-heating
[note]   2026-11-12T19:43:50+00:00 hvac01 allspeak[1795625]: 19:43:50.440787:Controller:3867->Event journal enabled, root /data/rbr-heating/events

== STATE FILES ==
-----------------
[ OK ] map.json: 6 KB, 4 room(s), 2 profile(s), modified 26 s ago
[ OK ] thermometers.json: modified 26 s ago (temperature readings from the Zigbee bridge)
[note] rbr-dashboard.json: not written (controller runs with --no-dashboard; safe to delete)
[note] event journal enabled but no bundle written yet
[FAIL] disk: 0.7 GB free of 5.6 GB

== ZIGBEE ==
------------
[ OK ] serial device(s): /dev/ttyUSB0
[ OK ] /dev/zigbee-dongle symlink present
[ OK ] Zigbee2MQTT config: /opt/zigbee2mqtt/data/configuration.yaml
[ OK ] coordinator port: /dev/zigbee-dongle
[ OK ] Zigbee2MQTT MQTT server: mqtt://localhost:1883
[ OK ] CP210x coordinator on USB (10c4:ea60)

== MQTT CONFIG ==
-----------------
[ OK ] local bridge config: /etc/mosquitto/conf.d/rbr-local.conf
[note]   address rbrheating.duckdns.org:8883
[note]   remote_username rbr
[note]   topic # both 1
[note]   bridge_protocol_version mqttv311
[note] remote password is present (not printed)
[ OK ] port 1883 listening
[ OK ] port 8080 listening
[ OK ] port 8889 listening

== BROKER ==
------------
[ OK ] controller broker: localhost:1883
[note] UI broker: localhost:1883 over WebSocket (from credentials.port)
[ OK ] DNS: localhost -> 127.0.0.1, ::1
[ OK ] localhost:1883 reachable (::1)
[ OK ] UI WebSocket port 1883 reachable (::1)

== ROUND TRIP ==
----------------
[note] sending a 'first' map request as sender 40:b0:34:33:22:11/doctor-<pid> and waiting up to 12 s
[ OK ] probe connected to the broker (12.1 s)
[FAIL] no reply from the controller within 12 s — the broker path works, but the controller does not answer its own topic

==================================================================
2 failure(s), 2 warning(s)

What this points at
  * controller has restarted 80 times — look for a crash loop in its journal rather than restarting it again.
  * Less than 1 GB free. The controller and journal exporters cannot write; clear old journals/backups first.
  * The broker is fine and the controller is not answering. This is the state that shows up as 'Reconnecting...' in the UI. Restart the controller and re-run the probe; if the reply still does not come, read the controller journal for 'Subscribed to topic' with no 'Load the system map' after it.

Next steps
  * Work through the [FAIL] items above, starting with the first in each section.
  * Send rbr-doctor.txt with any report — it contains no passwords.

**Assistant**

Two of these are real, one is a false negative from the probe, and one was a false warning. The system behaving is consistent with that.

**Real — disk.** 0.7 GB free of 5.6 GB is the thing to fix. The controller's own writes are still working (`map.json` 26 s old), but the updater, journal exporter and backups need room; below a few hundred MB the controller's writes start to fail. Check what is using it: `df -h /home/rbr/rbr /data`; `sudo du -x -h -d1 /home/rbr/rbr /var/log /var/cache/apt 2>/dev/null | sort -h | tail`; `sudo du -sh /data/rbr-heating/* 2>/dev/null`; `sudo journalctl --disk-usage`. The usual culprits are `backup/` (12 monthly ZIPs), `<journal-root>/exports` (14 days), `/var/log` and the apt cache. Clear old exports/backups, run `sudo apt-get clean`, and `sudo journalctl --vacuum-size=100M`. The updated doctor prints this breakdown automatically when free space is below 2 GB. If `/data` is a separate filesystem, the 5.6 GB figure is the install filesystem, not the journal disk.

**Real, but not explained by this report — 80 restarts.** The controller was up only 14 s when the checks ran, so it had just restarted. 80 restarts since the unit was loaded is not normal, but the report does not show why: `systemctl status` exposes only the last few lines, and the journal excerpt starts at the current session. Get the cadence and the exit status: `sudo journalctl -u controller --since "-24 hours" --no-pager | grep -E "Started controller|Main process exited|Failed with result|Scheduled restart|Stopped controller"`. If the starts are about hourly, look at `journalctl -u rbr-updater` (the updater only restarts on a newer release, so that would mean real updates). If they are every few minutes, it is a crash loop; `status=0/SUCCESS` is a clean exit (often a release), `status=1/FAILURE` or a signal is a crash. If they cluster every 15 minutes, check `journalctl -t rbr-watchdog`. The updated doctor now counts starts in the captured journal and prints the last start lines and exit reasons, so one re-run should say which. Do not just restart it again; that loses the evidence.

**Probably a false negative — no reply to the round trip.** The UI working is stronger evidence than the probe. The controller had been up 14 s (just restarted), and it drains its MQTT queue between room cycles; a four-room cycle can easily outlast 12 s. The UI's own first-map watchdog allows 30 s. The probe also uses the controller's own credentials, which can publish to the system topic but may not be allowed to subscribe to the throwaway sender topic. The updated probe waits 30 s by default, reports connect and reply times separately, records the broker's SUBACK, and says explicitly if the subscription was refused. Re-run it; if it still reports no reply **and** the subscription was granted, then look at the controller, but I expect a reply.

**Was a false warning — AllSpeak runtime not found.** The controller runs `/usr/bin/python3 /home/rbr/.local/bin/allspeak`, so the file is readable but not necessarily executable; the lookup required the execute bit. It now prefers the install directory owner's home, accepts a readable file and runs it through the interpreter. The re-run will report `2610142212`. That runtime is old, but the controller is working on it; leave it unless you are chasing a bug.

**No action — `rbr-dashboard.json`.** `--no-dashboard` is in the running command, so it is never written. The "not written" note is correct.

**Order of work:** free disk space; replace `rbr-doctor.py` and re-run; read the new restart/exit evidence and the probe's subscription result. If the restarts are clean and hourly, they are update-related; if they are failures, that is the real fault to chase. The disk is the one that will cause an outage if left.
