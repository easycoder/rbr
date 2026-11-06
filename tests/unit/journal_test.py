#!/usr/bin/env python3
"""
journal_test.py - integration test for the controller-side event journal.

Extracts the Journal* routines from controller.allspeak at run time (the way
setrelay_test.py extracts SetRelay), drives them with a small AllSpeak probe,
and checks the JSONL that eventlog.py writes: session/sensor/room/UI/plan
events, the PWA Source provenance, and batch ordering.

Run directly:  python3 tests/unit/journal_test.py
or as part of: tests/unit/run-unit-tests.sh
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
CONTROLLER = REPO / "controller.allspeak"
EVENTLOG = REPO / "eventlog.py"

DECLARATIONS = """
    script JournalProbe

    dictionary JournalEvent
    dictionary JournalData
    dictionary JournalDataCopy
    dictionary JournalProfileRec
    dictionary JournalMapCopy
    list JournalEvents
    dictionary JournalRooms
    dictionary JournalSensors
    variable JournalEnabled
    variable JournalRoot
    variable JournalType
    variable JournalBoot
    variable JournalSeq
    variable JournalBatchSeq
    variable JournalBatchPath
    variable JournalPending
    variable JournalRoomText
    variable JournalRoomHash
    variable JournalSensorText
    variable JournalSensorHash
    variable JournalSensorKey
    variable JournalDataText
    variable JournalMapText
    variable JournalProfileIdx
    variable JournalProfileName
    variable JournalProfileWas
    variable JournalRequestSeen
    variable JournalPlanChanged
    variable JournalPlanReason
    variable JournalRequestLast

    dictionary Map
    dictionary Profile
    dictionary Room
    dictionary Thermometer
    dictionary Thermometers
    dictionary Message
    list Profiles
    list Rooms
    variable SelectedProfile
    variable StartedVersion
    variable HeatlogRoot
    variable VolatilePrefix
    variable RoomName
    variable Sensor
    variable TempNow
    variable Simulate
    variable SenderName
    variable Action
    variable RequestState
    variable RequestName
"""

DRIVER = """
    set StartedVersion to `probe`
    set SelectedProfile to 0
    set JournalRequestLast to empty
    reset Profiles
    reset Profile
    set entry `name` of Profile to `Weekday`
    append Profile to Profiles
    reset Rooms
    reset Room
    set entry `name` of Room to `Kitchen`
    append Room to Rooms
    reset Map
    set entry `name` of Map to `Probe home`
    set entry `profile` of Map to 0
    set entry `profiles` of Map to Profiles
    set entry `rooms` of Map to Rooms
    put `{root}` into HeatlogRoot
    put `{volatile}/` into VolatilePrefix
    gosub to JournalStart

    set RoomName to `Kitchen`
    set Sensor to `Kitchen-thermometer`
    set TempNow to 1840
    set Simulate
    gosub to JournalSensor
    set TempNow to 1850
    gosub to JournalSensor
    gosub to JournalSensor

    reset Room
    set entry `name` of Room to `Kitchen`
    set entry `mode` of Room to `timed`
    set entry `target` of Room to 21
    set entry `period` of Room to 0
    set entry `advance` of Room to `-`
    set entry `relay` of Room to `off`
    set entry `status` of Room to `good`
    set entry `statusMessage` of Room to ``
    set entry `relayMessage` of Room to ``
    set entry `relayfails` of Room to `[]`
    gosub to JournalRoomState
    set entry `relay` of Room to `on`
    gosub to JournalRoomState
    gosub to JournalRoomState

    set SenderName to `client-1`
    set Action to `Operating Mode`
    reset Message
    set entry `Action` of Message to `Operating Mode`
    set entry `Room` of Message to `Kitchen`
    set entry `Mode` of Message to `on`
    reset JournalData
    set entry `screen` of JournalData to `home`
    set entry `control` of JournalData to `mode`
    set entry `gesture` of JournalData to `tap`
    set entry `room` of JournalData to `Kitchen`
    set entry `Source` of Message to JournalData
    gosub to JournalUIRequest

    set RequestName to `Boiler`
    set RequestState to `on`
    gosub to JournalRequestRelay
    set JournalPlanReason to `ui:Update Profiles`
    gosub to JournalPlanSnapshot
    gosub to JournalFlush
    gosub to JournalSessionStop
    stop
"""


def journal_routines():
    """The controller's Journal* block, verbatim, from its first doc block to EOF."""
    text = CONTROLLER.read_text(encoding="utf-8")
    marker = "!! Event journal start-up"
    if marker not in text:
        raise AssertionError("the controller has no event-journal block")
    return text[text.index(marker):]


class JournalProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.allspeak = shutil.which("allspeak")
        if not cls.allspeak:
            raise unittest.SkipTest("allspeak is not installed")

    def test_journal_writes_ordered_events_with_provenance(self):
        with tempfile.TemporaryDirectory(prefix="rbr-journal-test-") as tmp:
            root = pathlib.Path(tmp) / "events"
            volatile = pathlib.Path(tmp) / "volatile"
            volatile.mkdir()
            shutil.copy(EVENTLOG, pathlib.Path(tmp) / "eventlog.py")
            (pathlib.Path(tmp) / "journal-root").write_text(str(root) + "\n", encoding="utf-8")
            script = DECLARATIONS + DRIVER.format(root=root, volatile=volatile) + "\n" + journal_routines()
            path = pathlib.Path(tmp) / "journal-probe.allspeak"
            path.write_text(script, encoding="utf-8")
            result = subprocess.run(
                [self.allspeak, str(path)], cwd=tmp, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            files = list(root.glob("*/*/*.jsonl"))
            self.assertEqual(len(files), 1, files)
            events = [json.loads(line) for line in files[0].read_text(encoding="utf-8").splitlines()]
            types = [event["type"] for event in events]
            self.assertEqual(types[:2], ["session.start", "sensor.reading"], types)
            self.assertEqual(types.count("sensor.reading"), 2, types)
            self.assertEqual(types.count("room.state"), 2, types)
            self.assertIn("ui.request", types)
            self.assertIn("plan.snapshot", types)
            self.assertEqual(types[-1], "session.stop")
            self.assertEqual([event["seq"] for event in events], list(range(1, len(events) + 1)))

            request = next(event for event in events if event["type"] == "ui.request")
            self.assertEqual(request["data"]["source"]["screen"], "home")
            self.assertEqual(request["data"]["source"]["control"], "mode")
            self.assertEqual(request["data"]["source"]["gesture"], "tap")
            self.assertEqual(request["data"]["source"]["room"], "Kitchen")

            snapshot = next(event for event in events if event["type"] == "plan.snapshot")
            self.assertIn("mapHash", snapshot["data"])
            self.assertTrue((root / "maps" / f"{snapshot['data']['mapHash']}.json").is_file())


if __name__ == "__main__":
    unittest.main()
