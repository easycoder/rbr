# 2026-11-17

## 11:49

A user installation is misbehaving. The PWA shows a blank screen until the controller is restarted. I have a report this happened at around 21:00 yesterday then again today at 10:55. I asked for the current journal and doctor's reports; everything I've been sent is in various/Newton12. Can you examine and draw any conclusions?

**Assistant**

I read both doctor reports and both journal bundles. There are two independent faults here, and the reports are pointing at one while the blank screen is the other.

## 1. The controller has been crash-looping every ~79 seconds — for weeks

The event journal is unambiguous. On 16 Nov there are **1,014 `session.start` events**; on 15 Nov, **1,098**. That is 45–46 per hour, every hour, with a median gap of **79.0 s** (p10 78.5, p90 79.3), across all four releases the updater applied on the 15th (2611141554 from midnight → 2611152046 from 21:03). Neither bundle contains a single `session.stop`, so none of those are clean exits.

Each session is killed by this, 73–74 s after it starts:

`Runtime Error in Controller at line 2097 (multiply TrvSeen by 1000): Arithmetic error in multiply: invalid literal for int() with base 10: '1794857533.0439382'`

`TrvSeen` is the TRV's `last_seen`. `zigbee-bridge.py` writes it as a float epoch (`state["last_seen"] = time.time()`), AllSpeak has no float type — a decimal is a string — and `multiply` converts with `int()`. The value is exact proof: 1794857533.0439382 is 19:32:13 on the 16th. Unhandled, it ends the process.

Why 74 s and not immediately: `ZigbeeTrvs` is only loaded in the once-a-minute save tick in `HandleMessages` (`add 60000 to LastMapSave`), so for the first minute there is no `running_state` and the block is skipped. The tick at ~60 s arms it; the next room cycle dies. Hence ~74 s of life plus systemd's 5 s restart delay = the 79 s cadence.

Do not read that cadence as design. AGENTS.md still says the controller "self-times 6 cycles of 10 seconds each, then exits"; this release has no such timer — it exits only on a bad MAC, missing credentials, an applied update (which would log `Update applied` and write `session.stop`), or a runtime error. This is a crash loop, and the block that fails was added on 26 Oct (`4cf9234`).

The code fix is one line: `put TrvSeen scale 1000 into TrvSeen` instead of `multiply TrvSeen by 1000` — `scale` is the runtime's decimal-safe conversion and the controller already uses it (`put Temp scale 100 into Temp`). It needs a regression test with a fractional `last_seen`; the existing TRV tests do not exercise this path, which is why nothing caught it.

## 2. The blank screen is a second fault: a session that connected but never started

Both doctors show the signature: `Subscribed to topic: 40:b0:34:33:22:11` with no `Load the system map` after it. That is the controller's own marker for "connected, not running".

- **16 Nov:** the last session started 19:40:50, subscribed 19:40:52, then nothing. The journal has nine events between 19:39:32 and 21:28:01 (seven room states from the session before the crash, plus the two starts) — 107 minutes of no work. The 21:21 doctor caught it at "up 100 min". The 21:28:01 start is the restart that fixed it; the app's `ui.first` arrives 27 s later.
- **17 Nov:** started 09:47:08, subscribed 09:47:10, still wedged at 11:00 — that is the 10:55 blank screen. The 09:47:02 crash line belongs to the session before.

The process is alive, and so is its MQTT client — the 10:57 probe even produced `WARNING: ignoring unframed payload` from the MQTT thread. But `Start` never ran, so `MainLoop` never ran: no map load, no room cycles, no `thermometers.json` (the doctor's "modified 70 min ago" is the last write from the pre-crash session), and nothing for systemd to restart. `map.json`'s mtime says the same.

The cause is a race in the runtime's connect event. `on mqtt connect go to Start` is registered *after* the `mqtt` block starts the client. In `as_mqtt.py`, `on_connect` queues the connect intent only `if is_first_connect and self.onConnectPC is not None`; `onConnectPC` is set when the `on mqtt connect` line executes. paho's `connect()` returns before CONNACK, so the connect callback runs on the paho thread and races the main flow. Lose that race and the event is gone for good: `is_first_connect` never comes back, and a reconnect will not revive it either. The observed state — subscribed, idle, permanent — is exactly what that failure looks like. A manual restart works because a fresh process re-runs the registration and normally wins.

The frequency fits: about 2,100 starts in two days, two wedges. The crash loop is what turns a rare race into a roughly daily event.

Fix: in the runtime, when `onConnectPC` is set and the client is already connected, queue the intent immediately. That is an AllSpeak change (and wants a REQUESTS.md row). Until the box's runtime is updated, the watchdog is the safety net.

## 3. What the reports miss

- `rbr-watchdog.sh` has `probe_controller() { return 0; }` — the controller is the one service with no health check, so a wedged-but-alive controller is never restarted. That is why the 16th's wedge lasted 107 minutes and today's 73+.
- The doctor's `ROUND TRIP [FAIL] — no reply from the controller` cannot be trusted: `mqtt_probe` publishes raw JSON with no `!last!1 ` frame, so the runtime drops it before the script sees it. The 17th's log even shows the doctor's own probe being ignored. It will fail on a healthy controller too. The wedge is real, but it is proved by the missing `Load the system map`, not by the probe.
- "Restarted 98 times / 9 starts in the last 300 lines" is not a new loop; it is the chronic crash loop.
- `allspeak --version` failing is a root-environment artefact: the doctor runs as root, whose `python3` cannot see `/home/rbr/.local/lib/...`; the service runs as `rbr`. Cosmetic, but it makes that one version check useless.
- Disk is 87% full (0.7 GB free): journal 68–72 MB, system log 41 MB, apt cache 140 MB. Not the cause, but the updater, exports and backups are what fail next.

There is no bundle for today yet — the export runs at 03:35 — so the 17th's evidence is the two reports. If you want its journal now, it is `/data/rbr-heating/events/2026/11/2026-11-17.jsonl` on the box.

## Order I would fix it in

1. The `scale` one-liner plus a unit test. This stops ~45 deaths an hour and is the fault that has been silently degrading the heating for weeks.
2. The watchdog probe: restart the controller when its current session has `Subscribed to topic` with no `Load the system map` after it (the doctor already implements that check), or when `thermometers.json` in `/run/rbr` is stale. This is what would have saved both blank screens, and it covers the runtime bug until a runtime update lands.
3. The runtime connect fix upstream, plus the REQUESTS.md row.
4. The doctor's probe framing, so round-trip failures mean something again.
5. Disk housekeeping (`journalctl --vacuum-size=200M`, clear the apt cache).

One code-review note while I was in there: the `ProcessTrvState` doc block has no tail (`@hash`, `@verified`, `!!!`) and its prose sits after the previous block's code — `asdoc-check` reports `doc-after-code` at 2084–2086. Unlike the rest of the file, that routine never went through the managed review, which is consistent with the bug surviving since October.

I can do 1 and 4 here now (small, local, testable); say the word and I will.

## 12:00

Do what you can to fix the problems. I'll deploy then rewind my version to ensure the fix is stable before releasing.

**Assistant**

Fixed the three things I can fix in this repository: the crash loop, the watchdog's blind spot, and the doctor's probe. The runtime's connect-event race is still open (it is an AllSpeak change), and it is now recorded in `REQUESTS.md` with the watchdog as the workaround.

**1. The crash loop — `controller.allspeak`.** `ProcessTrvState` now converts the TRV's `last_seen` with `put TrvSeen scale 1000 into TrvSeen` instead of `multiply TrvSeen by 1000`. `scale` is the decimal-safe conversion `ConvertTempToInt` already uses; the bridge's float epoch no longer calls `int()`. Four comment lines mark why it must not go back. New `tests/unit/trv_state_test.py` extracts the routine from the controller and drives it with a fractional `last_seen`, an integer one, a stale one (46 minutes), a missing one and a non-heat/idle value. Swapped back to `multiply` it reproduces the live error verbatim; with the fix all five cases pass.

**2. The blank screen — `rbr-watchdog.sh`.** The controller was the one service with `probe_controller() { return 0; }`. It now reads the unit's recent log for `Subscribed to topic` with no `Load the system map` after it, and restarts when that has stood for more than two minutes. The grace covers a normal start and the 5-second restart gap. New `tests/unit/watchdog_probe_test.py` runs the real script with fake `systemctl`/`journalctl`/`logger`: a healthy start, a session still starting and an empty journal do not restart; a subscribed-never-started session does. It fails with the old `return 0`.

**3. The doctor — `rbr-doctor.py`.** The probe now sends `!last!1 ` plus the JSON body, and reassembles a chunked reply (a full map is split at 1024 bytes) before reporting. `tests/unit/doctor_test.py` pins the frame and a three-chunk reply, and that an incomplete one is not reported as a reply.

**Also:** `tests/unit/run-unit-tests.sh` runs the two new modules; `AGENTS.md` no longer claims the controller self-times and exits (it does not — that false line is what makes a crash loop look like design); `DIFF.md` is rewritten; `REQUESTS.md` has the runtime row.

`tests/unit/run-unit-tests.sh` passes: controller compiles, AllSpeak suite 83/83, Python 202 tests (including the 10 new ones), `0 error(s)` from `asdoc-check` with the affected block's hash refreshed. Nothing is committed and `version` is untouched — deploy from the working tree, and restart the controller yourself when deploying without `--release`, because the version stamp unchanged means the running process will not exit to load the new code.

## 12:08

Why would these problems show on one system and not another?

**Assistant**

Because the two faults are conditional on different things: the crash loop is gated by the room's actuator, and the wedge is gated by how often the controller starts. This box is the one with both.

**The crash loop can only run on a TRV-wired room.** `ProcessRoom` branches on `if Room has entry 'trv'` and calls `ProcessTrv`, which is where `ProcessTrvState` lives; a relay room goes down the relay path and never touches the `last_seen` conversion. The shipped example map (`map.json` in this repo: eight rooms, relays, no `trv`) and the standard install are relay + thermometer, so they cannot show this at all. Newton12's map is four rooms, all `trv`, no relay — the battery-TRV trial.

Within a TRV system it needs one more thing: a valve whose zigbee2mqtt converter reports `running_state` as `heat` or `idle`. The bridge writes the key for every thermostat-like device, but the gate is `if TrvRunningState is not empty`, so a valve that never reports it, or reports null, skips the block and never reaches the conversion. And the gate only exists from the 26 Oct release (`4cf9234`); TRV driving itself arrived on 19 Oct, so a box that has not taken a release since then has no failing code either.

The journal corroborates it: every `room.state` on both the 15th and 16th has `trvrunning: null` — 6,322 events on the 16th, 7,059 on the 15th. The routine dies at the conversion before it records the state, so the valve tag on the page has never had a value on this box; it falls back to the demand tag. That is what a TRV system that hits this looks like, and a relay system never gets near it.

**The wedge is a race every system has; it needs attempts.** The lost `on mqtt connect` event is in the runtime (`as_mqtt.py`, unchanged since 5 Oct), and every box runs that runtime and a local mosquitto, so no system is immune and the window is the same size everywhere. What differs is how many times a controller starts: a normal box starts at boot and when a release changes `.version` — a handful of times a day or week. At the observed rate (two wedges in the 2,112 starts of the 15th and 16th, so roughly 1 in 1,000), that is one wedge every few years. This box starts every 79 seconds because of the crash loop: about 1,000 starts a day, so about one wedge a day. The crash loop is what turns a rare race into the reported symptom.

The other difference is reporting, not mechanism: a wedged system nobody opens the app on stays wedged quietly, and its journal shows the same "Subscribed with no Load the system map" gap. Any box could do this; it would just take far longer to catch.

**So:** any TRV-wired system that has taken the 26 Oct or later release and has a valve reporting `running_state` is probably crash-looping now, reported or not. `journalctl -u controller | grep -c 'Arithmetic error in multiply'` and counting `Load the system map` per hour will say. A relay system can still wedge, rarely; the watchdog change covers that everywhere. This box's 87% disk is its own problem and not shared.

Caveat: I have this system's journal and maps only; the fleet prediction comes from the code paths and the shipped example, not from other boxes' data.

## 12:19

It's probable he hasn't constrained the systemctl journal size. What's the command to do that?

**Assistant**

The one-off cleanup is `sudo journalctl --vacuum-size=100M` (or `--vacuum-time=2weeks`); `journalctl --disk-usage` shows what it is now.

That does not stop it growing again. The durable cap is a journald drop-in:

`sudo mkdir -p /etc/systemd/journald.conf.d`, then a file `/etc/systemd/journald.conf.d/rbr.conf` containing `[Journal]` and `SystemMaxUse=100M`, then `sudo systemctl restart systemd-journald`. Add `SystemMaxFileSize=50M` and `MaxRetentionSec=1month` if you want per-file and age caps too. Verify with `systemd-analyze cat-config systemd/journald.conf | grep -E 'Storage|MaxUse'` and `journalctl --disk-usage`.

Two RBR-specific points. `rbr-setup.sh` STEP 5d already writes that drop-in, but with `Storage=volatile` and `RuntimeMaxUse=64M` (journal in `/run`, gone at reboot), so a box that has been through the installer should not be growing a disk journal at all — this one clearly is, which means it predates that step or the file was removed (the docs tell people to remove it to keep logs). And on this box the journal is only ~87M of 4.3G used, so capping it stops the creep but will not recover the 661M free; the space is elsewhere.

If a volatile journal is the wrong trade while an incident is open, use `SystemMaxUse` on disk (the default `Storage=auto` keeps it persistent) rather than copying the installer's file; `RuntimeMaxUse` is ignored unless storage is volatile.
