# 2026-10-11

## 20:34

I've found a bug in the Advance mechanism, as follows:

On Sunday evening at 7:30pm the Sunroom felt a little cool, so I pressed Advance to select the next period, due to start at 20:00. Instead of going there, however, it advanced to 18:00. The behaviour is repeatable there and in other rooms. This is likely to be just a server-side problem. Please investigate.

**(mid-turn correction)** It didn't advance to 18::00 - it just said Off until 18:00

**(mid-turn steer)** If you need access to the cotroller itself, it's at 192.168.1.20, password r00m8Yr00m — **Username qed6**

**Assistant**

Found it, and it is both sides of the same blind spot: neither the controller nor the PWA knew that a period can start exactly where the running one ends.

Your Sunroom on Sunday (Weekend profile, read off the live box — thank you for the login) is `18:00–20:00 @ 21.5` then `20:00–23:00 @ 23.0`, two back-to-back periods. At 19:30 the room is in the first, and the *next change* in that schedule is the 20:00 period beginning — which is what you pressed Advance for. Both implementations instead assumed every from-a-period Advance means "this period ends early", so they went the wrong way.

**Why you saw "Off until 18:00"**

- The controller's `ApplyPeriodsAdvance`, from a natural period, went straight to background-temp. So instead of bringing 20:00 forward it switched the heating off and left the room at background until the real 20:00 arrived — the cooling you felt, and the opposite of what pressing Advance means.
- The PWA's projection searched for the next `on` strictly *after* the running period's `off`. A period starting at exactly that minute (20:00) failed the strict test, the wrap-around then picked the day's first period, and the subline rendered `Off until 18:00 (A)`. That string, as you corrected, is exactly what you saw.

**The fix** (`controller.allspeak`, `ApplyPeriodsAdvance`) — from a period, the shift now lands on the schedule's next change: normally this period's end, so heat off until the next period starts naturally; but when a period starts exactly where this one ends, that period is brought forward and the room heats to its temp now. From background, and for a genuine gap, and for the last period of the day, nothing changes. The auto-cancel is untouched: at 20:00 the natural period rolls, the advance cancels, and the room carries on at 23.0 with no glitch.

**The matching fix** (`new-ui/resources/allspeak/map-to-rooms.allspeak`) — the projection's search now includes the boundary minute, and the row only shows "Off until <next on>" with the BG prefix when the advance really does land in a gap. Your Sunroom now reads `23.0°→23:00 (A)` while advanced, agreeing with what the controller is doing.

**Verified two ways, on the real code**

- Built a probe that extracts the actual subroutines from `controller.allspeak` and runs them under the AllSpeak runtime, with the period times built relative to the clock so the cases hold at any hour: [code omitted] Back-to-back now gives `period=1 target=2300`; the other five cases are unchanged, and against the pre-fix code the new cases come out `period=-1 target=1200` — the bug, reproduced.
- Rendered the PWA in headless Chromium with a faked clock at Sunday 19:30 and a routed `demo-map.json` carrying your Sunroom/Hall/Kitchen shapes, then read the row text: [code omitted] Before the fix the Sunroom read `Off until 18:00 (A)` — your report, reproduced; after it, `23.0°→23:00 (A)`. The Hall (a real gap after its period) and the Kitchen (engaged from background) are unchanged, and the no-advance row still reads its natural `21.5°→20:00`. The first cut of my display condition misfired here — the Hall showed `21.0°→22:30 (A)` instead of "Off until" — which is why the condition is now the controller's own exact-match adjacency test rather than a `<=`.
- `./tests/unit/run-unit-tests.sh`: 65 tests, 173 checks, all pass. `unit-04`'s mirrored `ApplyPeriodsAdvance` is kept in sync and two advance cases were added (back-to-back → joins the next period; gap after → stays at background); both fail against the old logic, and `asdoc-check.py` is clean on the files I touched.

**Two things I noticed and left alone** (in `DIFF.md`): the Advance button's label says "Advance to next schedule period (22:30)" when the room is in its last period, where 22:30 is the period's *end*, so the wording is off in the gap case — worth "next schedule change"; and a wrap-around "Off until" line names no day, so tomorrow's first period reads as just "18:00".

To take it live: deploy `controller.allspeak` and restart the service on the box, and reload the PWA, since both halves need to agree.

The probe scripts are throwaway, in `/tmp/rbrprobe` (`make_probe.py` regenerates the AllSpeak probe from any revision, `pwa_probe.js` drives the headless PWA) — say the word if you would like them kept somewhere permanent. Also FYI: `version` in the working tree was already dirty when I started (`2609271537` vs HEAD's `2609261125`); I left it alone.
