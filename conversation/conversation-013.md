# 2026-10-19

## 13:56 — Setup Russell system

**User**

I want to set up a new RBR system on a Linux computer at `10.168.20.15`. Please guide me through the process.

**Assistant**

Walked through the install in the order that avoids the known traps: preflight first, then the controller pack and AllSpeak, then `rbr-setup.sh`, provisioning and Zigbee pairing. The box was a clean install — only SSH was open — and the first blocker was access: the machine rejected the available key, so the user created an `rbr` account and installed AllSpeak themselves. The install then proceeded on `hvac01`, with the controller running as a service and the Zigbee dongle detected.

The broker was the next real problem. The UI could reach the site but not the controller's MQTT namespace, and the broker accepted only the `rbr` and `root` keys. The user supplied the broker credentials and the ACL was corrected; the UI then connected and began receiving maps. Along the way the user had to put `rbr` in sudoers, add `~/.local/bin` to `$PATH`, and install `pip` before the runtime could go in.

Zigbee pairing produced the first real device set: thermometers `DR-HT`, `KW-HT`, `LR-HT`, `OB-HT` and `RW-HT`, the TRVs `DR-Rad`, `KW-Rad`, `LR-Rad` and `OB-Rad`, and a TS011F plug. The room abbreviations were decoded with the user: DR was Dining Room, KW Kitchen, LR Living Room, and RW, KW and OB were bedrooms. The first map had Dining Room, KW, OB, RW and Living Room, with the demand relay left unset. The UI initially failed with `room-0-name` and then `room-4-name` as the room list grew; the cause was thermometer-only rooms being filtered as the outside sensor, and the render guard was fixed so rooms with no relays still get cards. The user also flagged that the devices were battery-powered TRVs whose controller support was not complete yet.

That led to the self-contained TRV work: a room with a `trv` has no relays, the controller sends `system_mode` and `occupied_heating_setpoint` instead of switching a relay, a setpoint changed on the valve's dial is adopted back into the schedule, and the map format and README were updated. The battery TRV trial was now live rather than documentary. The session closed with the first system running, the rooms visible in the PWA, and the remaining follow-ups recorded rather than assumed.

# 2026-10-20

## 08:05 — Special Actions

**User**

Work continued on the special actions and one-off overrides.

**Assistant**

The override work was tightened so a one-off change is retired when its morning period ends, not only at midnight. `PruneOverrides` became a wrapper that reads the clock once, with `PruneOverridesAt` as the testable half; the notification path was separated so a fresh override is judged against today's profile. The schedule editor and the override UI were exercised against the controller, and the tests for override arming, expiry, disabled periods and the schedule editor were extended. The work was kept broker-free, using the extracted controller routines and the PWA compile check.

### 10:34 — Various 1

**User**

Can you tell me which thermometer the TRV in Living Room is associated with — the one in the TRV itself or the `LR-HT` thermometer?

**Assistant**

The live map had `sensor: LR-HT` and `trv: LR-Rad` for Living Room. RBR reads the room temperature from `sensor`, so the answer was `LR-HT`; the TRV's own `local_temperature` was only a separate diagnostic value. At that moment `LR-HT` read 19.77 °C while `LR-Rad` reported 21 °C and was idle, so the valve was not heating even though RBR saw the room below target.

**User**

Can I set the TRV to use `LR-HT` instead of its internal sensor?

**Assistant**

The TRVZB exposes `temperature_sensor_select` and `external_temperature_input`, so the hardware can do it, but RBR did not feed the external value. The one-off MQTT commands were demonstrated, and the user chose the RBR-native route rather than a standalone sync service.

**User**

Please wire up the RBR-native version.

**Assistant**

Implemented the controller-to-bridge external-sensor path: `ProcessTrv` sends `trvsensor` and the room thermometer reading as `external`; `deviceControl.allspeak` passes them; `zigbee-bridge.py` publishes `external_temperature_input` and `temperature_sensor_select`. The controller sends the reading when it changes, throttled to five minutes, and always with a setpoint/mode command. A TRV whose `sensor` is a different thermometer is set to `remote_temperature`; one whose `sensor` is the valve itself stays `local_temperature`. `trvext` and `trvextat` were added to the room identity so the throttle survives a materialise/commit; tests cover the parser, the state capture and the round trip. The change was deployed to `hvac01` and verified: `LR-Rad` went to `remote_temperature` with `external_temperature: 20` and a local temperature of 20 °C.

**User**

The LR TRV has switched back to local for its sensor. Can you see why?

**Assistant**

`LR-HT` had stopped reporting at 13:44 and was about 92 minutes stale. RBR's 45-minute gate therefore emptied the room reading and `ProcessTrv` correctly sent `mode: off`, `sensor: local`; the bridge's `last_command` recorded that exact command and Zigbee2MQTT showed `temperature_sensor_select: local_temperature`. The valve was not at fault. The mesh showed `LR-HT` parented to the new Zigbee plug but still not reporting — a sensor-side problem.

**User**

Will the switchover reverse when the HT comes back on?

**Assistant**

Yes. A fresh `LR-HT` report reaches the controller on its next one-minute merge; after the stale status clears, the next cycle sends `heat` with `sensor: remote` and the new reading. The expected delay is up to about a minute plus one or two 10-second cycles. If the room is Off or its schedule has ended, it will stay local/off until the room is turned on.

**User**

The UI is reporting `OB-HT` as having last reported 846 minutes ago, but Z2M shows current readings.

**Assistant**

Z2M was showing its cached state, not a live reading. `OB-HT` had `interview_completed: false`, no parent and no neighbours; the mesh showed `OB-HT` and `OB-Rad` both silent for about 15 hours. The cached value was the last successful report. The user added a mains Zigbee plug; `OB-HT` and `OB-Rad` came back through it, while `LR-HT` remained silent. The conclusion was that the TRVs are battery-powered end devices and cannot route; a mains-powered Zigbee router/smartplug is the right fix for the OB room.

**User**

I've moved back to my home system. Please arrange for the text “xxx is calling for heat” to take the same colour as the room name in the room card.

**Assistant**

`PaintSummary` now colours the summary title with `var(--color-accent)` whenever rooms are calling, unless frost protection is active; otherwise it uses the normal primary text colour. This covers both “Living Room is calling for heat” and “N rooms calling for heat” and matches the accent used for a calling room's name.

**User**

The UI error was `Line 910: No such element 'summary-avg'`.

**Assistant**

The deployed shell and summary card were current; the error came from an older cached shell whose line 910 still attached `SummaryAvg`, while the new card had removed that element. Added a hidden legacy `summary-avg` anchor to `summary-card.json` so an old cached shell can attach harmlessly, and bumped the service-worker cache so the current shell is precached and the old cache deleted.

**User**

In Timed mode, when Advance is active the only indication is `(A)` against the end time; the mode indicator should change to an A symbol.

**Assistant**

Added `advance.svg` and used it for the room's status chip when `Mode` is `Timed` and `Advance` is `A`, in the heat-chip colours. The `(A)` suffix remains. Sensor, offline, partial-failure, boost and On states still take priority, and the chip falls back to the clock otherwise.

**User**

The pencil icon isn't obvious, especially at its smaller rendering; an icon in the `various` folder may work better.

**Assistant**

Converted the supplied JPG into a transparent mask PNG (`edit-text.png`) and used it for the profile-row rename, day-edit and room-rename buttons at 16px, with accessible labels. Added `various/` to `.gitignore`, added the new icons to the PWA precache list, and bumped the cache.

**User**

If I select a room, tap Edit schedule, change one time value and tap the close X, the card closes and the change reverts; I expected a warning.

**Assistant**

The first unsaved-changes implementation covered the editors' own Cancel buttons, but the chrome X and scrim belong to `shell.allspeak`, which did not know the module's dirty state. The parent now leaves a close request in shared storage while a module editor is open; the schedule, devices and profiles editors poll for it and route it through their own Cancel handler, so the dirty confirmation runs. Verified in the browser: the X now warns, dismissing keeps the editor and accepting discards. A first attempt that attached module handlers directly to the shared X/scrim was rejected after it was found to replace the parent's handler and leave parent-owned sheets unable to close.

**User**

All changes good, so commit & push.

**Assistant**

Committed `fc60527` — “Warn before discarding sheet edits and clarify room-card affordances” — and pushed it to `origin/main`. The push initially failed because the configured SSH key was unusable; it succeeded through the valid `gh` credentials over HTTPS. The follow-up close-X fix remains uncommitted in the working tree, with the service-worker cache at `rbr-v1-2610201830`.
