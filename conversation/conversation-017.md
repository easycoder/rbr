# 2026-10-27

## 09:45

Yesterday was cloudy so during the morning I advanced Sunroom. In the early evening we lit the wood-burner in the next room, and the Sunrrom radiator went cold for the rest of the evening. At just after 3am this morning we heard the heat pump and found Sunroom was still on Advance, having presumably failed to cancel yesterday. Please look into it.

**Assistant**

Found it. The advance's auto-cancel relied on `PeriodWas`, an in-memory record of the natural period in the previous cycle. `ProcessAllRooms` reseeds it from the *current* natural period on startup, on a day rollover and after a UI save — so a change that happened while the controller was not running went unnoticed. Yesterday the controller was down for the compile outage, and the advance was still `A` in the map. With the room back in background, the next cycle applied the advance *from background* and jumped to the next period — today's 18:00 at 22°C — which is why the heat pump ran at 03:00.

The fix persists the end of the advance: `advanceuntil` is recorded when the advance is armed (the running period's end; across back-to-back periods the joined period's end; from background the next period's start), stored with the plan, and `ApplyPeriodsAdvance` cancels on it as well as on the rollover. An advance with no deadline — a map from an older controller — is cancelled rather than trusted. Leaving Timed, or arming a one-off override, clears it.

The Sunroom's schedule is the back-to-back 18:00–20:00 then 20:00–23:00 pair, so the morning advance was aimed at 18:00; from then the natural schedule would have taken over. The map now shows `advance: "-"`, so it is clear at present.

Tests: unit-04's advance cases now cover an expired deadline across a restart, a missing deadline, and the three deadline computations. 76 AllSpeak tests / 188 checks and 51 Python tests pass; the whole-controller compile check passes. `DIFF.md` says to deploy, but the SSH key on this machine is still a character device, so I could not publish.
