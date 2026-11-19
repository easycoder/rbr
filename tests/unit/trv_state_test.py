#!/usr/bin/env python3
"""
trv_state_test.py - the TRV running-state gate must survive the bridge's number.

Run directly:  python3 tests/unit/trv_state_test.py
or as part of: tests/unit/run-unit-tests.sh

Why this exists. `ProcessTrvState` compares the valve's `last_seen` with `now`
so a running state older than the 45-minute sensor gate is not shown as live.
`zigbee-bridge.py` writes `last_seen` as `time.time()` — a float epoch, e.g.
`1794857533.0439382` — and AllSpeak has no float type, so the value arrives as
text. `multiply TrvSeen by 1000` converts text with `int()`, which raises on the
decimal and (with no `or`) ends the process. On the live system that killed the
controller 70-odd seconds into every session, ~45 times an hour, for weeks
(2026-11-17 report). The routine is extracted from controller.allspeak at run
time, not mirrored, so the test always exercises the code that ships.
"""

import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
CONTROLLER = REPO / "controller.allspeak"

ROUTINES = ("TrvReportAge", "ProcessTrvState")

DECLARATIONS = """\
dictionary Room
dictionary ZigbeeTrvs
variable TrvRunningState
variable TrvName
dictionary TrvState
variable TrvSeen
variable TrvAge
variable TrvWasRunning
variable MapHasChanged
variable ProbeNow
variable ProbeSecs
variable StaleSecs
variable ProbeText
variable S
"""

# Each scenario re-arms the room to `was` before the call, so the assertion
# distinguishes "the state was kept" from "the routine set it".
DRIVER = """\
put now into ProbeNow
divide ProbeNow by 1000 giving ProbeSecs

! The shape the bridge writes: a float epoch. This is the value that killed
! the controller, because a decimal is a string here.
put `{"DR-Rad":{"running_state":"heat","last_seen":` cat ProbeSecs cat `.0439382}}` into ProbeText
put json ProbeText into ZigbeeTrvs
reset Room
set entry `name` of Room to `Dining Room`
set entry `trv` of Room to `DR-Rad`
set entry `trvrunning` of Room to `idle`
gosub to ProcessTrvState
if Room has entry `trvrunning` put entry `trvrunning` of Room into S else put `missing` into S
log `PROBE fresh=` cat S

! 46 minutes old: past the 45-minute gate, so the state is not live.
put ProbeSecs into StaleSecs
take 2760 from StaleSecs
put `{"DR-Rad":{"running_state":"heat","last_seen":` cat StaleSecs cat `.5}}` into ProbeText
put json ProbeText into ZigbeeTrvs
reset Room
set entry `name` of Room to `Dining Room`
set entry `trv` of Room to `DR-Rad`
set entry `trvrunning` of Room to `heat`
gosub to ProcessTrvState
if Room has entry `trvrunning` put entry `trvrunning` of Room into S else put `missing` into S
log `PROBE stale=` cat S

! An integer epoch (an older bridge, or a value written as a whole number).
put `{"DR-Rad":{"running_state":"idle","last_seen":` cat ProbeSecs cat `}}` into ProbeText
put json ProbeText into ZigbeeTrvs
reset Room
set entry `name` of Room to `Dining Room`
set entry `trv` of Room to `DR-Rad`
set entry `trvrunning` of Room to `heat`
gosub to ProcessTrvState
if Room has entry `trvrunning` put entry `trvrunning` of Room into S else put `missing` into S
log `PROBE integer=` cat S

! No last_seen at all: there is nothing to judge the state against, so it stays.
put `{"DR-Rad":{"running_state":"heat"}}` into ProbeText
put json ProbeText into ZigbeeTrvs
reset Room
set entry `name` of Room to `Dining Room`
set entry `trv` of Room to `DR-Rad`
set entry `trvrunning` of Room to `idle`
gosub to ProcessTrvState
if Room has entry `trvrunning` put entry `trvrunning` of Room into S else put `missing` into S
log `PROBE unseen=` cat S

! A valve reporting something other than heat/idle is not a state either.
put `{"DR-Rad":{"running_state":"off","last_seen":` cat ProbeSecs cat `.9}}` into ProbeText
put json ProbeText into ZigbeeTrvs
reset Room
set entry `name` of Room to `Dining Room`
set entry `trv` of Room to `DR-Rad`
set entry `trvrunning` of Room to `heat`
gosub to ProcessTrvState
if Room has entry `trvrunning` put entry `trvrunning` of Room into S else put `missing` into S
log `PROBE other=` cat S
stop
"""


def extract_routine(source, label):
    """Return the named label and its body, verbatim, from controller source."""
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
        "info `trv running-state probe`",
        "",
        "script TrvStateProbe",
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
        probe = pathlib.Path(tmp) / "trv-state-probe.allspeak"
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


class TrvRunningState(unittest.TestCase):
    """`last_seen` is a decimal string; the gate must convert it, not die."""

    @classmethod
    def setUpClass(cls):
        cls.v = run_probe()

    def test_a_fractional_last_seen_is_live(self):
        # The crash: 1794857533.0439382 and multiply's int() conversion.
        self.assertEqual(self.v["fresh"], "heat",
                         "a fresh fractional last_seen did not keep the valve state")

    def test_an_old_state_is_cleared(self):
        self.assertEqual(self.v["stale"], "",
                         "a state older than the 45-minute gate was kept")

    def test_an_integer_last_seen_still_works(self):
        self.assertEqual(self.v["integer"], "idle")

    def test_a_state_without_last_seen_is_kept(self):
        self.assertEqual(self.v["unseen"], "heat")

    def test_anything_else_is_not_a_state(self):
        self.assertEqual(self.v["other"], "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
