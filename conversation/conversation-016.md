# 2026-10-26

## 10:10

Problem thi morning - it seems to be ignoring the calendar and using the selected profile insted.

**Assistant**

Confirmed and fixed — and the live system has been repaired.

The cause: the calendar stores profile *names*, and the profile list stores the profiles themselves. Renaming a profile in the Profile sheet changed only the list. Your weekday profile is now called **Weekday**, but the calendar's Mon–Fri entries still said **Monday-Friday**. That name resolves to no profile, so both the controller and the page fell back to the selected profile — **All Off** — without saying so. Over the weekend the calendar's "Weekend" entry still matched, which is why it worked on Saturday and Sunday and broke on the first weekday morning.

Repair already done on the live system: Mon–Fri now point at **Weekday**; the header reads "TODAY'S PROFILE Weekday" and the rooms show the weekday schedule again.

Code fix: a rename now moves every calendar day that named the old profile to the new name; a delete clears the days that named the deleted profile; a duplicate profile name is refused (a name is how a profile is referenced); a day naming a profile that does not exist is shown as "Name (missing)" instead of looking ordinary; and the controller logs when it has to fall back. `tests/pwa-profile-sheet-check.js` drives the real sheet — it failed against the old module in 7 places. `npm run check` and the unit suite pass.

`DIFF.md` says to deploy the PWA; the desktop app's profile manager has the same rename gap, unexercised and left alone.

## 11:24

I've been sent the screenshots in various/ and I can't make sense of them. The radiators are apparently cold if Running State is "idle", hot when it's "heat".

**Assistant**

Both screens are right; they are answering different questions.

`Running State` is the valve's own verdict — `heat` = valve open, `idle` = closed — so at 06:39–06:40 all four radiators were cold. The app's orange "heating" tag is not a valve position: it is RBR's relay decision for the room, computed from the room thermometer against the schedule target, and it is shown even where there is no actuator.

At 06:39: Dining Room 19.8 vs 18.0 and Living Room 19.2 vs 18.0 → satisfied; KW 19.2 vs 19.5 and OB 19.1 vs 20.0 → calling. The valves were idle because each TRV's own local temperature was above its own setpoint: LR 19/18, DR 22.4/22, KW 20.3/19, OB 24.1/22.5. That local sensor sits at the valve and reads high; the app uses the room thermometer (DR-HT etc.).

The live map shows why nothing could follow the app: only Living Room has a `trv` (`LR-Rad`). Dining Room, KW and OB have `relays: []` and no `trv`, and the Devices sheet shows their TRV and relay fields blank. So their "heating" cannot open anything; their valves are running on their own dials. Binding DR-Rad, KW-Rad and OB-Rad in Rooms and Devices is the fix — RBR will then send each valve its target and the room thermometer reading as the external temperature.

Two related findings: an unactuated room still counts as "calling for heat" and sets `HeatingRequested`, which would fire a demand relay if one were configured (this system has none); and `running_state` is cached by the bridge but never published to the map, so the card cannot show what the valve is actually doing. Also LR-HT and OB-HT report only every 40-odd minutes, close to the 45-minute staleness gate that forces a valve off.
