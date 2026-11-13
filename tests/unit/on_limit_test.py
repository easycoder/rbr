#!/usr/bin/env python3
"""
on_limit_test.py - the system-wide cap on how long a room may stay in On.

Run directly:  python3 tests/unit/on_limit_test.py
or as part of: tests/unit/run-unit-tests.sh

On was the one unbounded override: a room set to On stayed on until someone
changed it. The cap keeps the manual "heat now" affordance but gives it a
deadline. `onmax` is a map-root setting (`always`, or 4–12 hours); `onuntil`
is the per-room deadline persisted with the plan; `onprevmode` is the mode the
room returns to when the deadline passes.

The three routines are extracted from controller.allspeak at run time, so the
test exercises the code that ships. The cases pin the Always On path, the
default 8-hour deadline, expiry, clamping when the setting is reduced, the
bounds for hand-edited values and the numeric-string form the System sheet
sends.
"""

import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
CONTROLLER = REPO / "controller.allspeak"

DECLARATIONS = """\
dictionary Map
dictionary Room
variable OnMax
variable OnDeadline
variable OnUntil
variable OnExpired
variable OnPrev
variable D
variable S
"""

DRIVER = """\
! 1. No setting: no deadline, no expiry.
reset Map
reset Room
set entry `mode` of Room to `on`
gosub to SetOnDeadline
clear S
if Room has entry `onuntil` set S
log `PROBE always-deadline=` cat S
gosub to CheckOnLimit
log `PROBE always-expired=` cat OnExpired

! 2. Eight hours, no deadline yet: SetOnDeadline starts one.
set entry `onmax` of Map to 8
reset Room
set entry `mode` of Room to `on`
gosub to SetOnDeadline
put entry `onuntil` of Room into D
take now from D
log `PROBE eight-remaining=` cat D
gosub to CheckOnLimit
log `PROBE eight-expired=` cat OnExpired

! 3. A deadline already in the past expires.
put now into D
take 1000 from D
set entry `onuntil` of Room to D
gosub to CheckOnLimit
log `PROBE past-expired=` cat OnExpired

! 4. Reducing the cap while the room is On clamps the existing deadline.
set entry `onmax` of Map to 4
put now into D
add 43200000 to D
set entry `onuntil` of Room to D
gosub to CheckOnLimit
put entry `onuntil` of Room into D
take now from D
log `PROBE clamped-remaining=` cat D

! 5. A hand-edited value below four hours is raised to four.
set entry `onmax` of Map to 3
reset Room
set entry `mode` of Room to `on`
gosub to CheckOnLimit
put entry `onuntil` of Room into D
take now from D
log `PROBE low-remaining=` cat D

! 6. A hand-edited value above twelve hours is lowered to twelve.
set entry `onmax` of Map to 13
reset Room
set entry `mode` of Room to `on`
gosub to CheckOnLimit
put entry `onuntil` of Room into D
take now from D
log `PROBE high-remaining=` cat D

! 7. Always On clears any deadline left by a previous setting.
set entry `onmax` of Map to `always`
put now into D
add 3600000 to D
set entry `onuntil` of Room to D
gosub to CheckOnLimit
clear S
if Room has entry `onuntil` set S
log `PROBE always-cleared=` cat S
log `PROBE always-cleared-expired=` cat OnExpired

! 8. The System sheet sends its select value as text.
set entry `onmax` of Map to `8`
reset Room
set entry `mode` of Room to `on`
gosub to CheckOnLimit
put entry `onuntil` of Room into D
take now from D
log `PROBE text-remaining=` cat D

! 9. The mode to return to: Timed and Off are kept; Boost and anything
! unknown fall back to Timed.
reset Room
set entry `onprevmode` of Room to `off`
gosub to OnReturnMode
log `PROBE return-off=` cat OnPrev
set entry `onprevmode` of Room to `boost`
gosub to OnReturnMode
log `PROBE return-boost=` cat OnPrev
set entry `onprevmode` of Room to `timed`
gosub to OnReturnMode
log `PROBE return-timed=` cat OnPrev
reset Room
gosub to OnReturnMode
log `PROBE return-empty=` cat OnPrev
stop
"""

HOUR = 3600000


def extract_routine(source, label):
    lines = source.split("\n")
    try:
        start = lines.index(label + ":")
    except ValueError:
        raise AssertionError(
            f"routine '{label}:' not found in {CONTROLLER.name} at column 0 — "
            "the extractor relies on that convention; update this test if the "
            "file was reorganised")
    end = start + 1
    while end < len(lines) and not lines[end].startswith("!! "):
        end += 1
    return "\n".join(lines[start:end]).rstrip()


def build_probe():
    source = CONTROLLER.read_text(encoding="utf-8")
    parts = [
        "info `on limit probe`",
        "",
        "script OnLimitProbe",
        "",
        DECLARATIONS.strip(),
        "",
        DRIVER.strip(),
        "",
    ]
    for label in ("OnDeadlineFromNow", "SetOnDeadline", "CheckOnLimit", "OnReturnMode"):
        parts.append(extract_routine(source, label))
        parts.append("")
    parts.extend(["script end", ""])
    return "\n".join(parts)


def run_probe():
    binary = os.environ.get("ALLSPEAK", "allspeak")
    if not shutil.which(binary.split()[0]):
        raise unittest.SkipTest(f"{binary} not found — install AllSpeak to run this test")
    with tempfile.TemporaryDirectory() as tmp:
        probe = pathlib.Path(tmp) / "on-limit-probe.allspeak"
        probe.write_text(build_probe(), encoding="utf-8")
        proc = subprocess.run([binary, str(probe)], capture_output=True, text=True, timeout=120)
    output = proc.stdout + proc.stderr
    if "Compile error" in output or "Runtime Error" in output:
        raise AssertionError("the probe did not run cleanly:\n" + output.strip())
    values = {}
    for line in output.splitlines():
        m = re.search(r"PROBE ([a-z-]+)=(.*)$", line)
        if m:
            values[m.group(1)] = m.group(2).strip()
    if not values:
        raise AssertionError("the probe produced no PROBE lines:\n" + output.strip())
    return values


def truthy(value):
    return value in ("1", "True", "true")


class OnLimit(unittest.TestCase):
    """On has a system-wide maximum and expires back to its previous mode."""

    @classmethod
    def setUpClass(cls):
        cls.v = run_probe()

    def remaining(self, name):
        return int(self.v[name])

    def test_always_on_has_no_deadline(self):
        self.assertFalse(truthy(self.v["always-deadline"]))
        self.assertFalse(truthy(self.v["always-expired"]))

    def test_eight_hours_sets_a_deadline_on_entry(self):
        self.assertAlmostEqual(self.remaining("eight-remaining") / HOUR, 8, delta=0.1)
        self.assertFalse(truthy(self.v["eight-expired"]))

    def test_a_past_deadline_expires(self):
        self.assertTrue(truthy(self.v["past-expired"]))

    def test_reducing_the_cap_clamps_an_existing_deadline(self):
        self.assertAlmostEqual(self.remaining("clamped-remaining") / HOUR, 4, delta=0.1)

    def test_below_four_hours_is_raised_to_four(self):
        self.assertAlmostEqual(self.remaining("low-remaining") / HOUR, 4, delta=0.1)

    def test_above_twelve_hours_is_lowered_to_twelve(self):
        self.assertAlmostEqual(self.remaining("high-remaining") / HOUR, 12, delta=0.1)

    def test_always_clears_an_existing_deadline(self):
        self.assertFalse(truthy(self.v["always-cleared"]))
        self.assertFalse(truthy(self.v["always-cleared-expired"]))

    def test_the_sheets_text_value_is_read_as_hours(self):
        self.assertAlmostEqual(self.remaining("text-remaining") / HOUR, 8, delta=0.1)

    def test_the_return_mode_keeps_timed_and_off(self):
        self.assertEqual(self.v["return-timed"], "timed")
        self.assertEqual(self.v["return-off"], "off")

    def test_the_return_mode_falls_back_to_timed_for_boost_and_unknown(self):
        self.assertEqual(self.v["return-boost"], "timed")
        self.assertEqual(self.v["return-empty"], "timed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
