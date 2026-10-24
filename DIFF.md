# What to do

- **Reload the PWA twice.** The schedule sheet's layout changed — the time steppers are gone and two dropdowns replace them — and `sw.js` has a new cache version, so the first load installs the new worker and the next load uses it. There is no controller, broker or map change: this is UI-only.

# What changed

The schedule editor now picks times from dropdowns instead of stepping them with −/+ buttons: every quarter hour from 00:00 to 23:45, the same 15-minute granularity the steppers had. Both ON and OFF are native `<select>` elements, filled from one shared list built once at start-up, so the layout file does not carry 96 options per card.

The stop follows the start the way Google Calendar does it. A period added with **+ Add period** starts at the most useful time available: if one of the room's periods is running now, it starts where that period ends; otherwise it starts at the quarter-hour slot closest to the current time (never more than seven minutes behind). It stops an hour later; changing its start keeps that one-hour distance until its stop is picked. Disabled periods do not count as running. Every other period — one loaded from the map, or one whose stop has been picked — moves its stop by the same amount as the start, preserving the duration the user chose, and wraps across midnight (18:00–23:00 moved to 19:00 becomes 19:00–00:00). The rule lives in `OnPeriodStartChanged`, and the editing-only `offAuto` flag is dropped on Save.

A time already in the map that is not on the quarter-hour grid (an older schedule with odd minutes) is appended to that card's dropdown rather than being shown as the nearest slot, so an unrelated Save cannot move it.

`tests/pwa-schedule-editor-check.js` drives the sheet in the real runtime: it checks the dropdown contents, both tracking behaviours including the midnight wrap, where **+ Add period** puts a new period (nearest quarter hour, or the end of the running period), and the saved `periods[]`. `npm run check` now includes it.
