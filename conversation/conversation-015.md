# 2026-10-25

## 09:56

An inconsistency. This morning at 07:35 the heating was on with demand from Bedroom 1. However, the schedule was set for it to come on at 8:00 and the room card said Off even though it was on. See various/bug 261025-1.jpeg.

**Assistant**

Found it, and yes — today's clock change is the cause. The controller converts a schedule time to an instant by adding `HH:MM` to `today`, which is local midnight. That assumes a day is 24 hours long. Today is not: the clocks went back at 02:00, so an extra hour of real time has elapsed since midnight. The controller was therefore placing every time after the changeover an hour early — Bedroom 1's 08:00 period began at 07:00, by its clock — so it was calling for heat at 07:35. The room card was right: it computes from the phone's wall clock, which said 07:35 and correctly showed "Off until 08:00". In other words the heating was wrong, not the card.

Confirmed in the real runtime under `TZ=Europe/London`: the old conversion maps 07:00 to local 06:00 and 08:00 to local 07:00 today. The fix re-reads the local hour and minute of the candidate instant and shifts by the difference, with the difference normalised modulo a day so a late time on the short spring day corrects by the hour rather than by −23 hours.

Changed `controller.allspeak` and the `simulator.allspeak` mirror, plus the copied routine in the unit tests. Added the guard that was missing: convert the current wall clock and require the result to read back as the same hour and minute — it fails against the old code today and passes against the new. The full-day span test now accepts 23, 24 or 25 hours, which is what a calendar day really is.

`tests/unit/run-unit-tests.sh` passes under both UTC and `TZ=Europe/London` (71 AllSpeak tests, 179 checks, plus 40 Python tests). `DIFF.md` says to deploy the controller; the PWA needs nothing.

## 10:05

Could today's DST change have anything to do with it?

**Assistant**

Yes — it is the cause, not a coincidence. `today` is local midnight, and the conversion adds clock hours to it as if the day had a fixed offset. On a fall-back day an extra hour has really elapsed by 07:35, so the controller's schedule was an hour early: the 08:00 period started at 07:00 and it fired the heat at 07:35. On a spring-forward day the opposite happens and periods run an hour late. The PWA uses the wall clock directly, which is why its card was accurate. The fix and its regression test are in place; deploy the controller for it to take effect.
