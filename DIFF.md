# 2026-11-19 — Appearance, Status and Systems move out of shell.allspeak

**Action:** `./deploy.sh`, then reload the app once on the phone. There is no controller change and no version bump, so nothing restarts.

## What changed

`new-ui/resources/allspeak/shell.allspeak` — 5,300 lines to 4,207. Three features now live in their own modules, each reached by message:

- `appearance.allspeak` (596 lines) — the page's time-of-day background, the palette and the hex maths, and the Appearance sheet's swatch / hex / time controls. Loaded at boot so the gradient is on the first frame; it forks its own hour tick.
- `status.allspeak` (345 lines) — the summary card and the top bar's live readouts: date, profile, outside reading, frost badge, demand flame, system name, and the aggregate "N rooms calling for heat" title. The shell sends a snapshot (`mount` / `paint` / `unmount`) and keeps no copy of the aggregates or the frost flag, so the card and the banner cannot disagree.
- `systems.allspeak` (438 lines) — the device's systems list, its storage and migration, the `mac` / `token` boot reply, and the whole About sheet including the pairing flow.

The shell keeps what is chrome: it renders each sheet's layout, shows and hides it with `HideAllSheets`, sets its title, and owns the controls that rebuild the home or close the chrome (the Appearance view pills and Done). Every new call is a fire-and-forget `send`, so nothing parks the shell and no map push is stranded behind a reply — except the systems `boot` request, which waits because the credential fetch cannot start without its answer.

`tests/pwa-compile-check.js`, `AGENTS.md` — the module set is eight, not six.

## Checked

`node tests/pwa-compile-check.js` 16/16, all eight modules. `npm run test:ui` 30/30. All twelve `tests/pwa-*-check.js` pass. The published `asdoc-check` reports 0 errors and 113 warnings.

Every `gosub` / `fork` / `go to` target in every module was checked separately: the compiler does not resolve them, and a lost `ToTenths` reached runtime during this change before the check existed. The simple-view spec caught it, since it exercises a room command.
