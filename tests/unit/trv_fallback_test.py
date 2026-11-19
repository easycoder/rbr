#!/usr/bin/env python3
"""
trv_fallback_test.py - heating a stale room from the valve's own sensor.

Run directly:  python3 tests/unit/trv_fallback_test.py
or as part of: tests/unit/run-unit-tests.sh

Why this exists. When a room thermometer goes quiet the controller holds the
room off, because this system refuses to heat without feedback. A
self-contained valve is itself a thermostat, so the 2026-11-19 design lets it
take over: learn the offset between the valve's sensor and the room's while
both report, then feed the valve a setpoint shifted by that offset and decide
the heat on the corrected reading. The bounds are the whole safety argument —
no offset, no valve report, no period, a heat-soaked reading or an offset that
does not track the room must all leave the room on the ordinary held-off rule.
This pins those bounds and the shift arithmetic.

The routines are extracted from controller.allspeak at run time, with the
converter they call, so the test exercises the code that ships.
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

ROUTINES = ("TrvReportAge", "LearnTrvBias", "ProcessTrvBias",
            "ApplyTrvBiasToSetpoint", "ConvertTempToInt")

DECLARATIONS = """\
dictionary Room
dictionary ZigbeeTrvs
dictionary TrvState
variable TrvName
variable RoomName
variable TrvAge
variable TrvSeen
variable TrvLocalText
variable TrvLocalTemp
variable TrvBiasDelta
variable TrvBiasAbs
variable TrvBiasMove
variable TrvBiasStep
variable TrvBiasN
variable TrvBiasMean
variable TrvBiasMin
variable TrvBiasMax
variable TrvBiasSpread
variable TrvBiasValve
variable TrvBiasLast
variable TrvBiasOver
variable TrvBiasNow
variable TrvBiasWas
variable TrvBiasShift
variable TrvBiasWhole
variable TrvBiasDeg
variable TrvBiasFrac
variable TrvFallback
variable TrvFallbackTemp
variable TrvFallbackWasTemp
variable TrvFails
variable TrvSetpoint
variable TempNow
variable Mode
variable PeriodActive
variable Simulate
variable MapHasChanged
variable Temp
variable ProbeNow
variable ProbeSecs
variable StaleSecs
variable TempText
variable K
variable S
"""

DRIVER = """\
put now into ProbeNow
divide ProbeNow by 1000 giving ProbeSecs

! ---------- learning ----------
! Four samples of a valve reading 1.0 C high: the mean is -100 hundredths.
gosub to ResetProbe
set entry `sensor` of Room to `S1`
set entry `trv` of Room to `T1`
put 2000 into TempNow
put `{"T1":{"local_temperature":21.0,"last_seen":` cat ProbeSecs cat `}}` into TempText
put json TempText into ZigbeeTrvs
put 0 into K
while K is less than 4
begin
    gosub to LearnTrvBias
    increment K
end
put entry `trvbias` of Room into S
log `PROBE learned-bias=` cat S
log `PROBE learned-n=` cat TrvBiasN
put entry `trvbiasvalve` of Room into S
log `PROBE learned-valve=` cat S

! A 10 C gap is a heat-soaked sensor, not a calibration: ignored.
put `{"T1":{"local_temperature":30.0,"last_seen":` cat ProbeSecs cat `}}` into TempText
put json TempText into ZigbeeTrvs
gosub to LearnTrvBias
put entry `trvbias` of Room into S
log `PROBE heatsample-bias=` cat S
log `PROBE heatsample-n=` cat TrvBiasN

! A fresh room reading is the only time the pair is comparable.
put `{"T1":{"local_temperature":21.0,"last_seen":` cat ProbeSecs cat `}}` into TempText
put json TempText into ZigbeeTrvs
put empty into TempNow
gosub to LearnTrvBias
put entry `trvbias` of Room into S
log `PROBE stale-room-bias=` cat S

! A replaced valve is a new sensor: the estimate starts again.
set entry `trvbiasvalve` of Room to `OLD-VALVE`
set entry `trvbiasn` of Room to 8
put 2000 into TempNow
gosub to LearnTrvBias
put entry `trvbias` of Room into S
log `PROBE replaced-bias=` cat S
log `PROBE replaced-n=` cat TrvBiasN
put entry `trvbiasvalve` of Room into S
log `PROBE replaced-valve=` cat S

! ---------- the decision ----------
! Trusted: stale room, live valve, four samples, last reading 19.0 C.
gosub to DelegateProbe
gosub to ProcessTrvBias
if TrvFallback put `yes` into S else put `no` into S
log `PROBE trusted-fallback=` cat S
log `PROBE trusted-est=` cat TrvFallbackTemp
put entry `trvfallback` of Room into S
log `PROBE trusted-field=` cat S

! Too few samples: no estimate, no fallback.
gosub to DelegateProbe
set entry `trvbiasn` of Room to 3
gosub to ProcessTrvBias
if TrvFallback put `yes` into S else put `no` into S
log `PROBE few-fallback=` cat S

! A fresh room reading means the ordinary path, not the fallback.
gosub to DelegateProbe
put 1950 into TempNow
gosub to ProcessTrvBias
if TrvFallback put `yes` into S else put `no` into S
log `PROBE fresh-fallback=` cat S

! Timed outside a period has no heat to delegate.
gosub to DelegateProbe
put -1 into PeriodActive
gosub to ProcessTrvBias
if TrvFallback put `yes` into S else put `no` into S
log `PROBE outside-fallback=` cat S

! Off wants nothing, whatever the valve says.
gosub to DelegateProbe
put `off` into Mode
gosub to ProcessTrvBias
if TrvFallback put `yes` into S else put `no` into S
log `PROBE off-fallback=` cat S

! The room sensor is the valve itself: there is no second sensor to fall back from.
gosub to DelegateProbe
set entry `sensor` of Room to `T1`
gosub to ProcessTrvBias
if TrvFallback put `yes` into S else put `no` into S
log `PROBE samesensor-fallback=` cat S

! A silent valve is not evidence of anything.
gosub to DelegateProbe
put ProbeSecs into StaleSecs
take 2760 from StaleSecs
put `{"T1":{"local_temperature":20.0,"last_seen":` cat StaleSecs cat `.5}}` into TempText
put json TempText into ZigbeeTrvs
gosub to ProcessTrvBias
if TrvFallback put `yes` into S else put `no` into S
log `PROBE oldvalve-fallback=` cat S

! First cycle of an outage: a reading 6 C above the room's last value is
! heat-soak, not calibration, so the fallback refuses to start.
gosub to DelegateProbe
put `{"T1":{"local_temperature":25.0,"last_seen":` cat ProbeSecs cat `}}` into TempText
put json TempText into ZigbeeTrvs
gosub to ProcessTrvBias
if TrvFallback put `yes` into S else put `no` into S
log `PROBE heatsoke-start=` cat S

! Once running, that same difference is expected: the room is under the
! valve's control and has been warming.
gosub to DelegateProbe
set entry `trvfallback` of Room to `yes`
put `{"T1":{"local_temperature":25.0,"last_seen":` cat ProbeSecs cat `}}` into TempText
put json TempText into ZigbeeTrvs
gosub to ProcessTrvBias
if TrvFallback put `yes` into S else put `no` into S
log `PROBE heatsoke-running=` cat S

! A spread wider than 2.5 C means the two sensors do not track each other.
gosub to DelegateProbe
set entry `trvbiasmin` of Room to -400
set entry `trvbiasmax` of Room to 100
gosub to ProcessTrvBias
if TrvFallback put `yes` into S else put `no` into S
log `PROBE spread-fallback=` cat S

! ---------- the setpoint shift ----------
put `20.0` into TrvSetpoint
set entry `trvbias` of Room to -120
gosub to ApplyTrvBiasToSetpoint
log `PROBE shift-high=` cat TrvSetpoint

put `20.0` into TrvSetpoint
set entry `trvbias` of Room to 50
gosub to ApplyTrvBiasToSetpoint
log `PROBE shift-low=` cat TrvSetpoint

! The valve's own range is the outer bound.
put `35.0` into TrvSetpoint
set entry `trvbias` of Room to -500
gosub to ApplyTrvBiasToSetpoint
log `PROBE shift-max=` cat TrvSetpoint

put `4.0` into TrvSetpoint
set entry `trvbias` of Room to 500
gosub to ApplyTrvBiasToSetpoint
log `PROBE shift-min=` cat TrvSetpoint
stop

ResetProbe:
    reset Room
    reset ZigbeeTrvs
    put `timed` into Mode
    put 0 into PeriodActive
    clear Simulate
    clear MapHasChanged
    put empty into TempNow
    put empty into TrvBiasN
    put empty into TrvBiasValve
    clear TrvFallback
    put empty into TrvFallbackTemp
    put empty into S
    return

DelegateProbe:
    gosub to ResetProbe
    set entry `name` of Room to `Living Room`
    set entry `sensor` of Room to `S1`
    set entry `trv` of Room to `T1`
    set entry `temperature` of Room to 1900
    set entry `trvbias` of Room to -100
    set entry `trvbiasn` of Room to 8
    set entry `trvbiasmin` of Room to -100
    set entry `trvbiasmax` of Room to -100
    set entry `trvbiasvalve` of Room to `T1`
    put `{"T1":{"local_temperature":20.0,"last_seen":` cat ProbeSecs cat `}}` into TempText
    put json TempText into ZigbeeTrvs
    return
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
        "info `trv fallback probe`",
        "",
        "script TrvFallbackProbe",
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
        probe = pathlib.Path(tmp) / "trv-fallback-probe.allspeak"
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


class TrvFallback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = run_probe()

    def test_the_offset_is_learned_from_the_pair(self):
        self.assertEqual(self.v["learned-bias"], "-100",
                         "a valve reading 1.0 C high did not learn a -1.0 C offset")
        self.assertEqual(self.v["learned-n"], "4")
        self.assertEqual(self.v["learned-valve"], "T1")

    def test_a_heat_soaked_sample_is_ignored(self):
        self.assertEqual(self.v["heatsample-bias"], "-100",
                         "a 10 C disagreement was folded into the offset")
        self.assertEqual(self.v["heatsample-n"], "4",
                         "a heat-soaked reading counted as a sample")

    def test_learning_needs_a_fresh_room_reading(self):
        self.assertEqual(self.v["stale-room-bias"], "-100")

    def test_a_replaced_valve_starts_the_estimate_again(self):
        self.assertEqual(self.v["replaced-n"], "1")
        self.assertEqual(self.v["replaced-valve"], "T1")

    def test_a_trusted_pair_delegates_the_thermostat(self):
        self.assertEqual(self.v["trusted-fallback"], "yes")
        self.assertEqual(self.v["trusted-est"], "1900",
                         "20.0 C local with a -1.0 C offset should estimate 19.0 C")
        self.assertEqual(self.v["trusted-field"], "yes",
                         "the page's field was not written")

    def test_too_few_samples_do_not_delegate(self):
        self.assertEqual(self.v["few-fallback"], "no")

    def test_a_fresh_reading_uses_the_ordinary_path(self):
        self.assertEqual(self.v["fresh-fallback"], "no")

    def test_timed_outside_a_period_does_not_delegate(self):
        self.assertEqual(self.v["outside-fallback"], "no")

    def test_off_does_not_delegate(self):
        self.assertEqual(self.v["off-fallback"], "no")

    def test_a_room_that_reads_its_own_valve_does_not_delegate(self):
        self.assertEqual(self.v["samesensor-fallback"], "no")

    def test_a_silent_valve_does_not_delegate(self):
        self.assertEqual(self.v["oldvalve-fallback"], "no")

    def test_a_heat_soaked_first_cycle_does_not_start(self):
        self.assertEqual(self.v["heatsoke-start"], "no")

    def test_a_running_fallback_is_not_rechecked_against_the_old_reading(self):
        self.assertEqual(self.v["heatsoke-running"], "yes")

    def test_an_offset_that_does_not_track_the_room_does_not_delegate(self):
        self.assertEqual(self.v["spread-fallback"], "no")

    def test_the_setpoint_is_shifted_by_the_offset(self):
        self.assertEqual(self.v["shift-high"], "21.2",
                         "a -1.2 C offset should ask a 20 C room for 21.2 C at the valve")
        self.assertEqual(self.v["shift-low"], "19.5",
                         "a +0.5 C offset should ask a 20 C room for 19.5 C at the valve")

    def test_the_shift_stays_inside_the_valves_range(self):
        self.assertEqual(self.v["shift-max"], "35.0")
        self.assertEqual(self.v["shift-min"], "4.0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
