#!/usr/bin/env python3
"""
trv_dial_adoption_test.py - the fallback's shifted setpoint is not a hand on the dial.

Run directly:  python3 tests/unit/trv_dial_adoption_test.py
or as part of: tests/unit/run-unit-tests.sh

Why this exists. `SyncTrvLocalSetpoint` treats a valve setpoint that differs
from the last commanded one as a person turning the dial and writes it into the
room's schedule. The radiator-sensor fallback deliberately sends a shifted
setpoint, so entering it — and the cycle it ends, while the valve still reports
the shifted value — looks exactly like a dial change. Without the guard, a room
would rewrite its own period target with the offset baked in, and the offset
would then compound. This pins the guard, and that an ordinary dial change is
still adopted.

The routine is extracted from controller.allspeak at run time, with the
converter it calls and a stub for ForceUpdate, so the test exercises the code
that ships.
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

ROUTINES = ("SyncTrvLocalSetpoint", "ConvertTempToInt")

DECLARATIONS = """\
dictionary Room
dictionary ZigbeeTrvs
dictionary TrvState
variable TrvName
variable TrvReported
variable TrvReportedText
variable TrvStateMode
variable TrvSetpointWas
variable TrvReportedInt
variable TrvWasInt
variable TrvDelta
variable TrvPeriodIdx
list TrvPeriods
dictionary TrvPeriod
variable TrvCommandAt
variable TrvFallback
variable TrvBiasWas
variable Temp
variable Mode
variable MapHasChanged
variable TempText
variable S
"""

DRIVER = """\
gosub to ResetProbe

! A hand on the dial is still adopted: 20.0 commanded, 22.0 reported.
set entry `trvsetpoint` of Room to `20.0`
set entry `target` of Room to 20
put `{"T1":{"setpoint":"22.0","system_mode":"heat"}}` into TempText
put json TempText into ZigbeeTrvs
gosub to SyncTrvLocalSetpoint
put entry `target` of Room into S
log `PROBE dial-target=` cat S
put entry `trvsetpoint` of Room into S
log `PROBE dial-setpoint=` cat S

! The same report while the fallback runs is the controller's own shift.
gosub to ResetProbe
set entry `trvsetpoint` of Room to `20.0`
set entry `target` of Room to 20
set TrvFallback
put `{"T1":{"setpoint":"22.0","system_mode":"heat"}}` into TempText
put json TempText into ZigbeeTrvs
gosub to SyncTrvLocalSetpoint
put entry `target` of Room into S
log `PROBE fallback-target=` cat S
put entry `trvsetpoint` of Room into S
log `PROBE fallback-setpoint=` cat S

! The exit cycle: the fallback has ended, but the valve still reports 22.0.
gosub to ResetProbe
set entry `trvsetpoint` of Room to `20.0`
set entry `target` of Room to 20
put `yes` into TrvBiasWas
put `{"T1":{"setpoint":"22.0","system_mode":"heat"}}` into TempText
put json TempText into ZigbeeTrvs
gosub to SyncTrvLocalSetpoint
put entry `target` of Room into S
log `PROBE exit-target=` cat S

! A difference under a tenth of a degree is not a dial change.
gosub to ResetProbe
set entry `trvsetpoint` of Room to `20.0`
set entry `target` of Room to 20
put `{"T1":{"setpoint":"20.0","system_mode":"heat"}}` into TempText
put json TempText into ZigbeeTrvs
gosub to SyncTrvLocalSetpoint
put entry `target` of Room into S
log `PROBE small-target=` cat S

! A valve that is not heating reports a frost setpoint, not a dial change.
gosub to ResetProbe
set entry `trvsetpoint` of Room to `20.0`
set entry `target` of Room to 20
put `{"T1":{"setpoint":"4.0","system_mode":"off"}}` into TempText
put json TempText into ZigbeeTrvs
gosub to SyncTrvLocalSetpoint
put entry `target` of Room into S
log `PROBE off-target=` cat S
stop

ResetProbe:
    reset Room
    reset ZigbeeTrvs
    put `T1` into TrvName
    set entry `trv` of Room to `T1`
    put `timed` into Mode
    clear TrvFallback
    put empty into TrvBiasWas
    clear MapHasChanged
    put empty into S
    return

ForceUpdate:
    set MapHasChanged
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
    return "\n".join([
        "info `trv dial adoption probe`",
        "",
        "script TrvDialProbe",
        "",
        DECLARATIONS.strip(),
        "",
        DRIVER.strip(),
        "",
        "\n\n".join(extract_routine(source, r) for r in ROUTINES),
        "",
        "script end",
        "",
    ])


def run_probe():
    binary = os.environ.get("ALLSPEAK", "allspeak")
    if not shutil.which(binary.split()[0]):
        raise unittest.SkipTest(f"{binary} not found — install AllSpeak to run this test")
    with tempfile.TemporaryDirectory() as tmp:
        probe = pathlib.Path(tmp) / "trv-dial-probe.allspeak"
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


class TrvDialAdoption(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = run_probe()

    def test_a_real_dial_change_is_adopted(self):
        self.assertEqual(self.v["dial-target"], "22.0")
        self.assertEqual(self.v["dial-setpoint"], "22.0")

    def test_the_shifted_setpoint_is_not_adopted_while_the_fallback_runs(self):
        self.assertEqual(self.v["fallback-target"], "20")
        self.assertEqual(self.v["fallback-setpoint"], "20.0")

    def test_the_shifted_setpoint_is_not_adopted_on_the_exit_cycle(self):
        self.assertEqual(self.v["exit-target"], "20")

    def test_a_small_difference_is_not_a_dial_change(self):
        self.assertEqual(self.v["small-target"], "20")

    def test_a_frost_setpoint_is_not_a_dial_change(self):
        self.assertEqual(self.v["off-target"], "20")


if __name__ == "__main__":
    unittest.main(verbosity=2)
