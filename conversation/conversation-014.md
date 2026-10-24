# 2026-10-24

## 15:16

Can the schedule be made to work like Google Calendar, with a drop-down list of times and where the stop time tracks the start time by an hour until explicitly set?

**Assistant**

Yes. The schedule sheet now uses Google-Calendar-style time dropdowns, and the stop follows the start as you described.

What changed:

- Both **On at** and **Off at** are native dropdowns listing every quarter hour from 00:00 to 23:45, replacing the −/+ steppers. Temperature keeps its steppers.
- **+ Add period** creates 06:00–07:00 with the stop marked as tracking: moving the start keeps the stop exactly one hour later until a stop is picked.
- A picked stop becomes that period's duration. After that, moving the start carries the stop by the same amount, so 18:00–23:00 moved to 19:00 becomes 19:00–00:00. This is the preserve-duration rule you chose for existing periods, and it covers stops picked during the session too.
- Both ends wrap across midnight, using the shorter direction when a start crosses 00:00.
- A stored time that is not on a quarter hour is added to that card's list rather than rounded, so an unrelated Save cannot move it.
- The tracking flag is editing-only and is not written into `periods[]`.

The work is in `schedule-editor.allspeak` and `schedule-period.json`, with a new `tests/pwa-schedule-editor-check.js` that drives the real runtime. `npm run check` passes: compile 12/12, devices 10/10, schedule editor 16/16, map-push/save 4/4. Reload the PWA twice because the layout and cache version changed.

## 15:26

I think Add period should pick a start time that's as close as possible to the current time. If a period is active, pick the time it ends.

**Assistant**

Done. **+ Add period** now chooses its start from the clock: if one of the room's enabled periods is running right now, the new period starts at that period's stop; otherwise it starts at the quarter-hour slot nearest the current time (15:07 -> 15:00, 15:08 -> 15:15, 23:53 -> 00:00). The new period still stops an hour later and keeps that one-hour tracking until a stop is picked.

The active check matches the controller's `FindCurrentPeriod`: overnight periods wrap, disabled periods do not count, and an on/off pair that is equal counts as active. Overlapping periods resolve to the first match in the list, as the controller does.

Verified with `npm run check`: compile 12/12, devices 10/10, schedule editor 18/18 (with a frozen clock covering both branches), map-push/save 4/4. `DIFF.md` updated.
