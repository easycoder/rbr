#!/usr/bin/env python3
"""
commit_roundtrip_test.py - unit tests for the split between the controller's
working room array and the profile state it is built from.

Run directly:  python3 tests/unit/commit_roundtrip_test.py
or as part of: tests/unit/run-unit-tests.sh

Why this exists. The shared room list stores a room's schedule state once per
profile, keyed by name, and the controller works on a materialised copy. Two
aliasing facts make that split delicate, and both were learned the hard way on
the live system (see DIFF.md):

  * `append A to L` COPIES, so a working room is not the stored record — a
    change made to it is lost unless CommitRooms writes it back;
  * `put entry K of D into V` ALIASES, so building the working record from the
    stored one leaks identity (relays, sensors, readings) into the plan.

Missing the first made Advance, On and Off revert a second after the tap;
missing the second made the page ship relays and readings back inside every
profile. Neither is visible by reading the map — you have to change something
and look again — so this test does exactly that, on the controller's own
routines, extracted from controller.allspeak at run time rather than mirrored.

The routines are extracted, not copied, so the test always exercises the code
that ships. If a routine stops being found the test fails loudly, which is the
first sign the convention it relies on (a `Label:` at column 0, its doc block
starting with `!! `) has changed.
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

# The routines that cross the boundary between the working array and the stored
# profile. UpdateRooms is here because it is the write-back path a UI handler
# uses (`set item RoomIndex of Rooms to Room` then commit).
ROUTINES = ("MaterialiseRooms", "CommitRooms", "UpdateRooms")

FIXTURE = {
    "rooms": [
        {"name": "Kitchen", "relays": ["k1"], "sensor": "kt", "linked": "yes",
         "temperature": 2000, "status": "good", "relay": "off"},
        {"name": "Sunroom", "relays": ["s1"], "sensor": "st", "linked": "yes",
         "temperature": 2100, "status": "good", "relay": "off"},
    ],
    "profiles": [
        {"name": "Weekend", "rooms": {
            "Kitchen": {"mode": "off", "target": 12, "periods": [], "advance": "-"},
            "Sunroom": {"mode": "timed", "target": 23, "advance": "-", "until": 123,
                        "periods": [{"on": "18:00", "off": "23:00", "temp": "23.0"}]},
        }},
    ],
    "profile": 0,
}

DECLARATIONS = """\
dictionary Map
list Profiles
dictionary Profile
list Rooms
dictionary Room
variable RoomCount
variable SelectedProfile
variable MaterialisedProfile
dictionary MRTemp
variable MRText
dictionary MRStates
list MRIdentity
dictionary MRRoom
dictionary MRState
variable MRIdx
variable MRName
list CRIdentity
dictionary CRIndex
dictionary CRRoom
dictionary CRTarget
dictionary CRCopy
dictionary CRProfile
dictionary CRStates
dictionary CRState
variable CRStateIdx
variable CRIdx
variable CRId
variable CRName
variable CRName0
variable CRCopyText
variable RoomIndex
variable RoomName
dictionary Fixture
variable S
"""

DRIVER = """\
put json Fixture into Map
put entry `profiles` of Map into Profiles
put entry `profile` of Map into SelectedProfile

! Materialise as ProcessAllRooms does, then do what a UI handler does: change
! the working record and write it back through UpdateRooms.
gosub to MaterialiseRooms
put 0 into RoomIndex
put item RoomIndex of Rooms into Room
set entry `mode` of Room to `on`
set entry `advance` of Room to `A`
gosub to UpdateRooms

! Then the next ProcessAllRooms: the change must still be there.
gosub to MaterialiseRooms
put item 0 of Rooms into Room
put entry `mode` of Room into S
log `PROBE working-mode=` cat S
put entry `advance` of Room into S
log `PROBE working-advance=` cat S

! And it must be in the profile, which is what the page reads.
put item SelectedProfile of Profiles into Profile
put entry `rooms` of Profile into MRStates
put entry `Kitchen` of MRStates into MRState
put entry `mode` of MRState into S
log `PROBE state-mode=` cat S
put entry `advance` of MRState into S
log `PROBE state-advance=` cat S

! The plan must not have absorbed identity: a page echoes this back on save.
if MRState has entry `name` put `yes` into S else put `no` into S
log `PROBE state-has-name=` cat S
if MRState has entry `relays` put `yes` into S else put `no` into S
log `PROBE state-has-relays=` cat S
if MRState has entry `sensor` put `yes` into S else put `no` into S
log `PROBE state-has-sensor=` cat S
if MRState has entry `linked` put `yes` into S else put `no` into S
log `PROBE state-has-linked=` cat S
if MRState has entry `temperature` put `yes` into S else put `no` into S
log `PROBE state-has-temperature=` cat S
if MRState has entry `status` put `yes` into S else put `no` into S
log `PROBE state-has-status=` cat S

! A field a handler deletes must stay deleted, not come back from the store.
put 1 into RoomIndex
put item RoomIndex of Rooms into Room
delete entry `until` of Room
gosub to UpdateRooms
gosub to MaterialiseRooms
put item SelectedProfile of Profiles into Profile
put entry `rooms` of Profile into MRStates
put entry `Sunroom` of MRStates into MRState
if MRState has entry `until` put `yes` into S else put `no` into S
log `PROBE state-sunroom-has-until=` cat S
put entry `mode` of MRState into S
log `PROBE state-sunroom-mode=` cat S
stop
"""


def extract_routines(source, labels):
    """Return the named labels and their bodies, verbatim, from controller source."""
    lines = source.split("\n")
    out = []
    for label in labels:
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
        out.append("\n".join(lines[start:end]).rstrip())
    return "\n".join(out)


def build_probe():
    source = CONTROLLER.read_text(encoding="utf-8")
    routines = extract_routines(source, ROUTINES)
    return "\n".join([
        "info `commit round-trip probe`",
        "",
        "script CommitProbe",
        "",
        DECLARATIONS.strip(),
        "",
        "put `" + json.dumps(FIXTURE).replace("`", "'") + "` into Fixture",
        "",
        DRIVER.strip(),
        "",
        routines,
        "",
        "script end",
        "",
    ])


def run_probe():
    binary = os.environ.get("ALLSPEAK", "allspeak")
    if not shutil.which(binary.split()[0]):
        raise unittest.SkipTest(f"{binary} not found — install AllSpeak to run this test")
    with tempfile.TemporaryDirectory() as tmp:
        probe = pathlib.Path(tmp) / "commit-probe.allspeak"
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


class CommitRoundTrip(unittest.TestCase):
    """The working array and the profile state must stay in step, both ways."""

    @classmethod
    def setUpClass(cls):
        cls.v = run_probe()

    def test_a_state_change_survives_the_next_materialise(self):
        # The live symptom: Advance/On/Off applied, then reverted a second later.
        self.assertEqual(self.v["working-mode"], "on",
                         "the working room lost the change at the next materialise")
        self.assertEqual(self.v["working-advance"], "A",
                         "the working room lost the advance at the next materialise")

    def test_the_change_reaches_the_profile_the_page_reads(self):
        self.assertEqual(self.v["state-mode"], "on",
                         "the profile state was never committed, so the page shows the old mode")
        self.assertEqual(self.v["state-advance"], "A",
                         "the profile state was never committed, so the page shows the old advance")

    def test_the_plan_does_not_absorb_identity(self):
        # A page echoes the profiles back on save, so a leak here lands in the map.
        for field in ("name", "relays", "sensor", "linked", "temperature", "status"):
            self.assertEqual(self.v[f"state-has-{field}"], "no",
                             f"'{field}' leaked into the profile state")

    def test_a_deletion_stays_deleted(self):
        # Replacing the state entry wholesale, rather than merging into it, is
        # what lets a handler remove a field (the boost pair on leaving boost).
        self.assertEqual(self.v["state-sunroom-has-until"], "no",
                         "'until' came back from the store after being deleted")
        self.assertEqual(self.v["state-sunroom-mode"], "timed",
                         "the untouched room's state changed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
