#!/usr/bin/env python3
"""
period_grace_test.py - the window that lets a period start on the last known
temperature when the thermometer is between reports.

Run directly:  python3 tests/unit/period_grace_test.py
or as part of: tests/unit/run-unit-tests.sh

Why this exists. The 45-minute staleness gate empties TempNow, which holds the
heat off until a thermometer reports again. A period that starts inside that
silence can therefore miss its whole start (the 2026-11-03 Bedroom 1 report:
due on at 07:00, cold at 07:25, heat only at the 60-minute report).
PeriodHeatGrace grants a period's first 30 minutes the preserved last reading.
The bound is the whole safety argument, so this test pins the window from both
sides along with the conditions that must NOT grant it: no last reading, no
scheduled period, On mode, an all-day period, and a period that began
yesterday and wraps midnight.

PeriodHeatGrace is extracted from controller.allspeak at run time, with the two
time/temperature converters it calls, so the test exercises the code that
ships. Periods are built relative to `now`, which keeps the cases independent
of the time of day (a window built across midnight still resolves correctly).
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
dictionary Room
dictionary Period
list PeriodList
variable EventCount
variable NaturalPeriodActive
variable Mode
variable Time
variable Temp
variable T
variable I
variable GraceStart
variable GraceElapsed
variable GraceTemp
variable PeriodGrace
variable OnOffset
variable OffOffset
variable OnText
variable OffText
"""

DRIVER = """\
! Build one period whose `on` is OnOffset ms from now and `off` is OffOffset
! ms from now, then run the grace probe over it.
gosub to ResetProbe

! 1. Started 10 minutes ago, last reading 19.5 C: the grace applies.
put -600000 into OnOffset
put 600000 into OffOffset
gosub to MakePeriod
set entry `temperature` of Room to 1950
gosub to PeriodHeatGrace
log `PROBE recent-grace=` cat PeriodGrace
log `PROBE recent-temp=` cat GraceTemp

! 2. Started 45 minutes ago: the 30-minute window has closed.
gosub to ResetProbe
put -2700000 into OnOffset
put 600000 into OffOffset
gosub to MakePeriod
set entry `temperature` of Room to 1950
gosub to PeriodHeatGrace
log `PROBE old-grace=` cat PeriodGrace

! 3. No last reading: nothing to decide on, so no grace.
gosub to ResetProbe
put -600000 into OnOffset
put 600000 into OffOffset
gosub to MakePeriod
gosub to PeriodHeatGrace
log `PROBE noreading-grace=` cat PeriodGrace

! 4. An all-day period (on = off) has no start a schedule asked for.
gosub to ResetProbe
put 0 into OnOffset
put 0 into OffOffset
gosub to MakePeriod
set entry `temperature` of Room to 1950
gosub to PeriodHeatGrace
log `PROBE allday-grace=` cat PeriodGrace

! 5. Only Timed mode is a scheduled period.
gosub to ResetProbe
put -600000 into OnOffset
put 600000 into OffOffset
gosub to MakePeriod
set entry `temperature` of Room to 1950
set Mode to `on`
gosub to PeriodHeatGrace
log `PROBE onmode-grace=` cat PeriodGrace

! 6. A period that began yesterday and wraps midnight is not "just started".
gosub to ResetProbe
put 600000 into OnOffset
put 300000 into OffOffset
gosub to MakePeriod
set entry `temperature` of Room to 1950
gosub to PeriodHeatGrace
log `PROBE wrapped-grace=` cat PeriodGrace

! 7. No period running at all.
gosub to ResetProbe
put -600000 into OnOffset
put 600000 into OffOffset
gosub to MakePeriod
set entry `temperature` of Room to 1950
set NaturalPeriodActive to -1
gosub to PeriodHeatGrace
log `PROBE background-grace=` cat PeriodGrace

! 8. The preserved reading can still be a "19.5" string.
gosub to ResetProbe
put -600000 into OnOffset
put 600000 into OffOffset
gosub to MakePeriod
set entry `temperature` of Room to `19.5`
gosub to PeriodHeatGrace
log `PROBE string-grace=` cat PeriodGrace
log `PROBE string-temp=` cat GraceTemp

stop

ResetProbe:
    reset Room
    reset PeriodList
    put `timed` into Mode
    set EventCount to 0
    set NaturalPeriodActive to 0
    clear PeriodGrace
    put empty into GraceTemp
    return

MakePeriod:
    reset Period
    put now into T
    add OnOffset to T
    put datime T format `%H:%M` into OnText
    put now into T
    add OffOffset to T
    put datime T format `%H:%M` into OffText
    set entry `on` of Period to OnText
    set entry `off` of Period to OffText
    set entry `temp` of Period to `20.0`
    append Period to PeriodList
    set EventCount to 1
    set NaturalPeriodActive to 0
    return
"""


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
        "info `period grace probe`",
        "",
        "script PeriodGraceProbe",
        "",
        DECLARATIONS.strip(),
        "",
        DRIVER.strip(),
        "",
    ]
    for label in ("PeriodHeatGrace", "ConvertTimeToInt", "ConvertTempToInt"):
        parts.append(extract_routine(source, label))
        parts.append("")
    parts.extend(["script end", ""])
    return "\n".join(parts)


def run_probe():
    binary = os.environ.get("ALLSPEAK", "allspeak")
    if not shutil.which(binary.split()[0]):
        raise unittest.SkipTest(f"{binary} not found — install AllSpeak to run this test")
    with tempfile.TemporaryDirectory() as tmp:
        probe = pathlib.Path(tmp) / "period-grace-probe.allspeak"
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


class PeriodStartGrace(unittest.TestCase):
    """A period may start on the last known reading, for 30 minutes only."""

    @classmethod
    def setUpClass(cls):
        cls.v = run_probe()

    def test_a_period_that_just_started_uses_the_last_reading(self):
        self.assertIn(self.v["recent-grace"], ("1", "True"))
        self.assertEqual(self.v["recent-temp"], "1950")

    def test_the_window_closes_after_thirty_minutes(self):
        self.assertIn(self.v["old-grace"], ("0", "False"))

    def test_without_a_last_reading_there_is_no_grace(self):
        self.assertIn(self.v["noreading-grace"], ("0", "False"))

    def test_an_all_day_period_has_no_start_to_grace(self):
        self.assertIn(self.v["allday-grace"], ("0", "False"))

    def test_only_timed_mode_is_a_scheduled_period(self):
        self.assertIn(self.v["onmode-grace"], ("0", "False"))

    def test_a_period_that_began_yesterday_is_not_just_started(self):
        self.assertIn(self.v["wrapped-grace"], ("0", "False"))

    def test_no_active_period_means_no_grace(self):
        self.assertIn(self.v["background-grace"], ("0", "False"))

    def test_a_preserved_reading_is_normalised_to_hundredths(self):
        self.assertIn(self.v["string-grace"], ("1", "True"))
        self.assertEqual(self.v["string-temp"], "1950")


if __name__ == "__main__":
    unittest.main(verbosity=2)
