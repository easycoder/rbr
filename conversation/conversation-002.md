# 2026-08-05

## 15:47

A recent change to AllSpeak added a 'scale' operator to ease conversion of floating-point strings to integers (see learn/ Arithmetic). Please examine the RBR code to see if there are any places this can be used advantageously.

**Assistant**

Analysed every decimal-string → integer conversion in the RBR `.as` sources. `scale` landed in AllSpeak only on 2026-08-04 (commit f6e0895, version 2608041425); the installed controller CLI (`allspeak-ai 260606112150`) and every pinned `allspeak.js` (repo, tests, and the live `rbrheating.com/dist/allspeak.js` unless re-pinned) predate it, so adoption is gated on a runtime upgrade. Found five clean fits plus one inline parse:

- Controller (hundredths): `controller.as` ConvertTempToInt ("20.5"→2050), `simulator.as` ConvertTempToInt (had a divergence bug: "20.5"→2005), `migrate-periods.as` TempStrToInt.
- New UI (tenths): `new-ui/resources/as/shell.as` ToTenths (25-line sign-strip + dot-split dance) and its inline average parse in ComputeSummaryStats, plus the duplicate `ToTenths` in `new-ui/resources/as/schedule-editor.as`.

Excluded: all `ConvertTimeToInt`/`ParseTimeMinutes` (HH:MM colon strings — `scale` is decimal-only) and every reverse formatter (`X cat '.' cat Y` display builders). `scale` also fixes a latent bug: the old ConvertTempToInt turned "-3.5" into -250 instead of -350.

## 15:47

I'd like the refactor to apply to both. Can you list the affected files so I can review them.

**Assistant**

Applied the refactor to all five sites (controller + UI). Affected files:

- `controller.as` — ConvertTempToInt → `put Temp scale 100 into Temp`; @hash refreshed.
- `simulator.as` — ConvertTempToInt → `scale 100` (also fixes the 2005-vs-2050 divergence with the controller).
- `migrate-periods.as` — TempStrToInt → `scale 100`, empty guard kept.
- `new-ui/resources/as/shell.as` — ToTenths → `scale 10` (NegativeFlag sign-strip dance deleted) and the ComputeSummaryStats inline average parse → `scale 10`.
- `new-ui/resources/as/schedule-editor.as` — ToTenths duplicate → `scale 10`.

Verified by compiling and running the exact new subroutine bodies under the dev AllSpeak runtime (PYTHONPATH pointing at ~/dev/allspeak/allspeak-py): 20.5→2050, 20→2000, -3.5→-350, ''→0, 21.5→2150, 15→1500, 20.5→205, -0.5→-5, -1.7→-17. `asdoc-check.py` reports 0 errors; only the expected verify-stale prompts on the two controller-side edited sections remain (re-verify in asedit). Deliberately left the unrelated pre-existing stale hashes untouched so the diff is reviewable, and left the legacy `resources/as/` copies alone. Runtime gating still applies: upgrade the controller pip package and re-pin the UI dist before deploying; the `scale` syntax fails to compile on the June runtime.
