# 2026-11-19

## 09:46

Last night I used "Change the morning start time" to have Bedroom 1 radiator come on an hour early. This morning it fired up at 6:30 and showed the flame icon, but the Bedroom 1 pill remained black text. At 7:30 it then went blue and the heating remained on. I tapped the pill and got in succession the 2 errors at various/error. I've also included the journal for this morning.

**Assistant**

Fixed both problems — they turned out to be separate.

**Why the pill stayed black while the flame was lit.** The page works out a room's state from the schedule itself, and it was using the *stored* schedule while the controller used the schedule *plus today's armed override*. The journal shows the request at 00:03: `Room Override`, Bedroom 1, `06:30`, `keepoff: yes`, so the controller moved the morning period to 06:30–07:30 and switched the relay on at 06:30. The page still had the unchanging 07:30–08:30 period, so it drew "Off until 07:30" in black and only turned blue at 07:30, when its own copy of the period began. `map-to-rooms.allspeak` now applies the same one-day shift as the controller's `GetEffectivePeriods` — moved start, moved stop with `keepoff` (clamped at 23:59), a skip or late start dropping the morning period, and an override dated tomorrow changing nothing today. The scheduled morning start used to pre-fill the Special time popup is captured before the shift, so an armed override is not offered back as the next time.

**The two dialogs.** `No such element: 'room-3-name'` and `Variable 'ModeTimedBtn' is not attached to a DOM element` are the home trying to repaint rows it had not built and controls nobody had wired. I reproduced the first exactly by building the home from a 2-room map and then pushing an 8-room map: `RefreshHomeScreen` looped to the new `RoomCount`, `Attach` waited for a row that was never rendered, and every later push failed the same way while the home stayed on the old rows. That is the same shape as the report. `shell.allspeak` now rebuilds when the room count changes, holds an incoming map while the reduced home's room card is being built (and flushes it afterwards), tracks whether that card was actually built, and falls back to the room list if its template never arrived instead of raising an error on every push.

**What the journal also shows**, separately and by design: the relay dropped at 07:00 for about nine minutes because the thermometer had gone quiet for 45+ minutes — the controller's sensor-staleness gate — and returned at 07:09. The brief off/on at 07:30 is the override's moved end handing back to the normal period; the `Advance` request at 07:33 then turned the demand off. Nothing in the controller or the map was wrong.

**Tests.** New `tests/ui/room-count.spec.js` covers the growth rebuild, a map landing while the room card is open, and the failed-template fallback. `tests/ui/special-override.spec.js` now asserts the moved morning is orange with the moved stop, in both views, and that the time popup still offers the scheduled start. `node tests/pwa-compile-check.js` 12/12, `tests/unit/controller-compile-check.sh` passes, the full Playwright suite passes, `tests/docs-reader-check.js` 72/72, and `asdoc-check` reports 0 errors. `tests/pwa-boot-guard-check.js` still fails its "a normal boot" case on unmodified `HEAD` (it reads `#app` after the current runtime has replaced it); that is not from this change.

**What you need to do:** run `./deploy.sh`, then reload the app once on the phone. There is no controller change and no version bump, so nothing restarts.
