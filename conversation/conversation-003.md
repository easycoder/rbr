# 2026-08-07

## 10:46

One of my radiator relays has been powered down for a couple of days, but the UI is not reporting it. Does the controller detect when a relay does not respond to requests for some time, and if so can a message be displayed in the UI under the room name?

**Assistant**

Yes on both counts, but there was a gap that explained what you saw.

Detection: the controller already has the machinery — every ~5s it polls each room's relay; empty replies accumulate into relayfails, and RoomStatus turns >5 failures into warn and >20 into fail, building a statusMessage ("Relay: N failures") and forcing the relay off. The gap was in the Zigbee path: zigbee-bridge.py always answered with HTTP 200 and the device's cached last-known state (defaulting to "unknown"), so a powered-down relay kept serving a stale "off" and the controller never saw a failure. RBR-Now legacy relays were detected; Zigbee ones weren't.

UI: statusMessage/status are already pushed to the UI in every map update, but were only used for the status dot and the per-room info popup — not under the room name.

Implemented (per your choice to do both):
- zigbee-bridge.py: tracks zigbee2mqtt per-device availability ("online"/"offline") and returns a body with no `state` field when a device is offline or hasn't been seen for >30 min (fallback when availability is unknown). deviceControl.as treats a missing state as a failure, so the controller's existing relayfails/warn/fail path now fires. Availability is trusted over staleness so a quiet-but-online device is never falsely flagged.
- UI: room card (resources/webson/room.json) now has a status line under the room name; rbr.as shows the controller's statusMessage there (hidden when the room is healthy).

Checks: bridge logic unit-tested, rbr.as parses clean under the AllSpeak analyser, webson references/ids validated, post-fix review passed. Full Playwright suite not runnable here (needs mosquitto + sudo, unavailable in this environment).

Deploy note: restart the rbr-zigbee-bridge service and confirm `availability: true` in the zigbee2mqtt configuration (/opt/zigbee2mqtt/data/configuration.yaml — the setup script writes it) so offline detection works. Then a powered-down relay should show the warning under its room name within a couple of minutes (warn after ~6 failed polls, fail after ~21).
