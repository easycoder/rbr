# 2026-05-23

## 20:40

A problem this morning. Hard to explain but here goes:

At midnight the calendar switched profiles from Monday-Friday to Weekend. When I checked the UI at 8:30am it was showing the Office as requesting heat, but the mode for that room was showing Off. I checked the request relay and it was Off. I tried changing the mode for Office but it had no effect, so I assume the map wasn't being modified. (I didn't think to check that at the time.) The controler was reporting temperature changes in its log and the UI was reporting map updates all the while.

I switched the Calendar off and reselected profiles a few times and at some point it all started working properly again.

It's possible that last Sunday I had been using Boost for the Office but then changed to Off without cancelling Boost. If the map had got into an inconsistent state it may well have gone unnoticed unti the next time Weekend was seleccted (i.e. this morning).

I believe I have also seen Advance fail to cancel when the next time period arrives. Not every time; just once or twice.

Can you check the Advance and Boost controller algorithms to see if you can see anything that might need attention?

**Assistant**

Three findings, in order of likelihood for this morning's incident.

### 1. The calendar doesn't switch profile at midnight (almost certainly the cause)

`ResolveCalendarProfile` (controller.as:474) is only called from `ProcessAllRooms` (controller.as:507). `ProcessAllRooms` is in turn only called from:

- Startup (controller.as:248)
- UI action `Update Rooms` (controller.as:1552)
- UI action `Select Profile` (controller.as:1568)
- UI action `Update Profiles` (controller.as:1590)

`MainLoop` does **not** call it. So when the calendar would resolve to a new profile at 00:00, nothing triggers the controller to notice. The running controller keeps processing the rooms list from the profile that was active when it last loaded — yesterday's Monday-Friday in your case.

This exactly matches what you saw at 8:30am:

- UI showed Office mode = Off → the UI side computed today's profile (Weekend) and read Office's mode from there.
- Relay state said "requesting heat" → the controller was still cycling against Weekday's Office, which was in `timed` mode with a morning period running.
- Map updates kept flowing and temperature logs kept coming → because the controller was perfectly happy processing yesterday's profile.
- "Changing the mode for Office had no effect" → you'd have been changing the mode on Weekend's Office in the UI; the controller, bound to Weekday's rooms list, didn't see your edit reflected in the room it was actually processing. (`Operating Mode` mutates the Profile in the map, but the live `Room` array is rebound only by `ProcessAllRooms`.)
- Toggling the calendar / reselecting profiles fixed it because each of those UI actions triggers `ProcessAllRooms`, which then re-runs `ResolveCalendarProfile` and re-binds `Rooms` from the current profile.

Fix sketch: `MainLoop` should detect a day rollover (track `today` and compare each cycle) and call `ProcessAllRooms` when it changes. Also worth re-running it on any `period rolled to a new natural period across all rooms` if you'd rather not depend on the clock alone.

### 2. Advance from background-time never auto-cancels

`ApplyPeriodsAdvance` (controller.as:1111) gates the auto-cancel with:

    if PeriodWas is not -1 and NaturalPeriodActive is not PeriodWas

The `PeriodWas is not -1` guard exists to avoid a spurious cancel on the very first cycle after `ProcessAllRooms` (where `PeriodWas` is seeded to -1). But -1 is also the legitimate value for "currently in background time, no period active". So:

- Engage Advance while inside a period → `PeriodWas` is that period's index → when the natural period rolls, auto-cancel fires. Works.
- Engage Advance while in background (between periods) → `PeriodWas` is -1 → when the next natural period arrives, `PeriodWas == -1` so the guard blocks the cancel. Advance stays engaged.

And it's worse than just "no cancel": with advance still `A` and `NaturalPeriodActive >= 0`, the "from a period" branch (controller.as:1148) shifts the target to background-temp. So the heat goes OFF the moment the natural period would have started — the opposite of what the user expects.

This matches your "fail to cancel, not every time" — only when you'd engaged Advance from background.

Fix sketch: use a distinct sentinel for "first cycle, no prior value" (e.g. -2) so legitimate background (-1) participates in the rollover comparison. Or latch the engagement-period onto the room when Advance is toggled (analogous to how Boost latches `boostperiod`).

### 3. Boost leaves stale state behind when you switch out without expiry

In `ProcessUIRequest` (controller.as:1609), the boost-state setup block only runs when the *new* mode is `boost`:

    if Mode is `boost`
    begin
        if Value2 is not `boost` set entry `prevmode` of Room to Value2
        if Room has entry `boostperiod` delete entry `boostperiod` of Room
    end

When you go boost→off (or boost→timed, boost→on), the block is skipped, so `until`, `prevmode`, and `boostperiod` are all left lying on the Room. Today this is harmless — those fields are only consulted in `ProcessRoom`'s boost branch (controller.as:632), and re-entering boost via the UI refreshes them — but it does mean rooms in the map carry zombie boost state, which is exactly the kind of thing that would have made your Sunday "boost then off without cancelling" feel suspicious. (To be clear: I don't think this caused the morning's mismatch — finding #1 fully explains it.)

Fix sketch: delete `until`, `prevmode`, `boostperiod` whenever the new mode != boost and the old mode == boost, in the same block.

### Recommendation

#1 is worth fixing first; it's the bug you actually hit. #2 is worth fixing because the failure mode (heat off when user expects on) is user-visible and matches your second symptom. #3 is cleanup — low priority but cheap.

Want me to draft the patches?

## 20:55

yes

**Assistant**

Applied three patches to `controller.as`:

**P1 — midnight rollover.** New `TodayWas` variable; check `if today is not TodayWas` at the top of `MainLoop` and call `ProcessAllRooms` when it fires; `ProcessAllRooms` now sets `TodayWas to today` so every entry point (startup, UI action, midnight) stamps the baseline.

**P2 — Advance from background auto-cancels.** `ProcessAllRooms` now seeds each room's `PeriodWas` from `GetNaturalPeriod` instead of `-1`. With a real anchor (period idx or `-1` for "in background"), the cancel guard `PeriodWas is not -1` is no longer needed — removed it from `ApplyPeriodsAdvance` and `RoomStatus`. Both branches now just compare against the seeded anchor.

**P3 — boost-exit cleanup.** Added an `else if Value2 is boost` branch in `ProcessUIRequest`'s Operating Mode handler that deletes `until`, `prevmode`, and `boostperiod` whenever the new mode isn't boost. Zombie state no longer survives a boost→off / boost→timed / boost→on transition.

Doc-block prose updated for `MainLoop`, `ProcessAllRooms`, and `ProcessUIRequest` to match the new behaviour. `asdoc-check.py --write` refreshed the @hash lines; 8 verify-stale warnings remain (6 from these changes, 2 pre-existing on lines 221 and 451). You can review and "Mark verified" in asedit Blocks mode.

Worth restarting the controller to pick up the changes — and you could test #1 by toggling the calendar on/off with two distinct profiles assigned to today and tomorrow, advancing the system clock, or just waiting until 00:00.

