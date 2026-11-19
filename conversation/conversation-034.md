# 2026-11-18

## 15:32

Close this session

**Assistant**

Closed. No code was changed for this turn; the tree is as the last change left it, with no scratch files.

What this session settled:

- **System sheet** — Maximum on duration now reopens on the saved value (the select was being handed the option's label instead of its value), is renamed from "Maximum time in On", and an empty `onmax` reads as Always On.
- **Appearance** — a new sheet behind the hamburger's top row: Detailed/Simplified (Simplified is the default for a new installation) and a background colour chosen from ten swatches or any hex, with a "time-based changes" toggle. The page gradient is built from the chosen colour; with the toggle off it uses the afternoon stops, which carry enough of the colour to read as that shade.
- **Off rooms** — the pill now matches a Timed room's neutral pill exactly and is told apart by its fainter text alone, after both a paler and a darker tint drew the eye more than the neutral one.
- **Marketing hero** — three photos at 40/40/20 (default, mixed-ethnicity, Black couple), each a JPEG near 360–375 KB, chosen by an inline `<head>` draw, with an accessible name per photo; `tests/ui/hero.spec.js` pins all three.
- **Heating type** — the controller now stores `systemType` from `System Name` (`ApplySystemName`, `NormaliseSystemType`); it had silently dropped it for as long as the field existed.
- **Schedule** — the two quarter-hour dropdowns are native time fields, minute precision, ids `-start-time`/`-off-time`; the duration rules are unchanged.
- **Morning override** — "Move the off time too", ticked by default: the controller shifts the morning's off by the same delta (`keepoff`), clamps at 23:59, and retires the override at the moved end rather than the scheduled one.
- **Docs** — `doc/SENSOR-REPORTING.md` records the Zigbee reporting procedure; the reader's chrome no longer says "Documentation"; the product docs no longer pin the cloud broker's hostname; the About sheet's Manual opens "The interface"; prose updated for the schedule fields and the override.

Still to do, in the order that matters:

1. `./deploy.sh --release` — one deploy publishes the site, `/docs/`, the PWA and the controller pack, and carries the handover work recorded in `DIFF.md`.
2. The handover host settings and its staging test, per `DIFF.md`.
3. Recapture `docs/operation/images/10-schedule-editor.png` — it still shows the old dropdowns.

Last verification, before the handover work landed: full UI suite 26/26, unit runner 190 Python tests plus 83 AllSpeak tests / 202 checks, `pwa-compile-check` 12/12, docs-reader 72/72, `git diff --check` clean. Worth one more full pass after the deploy, given `npm run check` is reported to stop at `pwa-boot-guard-check.js` on a failure that predates this work.
