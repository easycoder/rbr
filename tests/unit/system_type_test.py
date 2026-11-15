#!/usr/bin/env python3
"""
system_type_test.py - the System sheet's heating type survives a Save.

Run directly:  python3 tests/unit/system_type_test.py
or as part of: tests/unit/run-unit-tests.sh

The sheet sends `systemType` (`Boiler` or `Heat Pump`) in its `System Name`
request, and `Map.systemType` is what the next map carries back to it. For as
long as the field has existed the controller stored the name and the On cap and
silently dropped the heating type, so choosing Heat Pump looked saved and came
back as Boiler (reported 2026-11-15).

ApplySystemName and NormaliseSystemType are extracted from controller.allspeak
at run time, so the test exercises the code that ships. The cases pin the two
labels, the case and spelling aliases, the refusal of anything that is not a
type, the optional field, the missing-name path (which must not touch the map)
and the On cap that shares the same request.
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
dictionary Message
variable Value
variable OnMax
variable TypeText
variable SystemTypeOut
variable SystemNameApplied
variable T
"""

DRIVER = """\
! 1. The sheet's own label is stored, and the request counts as applied.
reset Map
reset Message
set entry `name` of Message to `My Home`
set entry `systemType` of Message to `Heat Pump`
gosub to ApplySystemName
log `PROBE applied=` cat SystemNameApplied
put entry `name` of Map into T
log `PROBE name=` cat T
put entry `systemType` of Map into T
log `PROBE heat-pump=` cat T

! 2. A lower-case label is accepted and canonicalised.
reset Map
reset Message
set entry `name` of Message to `My Home`
set entry `systemType` of Message to `boiler`
gosub to ApplySystemName
put entry `systemType` of Map into T
log `PROBE lower-boiler=` cat T

! 3. The browser-ism `heatpump` works too.
reset Map
reset Message
set entry `name` of Message to `My Home`
set entry `systemType` of Message to `heatpump`
gosub to ApplySystemName
put entry `systemType` of Map into T
log `PROBE heatpump=` cat T

! 4. A value that is not a type is refused, not written.
reset Map
set entry `systemType` of Map to `Boiler`
set entry `name` of Map to `Old Name`
reset Message
set entry `name` of Message to `New Name`
set entry `systemType` of Message to `electric`
gosub to ApplySystemName
put entry `systemType` of Map into T
log `PROBE junk-type=` cat T
put entry `name` of Map into T
log `PROBE junk-name=` cat T

! 5. The field is optional: a request carrying only a name leaves the type be.
reset Map
set entry `systemType` of Map to `Heat Pump`
reset Message
set entry `name` of Message to `New Name`
gosub to ApplySystemName
put entry `systemType` of Map into T
log `PROBE absent-type=` cat T
put entry `name` of Map into T
log `PROBE absent-name=` cat T

! 6. No name at all: nothing is applied, so the caller must not broadcast.
reset Map
set entry `name` of Map to `Old Name`
set entry `systemType` of Map to `Boiler`
reset Message
set entry `systemType` of Message to `Heat Pump`
gosub to ApplySystemName
log `PROBE no-name-applied=` cat SystemNameApplied
put entry `name` of Map into T
log `PROBE no-name-name=` cat T
put entry `systemType` of Map into T
log `PROBE no-name-type=` cat T

! 7. The On cap still rides in the same request, in both forms.
reset Map
reset Message
set entry `name` of Message to `My Home`
set entry `systemType` of Message to `Heat Pump`
set entry `onmax` of Message to `6`
gosub to ApplySystemName
put entry `onmax` of Map into T
log `PROBE onmax-hours=` cat T
set entry `onmax` of Message to `always`
gosub to ApplySystemName
put entry `onmax` of Map into T
log `PROBE onmax-always=` cat T
put entry `systemType` of Map into T
log `PROBE onmax-keeps-type=` cat T

! 8. A legacy `name` field with no `System Name` field is still a name.
reset Map
reset Message
set entry `name` of Message to `Legacy Name`
gosub to ApplySystemName
put entry `name` of Map into T
log `PROBE legacy-name=` cat T
stop
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
        "info `system type probe`",
        "",
        "script SystemTypeProbe",
        "",
        DECLARATIONS.strip(),
        "",
        DRIVER.strip(),
        "",
    ]
    for label in ("ApplySystemName", "NormaliseSystemType"):
        parts.append(extract_routine(source, label))
        parts.append("")
    parts.extend(["script end", ""])
    return "\n".join(parts)


def run_probe():
    binary = os.environ.get("ALLSPEAK", "allspeak")
    if not shutil.which(binary.split()[0]):
        raise unittest.SkipTest(f"{binary} not found — install AllSpeak to run this test")
    with tempfile.TemporaryDirectory() as tmp:
        probe = pathlib.Path(tmp) / "system-type-probe.allspeak"
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


class SystemType(unittest.TestCase):
    """The heating type survives a Save, because the controller stores it."""

    @classmethod
    def setUpClass(cls):
        cls.v = run_probe()

    def test_heat_pump_is_stored(self):
        self.assertEqual(self.v["heat-pump"], "Heat Pump")

    def test_the_name_is_stored_alongside_it(self):
        self.assertEqual(self.v["name"], "My Home")

    def test_a_request_with_a_name_counts_as_applied(self):
        self.assertTrue(truthy(self.v["applied"]))

    def test_a_lower_case_label_is_accepted(self):
        self.assertEqual(self.v["lower-boiler"], "Boiler")

    def test_the_heatpump_spelling_is_accepted(self):
        self.assertEqual(self.v["heatpump"], "Heat Pump")

    def test_a_value_that_is_not_a_type_is_refused(self):
        self.assertEqual(self.v["junk-type"], "Boiler")

    def test_a_refused_type_does_not_stop_the_rename(self):
        self.assertEqual(self.v["junk-name"], "New Name")

    def test_the_type_is_optional(self):
        self.assertEqual(self.v["absent-type"], "Heat Pump")
        self.assertEqual(self.v["absent-name"], "New Name")

    def test_a_request_without_a_name_applies_nothing(self):
        self.assertFalse(truthy(self.v["no-name-applied"]))
        self.assertEqual(self.v["no-name-name"], "Old Name")
        self.assertEqual(self.v["no-name-type"], "Boiler")

    def test_the_on_cap_still_rides_in_the_same_request(self):
        self.assertEqual(self.v["onmax-hours"], "6")
        self.assertEqual(self.v["onmax-always"], "always")

    def test_a_later_cap_request_keeps_the_stored_type(self):
        self.assertEqual(self.v["onmax-keeps-type"], "Heat Pump")

    def test_a_legacy_name_field_still_renames(self):
        self.assertEqual(self.v["legacy-name"], "Legacy Name")


if __name__ == "__main__":
    unittest.main(verbosity=2)
