# What to do

- **Deploy the controller.** `controller.allspeak` changed (and its `simulator.allspeak` mirror). Either `./deploy.sh --release` and let each controller pick it up on its next hourly update, or `scp controller.allspeak` to a controller and let the next 60-second run pick it up. No UI reload and no map change: the PWA was already showing the truth.

# What changed

Schedule times were converted to an instant by adding `HH:MM` to local midnight. That is only right on a 24-hour day: when the clocks change, every time after the change is an hour out for the rest of that day. Today (25 October 2026, clocks back at 02:00) the controller put Bedroom 1's 08:00 period at 07:00 and called for heat at 07:35 while the room's card correctly said "Off until 08:00". The conversion now re-reads the local hour and minute of its candidate and shifts by the difference — the real offset change — with the difference taken modulo a day so a late time on the short spring day also corrects by the hour rather than by a day.

`tests/unit/unit-03-time.allspeak` gains the guard that was missing: convert the current wall clock and require the result to read back as that same hour and minute. It fails against the old conversion on a transition day and passes on the new one. The full-day span test now accepts 23, 24 or 25 hours, because that is what a calendar day really is.
