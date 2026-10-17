#!/usr/bin/env python3
"""
identity_override_test.py - unit tests for what happens to a room's one-off
override when the room is renamed or removed.

Run directly:  python3 tests/unit/identity_override_test.py
or as part of: tests/unit/run-unit-tests.sh

`Map.overrides` is keyed by room name, deliberately: an override has to apply
whichever profile the calendar picks, so it cannot live inside a profile. That
made it the one place a rename could strand data — the armed "start at 08:30
tomorrow" would stay under a name that no longer exists, doing nothing, and
would then apply to any later room that took the old name.

MergeIdentityRooms is the only place that sees the room list either side of an
update, so it carries the entry across a rename and drops it with a deletion.
A rename is recognised by its wiring — the editor changes the label and nothing
else, so the same thermometer and the same relays appearing under a new name is
one room.

The routines are extracted from controller.allspeak at run time, not mirrored,
so this always tests the code that ships.
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
ROUTINES = ("MergeIdentityRooms", "MoveRoomOverrides")

FIXTURE = {
    "rooms": [
        {"name": "Kitchen", "relays": ["k1", "k2"], "sensor": "kt", "linked": "yes"},
        {"name": "Sunroom", "relays": ["s1"], "sensor": "st", "linked": "yes"},
        {"name": "Hall", "relays": ["h1"], "sensor": "ht", "linked": "yes"},
    ],
    "profiles": [{"name": "Weekend", "rooms": {}}],
    "profile": 0,
    "overrides": {
        "Kitchen": {"kind": "start", "date": "2026-10-18", "on": "08:30", "was": "06:30"},
        "Sunroom": {"kind": "skip", "date": "2026-10-18", "at": 1},
    },
}

DECLARATIONS = """\
dictionary Map
list URList
list MIRCurrent
variable FixtureText
variable RenameText
variable DeleteText
variable AddText
dictionary MIRByName
dictionary MIRSeen
dictionary MIRAdded
dictionary MIRRoom
dictionary MIRIn
dictionary MIRNew
dictionary MIRCopy
list MIRBuilt
dictionary OVSet
dictionary OVOld
dictionary OVNew
list OVNames
list OVInNames
list OVOldRelays
list OVNewRelays
variable OVI
variable OVJ
variable OVName
variable OVNewName
variable OVCandidate
variable OVSensor
variable OVOldRelaysText
variable OVNewRelaysText
variable MIRI
variable MIRName
variable MIRCopyText
variable MapHasChanged
variable S
"""

DRIVER = """
! Case 1: Kitchen renamed to Cooking, wiring untouched. The override goes with it.
reset Map
put json FixtureText into Map
put json RenameText into URList
gosub to MergeIdentityRooms
put entry `overrides` of Map into OVSet
if OVSet has entry `Kitchen` put `yes` into S else put `no` into S
log `PROBE rename-old=` cat S
if OVSet has entry `Cooking` put `yes` into S else put `no` into S
log `PROBE rename-new=` cat S
if OVSet has entry `Sunroom` put `yes` into S else put `no` into S
log `PROBE rename-kept-others=` cat S
put entry `overrides` of Map into OVSet
reset OVOld
put `-` into S
if OVSet has entry `Cooking` put entry `Cooking` of OVSet into OVOld
if OVOld has entry `on` put entry `on` of OVOld into S
log `PROBE rename-entry-on=` cat S

! Case 2: Sunroom deleted. Its override goes with it.
reset Map
put json FixtureText into Map
put json DeleteText into URList
gosub to MergeIdentityRooms
put entry `overrides` of Map into OVSet
if OVSet has entry `Sunroom` put `yes` into S else put `no` into S
log `PROBE delete-sunroom=` cat S
if OVSet has entry `Kitchen` put `yes` into S else put `no` into S
log `PROBE delete-kitchen=` cat S

! Case 3: an unrelated room added; nothing moves.
reset Map
put json FixtureText into Map
put json AddText into URList
gosub to MergeIdentityRooms
put entry `overrides` of Map into OVSet
if OVSet has entry `Kitchen` put `yes` into S else put `no` into S
log `PROBE add-kitchen=` cat S
if OVSet has entry `Sunroom` put `yes` into S else put `no` into S
log `PROBE add-sunroom=` cat S
if OVSet has entry `Study` put `yes` into S else put `no` into S
log `PROBE add-study=` cat S
stop
"""


def extract_routines(source, labels):
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


def incoming(rooms):
    """An identity list as the page sends it: identity fields only."""
    return [{k: r[k] for k in ("name", "relays", "sensor", "linked")} for r in rooms]


def build_probe():
    source = CONTROLLER.read_text(encoding="utf-8")
    routines = extract_routines(source, ROUTINES)
    rooms = FIXTURE["rooms"]
    renamed = [dict(rooms[0], name="Cooking"), rooms[1], rooms[2]]
    deleted = [rooms[0], rooms[2]]
    added = rooms + [{"name": "Study", "relays": ["y1"], "sensor": "yt", "linked": "yes"}]

    def lit(obj):
        return "`" + json.dumps(obj).replace("`", "'") + "`"

    return "\n".join([
        "info `identity override probe`",
        "",
        "script IdentityProbe",
        "",
        DECLARATIONS.strip(),
        "",
        f"put {lit(FIXTURE)} into FixtureText",
        f"put {lit(incoming(renamed))} into RenameText",
        f"put {lit(incoming(deleted))} into DeleteText",
        f"put {lit(incoming(added))} into AddText",
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
        probe = pathlib.Path(tmp) / "identity-probe.allspeak"
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


class RoomOverrides(unittest.TestCase):
    """A one-off override belongs to the room, not to the label."""

    @classmethod
    def setUpClass(cls):
        cls.v = run_probe()

    def test_a_rename_carries_the_override(self):
        self.assertEqual(self.v["rename-new"], "yes",
                         "the override did not follow the room to its new name")
        self.assertEqual(self.v["rename-old"], "no",
                         "the override was left under the old name")
        self.assertEqual(self.v["rename-entry-on"], "08:30",
                         "the override moved but its contents did not")

    def test_a_rename_leaves_other_rooms_alone(self):
        self.assertEqual(self.v["rename-kept-others"], "yes",
                         "another room's override was disturbed by the rename")

    def test_a_deletion_drops_the_override(self):
        # Otherwise it would apply to any later room that took the name.
        self.assertEqual(self.v["delete-sunroom"], "no",
                         "the deleted room's override was left armed")
        self.assertEqual(self.v["delete-kitchen"], "yes",
                         "an unrelated room's override was dropped")

    def test_adding_a_room_disturbs_nothing(self):
        self.assertEqual(self.v["add-kitchen"], "yes")
        self.assertEqual(self.v["add-sunroom"], "yes")
        self.assertEqual(self.v["add-study"], "no",
                         "a new room inherited somebody else's override")


if __name__ == "__main__":
    unittest.main(verbosity=2)
