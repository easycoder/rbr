# What to do

- **Deploy the controller** (`./deploy.sh --release`). The PWA is unchanged. This release also carries the compile fix already live since `2610261218`.
- No map change. An advance still flagged when the new controller starts has no deadline to check, so it is cancelled rather than trusted; nothing needs clearing by hand.

# What changed

An Advance is a Timed-mode override, and its auto-cancel relied on `PeriodWas` — an in-memory record of the natural period in the previous cycle. `ProcessAllRooms` reseeds `PeriodWas` from the *current* natural period on startup, on a day rollover and after a UI save. A change that happened while the controller was not running (the 26th's compile outage, or any restart) therefore went unnoticed: with `advance: A` still in the map and the room back in background, the next cycle applied the advance *from background* and jumped to the next period — the following day's 18:00. That is the 03:00 heat pump.

The controller now records `advanceuntil` when the advance is armed: the instant of the schedule change it is aiming at — the running period's end, the period it joins across a back-to-back pair, or the next period's start from background. It is stored with the plan and `ApplyPeriodsAdvance` cancels on it as well as on the rollover, so a restart during or after the change cannot resurrect it. An advance with no deadline (a map written by an older controller) is cancelled rather than trusted. Leaving Timed, or arming a one-off override, clears the flag and the deadline.

`tests/unit/unit-04-periods.allspeak` gains the deadline cases: an expired deadline cancels across a restart; no deadline cancels; and the deadline is the next start, the joined period's end, or the running period's end for background, back-to-back and gap schedules.
