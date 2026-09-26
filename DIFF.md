# What to do

- **Re-deploy the controller** — `controller.as` changed behaviour (this is a second change after the release you just started, so another `./deploy.sh --release` is needed).
- **Reload the PWA** — `new-ui` changed (`schedule-period.json`, `schedule-editor.as`, `map-to-rooms.as`). A normal reload picks them up (fetched with `?v=`); hard-reload if the service worker serves a stale copy.
- **Restart the desktop app** if you use it — `desktop/rbr-desktop.as` and `rbrwidgets.py` both changed.
- **No map edit is needed.** An absent `enabled` flag means enabled, so every existing `map.json` keeps working untouched.

# What changed

A schedule period now carries an optional boolean `enabled`. A period with `enabled: false` is ignored everywhere the schedule is read — it never becomes the current period, contributes no heat, is skipped by the advance projection and cannot be the morning target of a one-off override. An **absent** flag means enabled, so older maps and hand-written periods are unaffected and the whole map does not have to be rewritten. Both schedule editors write the flag explicitly on Save, adding it to every period of the room being edited.

A disabled period is also **non-editable in both editors**: its On-at / Off-at / Target rows are greyed out (45% opacity) and made inert, while its Enabled checkbox and Delete period button stay live — so a period is re-enabled or removed by ticking the box or deleting it, not by nudging its times.

- `controller.as` — `LoadRoomPeriods` now skips periods flagged `enabled: false`, so every consumer of the period list (containment, advance, `GetNaturalPeriod`, `IdentifyMorningPeriod`, the one-off override) ignores them for free.
- `new-ui/resources/webson/schedule-period.json` — the card's footer is a row holding an **Enabled** checkbox (checked by default) to the left of *Delete period*; the ON / OFF / Target rows gained ids so they can be dimmed as a group.
- `new-ui/resources/as/schedule-editor.as` — carries the flag through clone / save, paints the checkbox and the row dimming, and toggles both on change.
- `new-ui/resources/as/map-to-rooms.as` — the room subline projection and the morning-start lookup skip disabled periods.
- `desktop/rbrwidgets.py` + `desktop/rbr-desktop.as` — the same Enabled checkbox on the desktop card, a `toggle` event carried into the working copy and the saved schedule, and a faded, non-interactive body for a disabled period.
- `tests/unit/unit-10-overrides.as` — mirrors the new filter and adds cases for a disabled period and an all-disabled room.
- `AI/MAP_FORMAT.md` — documents `periods[].enabled`.

# One thing to look at

Fixed while here: `ProcessUIRequest`'s Operating-Mode `on` branch read the room's **raw** `periods` and indexed it with `PeriodActive`, which is an index into the *effective* list. That mis-picked the period whenever an override (or now a disabled period) had shifted the list; it now uses the effective list `FindCurrentPeriod` already loaded.
