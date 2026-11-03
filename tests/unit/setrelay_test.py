#!/usr/bin/env python3
"""
setrelay_test.py - the controller's per-room heat decision, on the routine that
ships.

Run directly:  python3 tests/unit/setrelay_test.py
or as part of: tests/unit/run-unit-tests.sh

Why this exists. SetRelay decides whether a room is "calling for heat": it
drives the relay, sets `HeatingRequested` (the boiler/demand relay) and stamps
the `relay` field the page reads. A room with no relay and no TRV has no
actuator at all, so a demand from it can only fire the boiler with nothing in
the room to release the heat — and it made the page claim "heating" for rooms
that were never wired (the 2026-10-26 report). The guard is easy to lose again
because every other branch is about temperature; this test pins it, alongside
the cases it must not change.

SetRelay is extracted from controller.allspeak at run time, not mirrored, so
the test exercises the code that ships. It falls through to RoomStatus in the
controller by design; the probe supplies a `RoomStatus:` label returning
immediately, which mirrors that flow without dragging in the status logic.
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
list R
variable RelayState
variable RelayStateWas
variable HasActuator
list ActuatorRelays
variable Mode
variable TempNow
variable TempDecision
variable PeriodGrace
variable GraceTemp
variable StaleGrace
variable Target
variable PriorStatus
variable BoostTemp
variable Temp
variable HeatingRequested
variable PeriodActive
variable S
"""

DRIVER = """\
! Fresh room with a relay by default; each case overrides what it needs.
gosub to ResetRoomForProbe

! 1. A relay room below target calls, as it always did.
reset R
append `r1` to R
set entry `relays` of Room to R
put `timed` into Mode
put 1900 into TempNow
put 1950 into Target
put `off` into RelayState
clear HeatingRequested
gosub to SetRelay
log `PROBE relays-on=` cat RelayState
if HeatingRequested put `yes` into S else put `no` into S
log `PROBE relays-request=` cat S

! 2. No relay and no TRV: nothing to open, so no demand.
gosub to ResetRoomForProbe
reset R
set entry `relays` of Room to R
put `timed` into Mode
put 1900 into TempNow
put 1950 into Target
put `off` into RelayState
clear HeatingRequested
gosub to SetRelay
log `PROBE unwired-on=` cat RelayState
if HeatingRequested put `yes` into S else put `no` into S
log `PROBE unwired-request=` cat S

! 3. A TRV is an actuator: the demand stands, and the valve gets its setpoint.
gosub to ResetRoomForProbe
reset R
set entry `relays` of Room to R
set entry `trv` of Room to `T1`
put `timed` into Mode
put 1900 into TempNow
put 1950 into Target
put `off` into RelayState
clear HeatingRequested
gosub to SetRelay
log `PROBE trv-on=` cat RelayState
if HeatingRequested put `yes` into S else put `no` into S
log `PROBE trv-request=` cat S

! 4. No actuator in On mode is still no demand.
gosub to ResetRoomForProbe
reset R
set entry `relays` of Room to R
put `on` into Mode
put 1900 into TempNow
put 1950 into Target
put `off` into RelayState
clear HeatingRequested
gosub to SetRelay
log `PROBE unwired-onmode=` cat RelayState
if HeatingRequested put `yes` into S else put `no` into S
log `PROBE unwired-onmode-request=` cat S

! 5. Boost is the branch that heats without a reading; it must not resurrect
!    a room with nothing to open.
gosub to ResetRoomForProbe
reset R
set entry `relays` of Room to R
put `boost` into Mode
put empty into TempNow
put 1950 into Target
put `off` into RelayState
clear HeatingRequested
gosub to SetRelay
log `PROBE unwired-boost=` cat RelayState
if HeatingRequested put `yes` into S else put `no` into S
log `PROBE unwired-boost-request=` cat S

! 6. A missing relays entry is the same as an empty one.
gosub to ResetRoomForProbe
put `timed` into Mode
put 1900 into TempNow
put 1950 into Target
put `off` into RelayState
clear HeatingRequested
gosub to SetRelay
log `PROBE missing-relays-on=` cat RelayState

! 7. A wired room above target stays off (the ordinary case).
gosub to ResetRoomForProbe
reset R
append `r1` to R
set entry `relays` of Room to R
put `timed` into Mode
put 2000 into TempNow
put 1950 into Target
put `on` into RelayState
clear HeatingRequested
gosub to SetRelay
log `PROBE above-target-on=` cat RelayState
if HeatingRequested put `yes` into S else put `no` into S
log `PROBE above-target-request=` cat S

! 8. An unlinked wired room is still driven by mode, not temperature.
gosub to ResetRoomForProbe
reset R
append `r1` to R
set entry `relays` of Room to R
set entry `linked` of Room to `no`
put `on` into Mode
put 2000 into TempNow
put 1950 into Target
put `off` into RelayState
clear HeatingRequested
gosub to SetRelay
log `PROBE unlinked-on=` cat RelayState

! 9. A prior warn status still forces off on a wired room.
gosub to ResetRoomForProbe
reset R
append `r1` to R
set entry `relays` of Room to R
set entry `status` of Room to `warn`
put `timed` into Mode
put 1900 into TempNow
put 1950 into Target
put `off` into RelayState
clear HeatingRequested
gosub to SetRelay
log `PROBE warn-on=` cat RelayState

! 10. A TRV room above its target is off, demand and all.
gosub to ResetRoomForProbe
reset R
set entry `relays` of Room to R
set entry `trv` of Room to `T1`
put `timed` into Mode
put 2000 into TempNow
put 1950 into Target
put `on` into RelayState
clear HeatingRequested
gosub to SetRelay
log `PROBE trv-above-on=` cat RelayState
if HeatingRequested put `yes` into S else put `no` into S
log `PROBE trv-above-request=` cat S

! 11. Period-start grace: a stale reading with a last known value heats in
!     the first 30 minutes of a period, even though status already says warn.
gosub to ResetRoomForProbe
reset R
append `r1` to R
set entry `relays` of Room to R
set entry `status` of Room to `warn`
set entry `temperature` of Room to 1950
put `timed` into Mode
put empty into TempNow
put 2000 into Target
put `off` into RelayState
set PeriodGrace
put 1950 into GraceTemp
clear HeatingRequested
gosub to SetRelay
log `PROBE grace-on=` cat RelayState
if HeatingRequested put `yes` into S else put `no` into S
log `PROBE grace-request=` cat S

! 12. The grace also outlives a fail status, which a long silence produces.
gosub to ResetRoomForProbe
reset R
append `r1` to R
set entry `relays` of Room to R
set entry `status` of Room to `fail`
set entry `temperature` of Room to 1950
put `timed` into Mode
put empty into TempNow
put 2000 into Target
put `off` into RelayState
set PeriodGrace
put 1950 into GraceTemp
clear HeatingRequested
gosub to SetRelay
log `PROBE grace-fail-on=` cat RelayState

! 13. The grace does not invent a reading: no last known value, no heat.
gosub to ResetRoomForProbe
reset R
append `r1` to R
set entry `relays` of Room to R
set entry `status` of Room to `warn`
put `timed` into Mode
put empty into TempNow
put 2000 into Target
put `off` into RelayState
set PeriodGrace
put empty into GraceTemp
clear HeatingRequested
gosub to SetRelay
log `PROBE grace-noreading-on=` cat RelayState

! 14. Once the 30-minute window closes, the ordinary staleness rule returns.
gosub to ResetRoomForProbe
reset R
append `r1` to R
set entry `relays` of Room to R
set entry `status` of Room to `warn`
set entry `temperature` of Room to 1950
put `timed` into Mode
put empty into TempNow
put 2000 into Target
put `off` into RelayState
clear PeriodGrace
put empty into GraceTemp
clear HeatingRequested
gosub to SetRelay
log `PROBE grace-expired-on=` cat RelayState

! 15. The grace decides on the last known value like any other reading, so a
!     room that was already above target stays off.
gosub to ResetRoomForProbe
reset R
append `r1` to R
set entry `relays` of Room to R
set entry `status` of Room to `warn`
set entry `temperature` of Room to 2050
put `timed` into Mode
put empty into TempNow
put 2000 into Target
put `on` into RelayState
set PeriodGrace
put 2050 into GraceTemp
clear HeatingRequested
gosub to SetRelay
log `PROBE grace-above-on=` cat RelayState

stop

ResetRoomForProbe:
    reset Room
    set entry `linked` of Room to `yes`
    set entry `status` of Room to `good`
    put 0 into PeriodActive
    put empty into PriorStatus
    put empty into BoostTemp
    put empty into S
    put empty into TempNow
    put empty into TempDecision
    clear PeriodGrace
    put empty into GraceTemp
    clear StaleGrace
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
    routine = extract_routine(source, "SetRelay")
    converter = extract_routine(source, "ConvertTempToInt")
    return "\n".join([
        "info `setrelay probe`",
        "",
        "script SetRelayProbe",
        "",
        DECLARATIONS.strip(),
        "",
        DRIVER.strip(),
        "",
        routine,
        "",
        converter,
        "",
        "! SetRelay falls through to RoomStatus in the controller by design.",
        "RoomStatus:",
        "    return",
        "",
        "script end",
        "",
    ])


def run_probe():
    binary = os.environ.get("ALLSPEAK", "allspeak")
    if not shutil.which(binary.split()[0]):
        raise unittest.SkipTest(f"{binary} not found — install AllSpeak to run this test")
    with tempfile.TemporaryDirectory() as tmp:
        probe = pathlib.Path(tmp) / "setrelay-probe.allspeak"
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


class SetRelayDecision(unittest.TestCase):
    """A room's demand follows its actuator; temperature alone is not enough."""

    @classmethod
    def setUpClass(cls):
        cls.v = run_probe()

    def test_a_relay_room_below_target_calls(self):
        self.assertEqual(self.v["relays-on"], "on")
        self.assertEqual(self.v["relays-request"], "yes")

    def test_no_actuator_never_calls(self):
        self.assertEqual(self.v["unwired-on"], "off",
                         "a room with no relay and no TRV demanded heat")
        self.assertEqual(self.v["unwired-request"], "no",
                         "a room with no actuator fired the demand relay")

    def test_a_trv_counts_as_an_actuator(self):
        self.assertEqual(self.v["trv-on"], "on")
        self.assertEqual(self.v["trv-request"], "yes")

    def test_on_mode_does_not_override_a_missing_actuator(self):
        self.assertEqual(self.v["unwired-onmode"], "off")
        self.assertEqual(self.v["unwired-onmode-request"], "no")

    def test_boost_does_not_override_a_missing_actuator(self):
        # Boost deliberately heats with no reading; it must not invent a radiator.
        self.assertEqual(self.v["unwired-boost"], "off")
        self.assertEqual(self.v["unwired-boost-request"], "no")

    def test_a_missing_relays_entry_is_not_an_actuator(self):
        self.assertEqual(self.v["missing-relays-on"], "off")

    def test_a_wired_room_above_target_is_off(self):
        self.assertEqual(self.v["above-target-on"], "off")
        self.assertEqual(self.v["above-target-request"], "no")

    def test_unlinked_wired_rooms_still_follow_mode(self):
        self.assertEqual(self.v["unlinked-on"], "on")

    def test_a_warn_status_still_forces_off(self):
        self.assertEqual(self.v["warn-on"], "off")

    def test_a_trv_room_above_target_is_off(self):
        self.assertEqual(self.v["trv-above-on"], "off")
        self.assertEqual(self.v["trv-above-request"], "no")

    def test_period_start_grace_heats_on_the_last_known_reading(self):
        self.assertEqual(self.v["grace-on"], "on")
        self.assertEqual(self.v["grace-request"], "yes")

    def test_the_grace_outlives_the_status_it_would_otherwise_trigger(self):
        # A sensor silent for over an hour is `fail`; the 30-minute window is
        # the bound, not the status, or the grace could never run at all.
        self.assertEqual(self.v["grace-fail-on"], "on")

    def test_the_grace_without_a_last_reading_does_not_heat(self):
        self.assertEqual(self.v["grace-noreading-on"], "off")

    def test_an_expired_grace_restores_the_staleness_rule(self):
        self.assertEqual(self.v["grace-expired-on"], "off")

    def test_the_grace_still_respects_the_last_reading_against_target(self):
        self.assertEqual(self.v["grace-above-on"], "off")


if __name__ == "__main__":
    unittest.main(verbosity=2)
