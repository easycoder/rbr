#!/usr/bin/env python3
"""Check the Show breakpoint: fold the map, pause at the marker, step once.

The runner is driven with a stub page driver, so no browser or broker is
needed. The events and the run snapshot are the assertions.

    python3 tools/rbr-studio/tests/show_check.py
"""

import copy
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

STUDIO = pathlib.Path(__file__).resolve().parent.parent
REPO = STUDIO.parent.parent
sys.path.insert(0, str(STUDIO))

from scenario_runner import engine  # noqa: E402


class Capture:
    def __init__(self):
        self.events = []

    def emit(self, event, **fields):
        self.events.append({"event": event, **fields})


class StubPage:
    def evaluate(self, script, value):
        return None


class StubDriver:
    instances = []

    def __init__(self, prepared, repo, headless, on_console=None, speed=0, view=False):
        self.prepared = prepared
        self.page = StubPage()
        self.page_errors = []
        self.console_lines = []
        self.view_url = None
        self.browser = object()
        self.maps = []
        self.raws = []
        self.advances = []
        self.current_step = None
        StubDriver.instances.append(self)

    def start(self):
        # The real driver pushes the base map during start().
        self.maps.append(copy.deepcopy(self.prepared.base_map))

    def advance_to(self, when, speed=None):
        self.advances.append((when, speed))

    def push_map(self, base_map):
        self.maps.append(copy.deepcopy(base_map))

    def push_raw(self, text):
        self.raws.append(text)

    def screenshot(self, path):
        return None

    def messages(self):
        return []

    def stop(self, failure=None, trace_path=None):
        return None

    def assert_expect(self, expect, timeout):
        return None

    def wait_wire(self, request, match, not_match, timeout):
        return None

    def wait_for(self, wait, timeout):
        return None

    def connection(self, action, message=None):
        return None

    def tap(self, target, timeout):
        return None

    def select(self, target, value, timeout):
        return None

    def fill(self, target, value, timeout):
        return None

    def scroll(self, target, delta, timeout):
        return None


class CancelAfterStepCommands:
    """A cancel that arrives after the first step; the run should stop there."""

    def __init__(self):
        self.polls = 0

    def poll(self):
        self.polls += 1
        if self.polls == 2:
            return {"command": "cancel"}
        return None

    def next(self):
        return {"command": "eof"}


class StepOnceCommands:
    """A Step click during the run, then Run once the pause lands."""

    def __init__(self):
        self.polls = 0

    def poll(self):
        self.polls += 1
        if self.polls == 1:
            return {"command": "step"}
        return None

    def next(self):
        return {"command": "continue"}


class FakeCommands:
    def __init__(self, commands):
        self.commands = list(commands)

    def poll(self):
        return None

    def next(self):
        if self.commands:
            return {"command": self.commands.pop(0)}
        return {"command": "eof"}


def make_map():
    return {
        "name": "Test home",
        "profile": 0,
        "calendar": "off",
        "rooms": [
            {"name": "Bedroom 1", "temperature": None, "humidity": None,
             "battery": None, "relay": None, "status": None,
             "relaysTotal": None, "relaysFailed": None, "relayfails": [0],
             "linked": "yes", "relays": ["bedroom-rad"]},
            {"name": "Outside", "temperature": 800, "relays": [],
             "linked": "yes"},
        ],
        "profiles": [{
            "name": "Weekday",
            "rooms": {
                "Bedroom 1": {"mode": "off", "target": 15, "period": -1,
                              "advance": "-"},
                "Outside": {"mode": "off", "target": 0, "period": 0,
                            "advance": "-"},
            },
        }],
    }


def make_scenario():
    return {
        "schemaVersion": 1,
        "name": "Fold and pause",
        "clock": {"start": "2026-11-07T00:00:00+00:00",
                  "timeZone": "Europe/London"},
        "home": {"map": make_map(), "profile": "Weekday"},
        "rooms": {"Bedroom_1": "Bedroom 1"},
        "steps": [
            {"id": "s1", "at": "2026-11-07T01:00:00+00:00",
             "controller": {"room": "Bedroom 1",
                            "set": {"temperature": 2000, "humidity": 55,
                                    "battery": 90, "relay": "off",
                                    "status": "good", "relaysTotal": 1,
                                    "relaysFailed": 0}}},
            {"id": "s2", "at": "2026-11-07T02:00:00+00:00",
             "controller": {"room": "Bedroom 1",
                            "state": {"set": {"mode": "timed", "target": 21,
                                              "period": 0, "advance": "-"}}}},
            {"id": "s3", "at": "2026-11-07T03:00:00+00:00", "marker": True,
             "controller": {"room": "Bedroom 1",
                            "set": {"temperature": 2100}}},
            {"id": "s4", "at": "2026-11-07T04:00:00+00:00",
             "controller": {"room": "Bedroom 1", "set": {"relay": "on"}}},
            {"id": "s5", "at": "2026-11-07T05:00:00+00:00",
             "controller": {"room": "Bedroom 1", "set": {"relay": "off"}}},
        ],
    }


class FailingDriver(StubDriver):
    """A driver whose expectation always fails, for the failure report."""

    def assert_expect(self, expect, timeout):
        raise AssertionError("summary.title is not visible")


class ShowCheck(unittest.TestCase):
    def setUp(self):
        StubDriver.instances.clear()
        self._tmp = tempfile.TemporaryDirectory(prefix="rbr-show-")
        self.root = pathlib.Path(self._tmp.name)
        self.scenario = self.root / "scenario.json"
        self.scenario.write_text(json.dumps(make_scenario(), indent=2) + "\n",
                                 encoding="utf-8")
        self.capture = Capture()
        self.commands = FakeCommands(["step", "continue"])

    def tearDown(self):
        self._tmp.cleanup()

    def run_show(self):
        with mock.patch.object(engine, "PageDriver", StubDriver):
            return engine.run_scenario(
                self.scenario, REPO, headless=True, jsonl=True,
                events=self.capture, run_dir=self.root / "run", speed=120,
                fold_to_marker=True, pause_at_marker=True,
                commands=self.commands)

    def test_fold_skips_pre_breakpoint_steps_and_starts_initialised(self):
        self.assertEqual(self.run_show(), 0)
        driver = StubDriver.instances[0]

        self.assertEqual(driver.maps[0]["rooms"][0]["temperature"], 2000)
        self.assertEqual(driver.maps[0]["rooms"][0]["relay"], "off")
        self.assertEqual(driver.maps[0]["rooms"][0]["status"], "good")
        state = driver.maps[0]["profiles"][0]["rooms"]["Bedroom 1"]
        self.assertEqual(state["mode"], "timed")
        self.assertEqual(state["target"], 21)
        self.assertEqual(driver.advances[0][0].isoformat(),
                         "2026-11-07T03:00:00+00:00")

    def test_first_step_is_the_marker_and_pauses(self):
        self.assertEqual(self.run_show(), 0)
        started = [event for event in self.capture.events
                   if event["event"] == "step.started"]
        self.assertEqual([event["stepId"] for event in started],
                         ["s3", "s4", "s5"])
        paused = [event for event in self.capture.events
                  if event["event"] == "run.paused"]
        self.assertEqual([event["stepId"] for event in paused], ["s3", "s4"])
        self.assertEqual([event["nextStepId"] for event in paused], ["s4", "s5"])

    def test_run_snapshot_is_trimmed_and_baked(self):
        self.assertEqual(self.run_show(), 0)
        snapshot = json.loads((self.root / "run" / "scenario.json").read_text())
        self.assertEqual([step["id"] for step in snapshot["steps"]],
                         ["s3", "s4", "s5"])
        self.assertEqual(snapshot["clock"]["start"],
                         "2026-11-07T03:00:00+00:00")
        self.assertEqual(snapshot["home"]["map"]["rooms"][0]["temperature"], 2000)
        self.assertIn("skipped 2 pre-breakpoint", snapshot["description"])

    def test_step_uses_an_instant_clock_and_show_resumes_the_pace(self):
        self.assertEqual(self.run_show(), 0)
        driver = StubDriver.instances[0]
        self.assertEqual([speed for _, speed in driver.advances], [120, 0, 120])

    def test_continue_finishes_the_run(self):
        self.assertEqual(self.run_show(), 0)
        finished = [event for event in self.capture.events
                    if event["event"] == "run.finished"]
        self.assertEqual(len(finished), 1)
        self.assertEqual(finished[0]["status"], "passed")
        self.assertEqual(finished[0]["passed"], 3)

    def test_cancel_after_a_step_stops_the_run(self):
        commands = CancelAfterStepCommands()
        with mock.patch.object(engine, "PageDriver", StubDriver):
            code = engine.run_scenario(
                self.scenario, REPO, headless=True, jsonl=True,
                events=self.capture, run_dir=self.root / "cancel",
                commands=commands)
        self.assertEqual(code, 1)
        finished = [event for event in self.capture.events
                    if event["event"] == "run.finished"]
        self.assertEqual(finished[0]["status"], "cancelled")
        started = [event["stepId"] for event in self.capture.events
                   if event["event"] == "step.started"]
        self.assertEqual(started, ["s1"])
        passed = [event for event in self.capture.events
                  if event["event"] == "step.finished" and event["status"] == "passed"]
        self.assertEqual([event["stepId"] for event in passed], ["s1"])

    def test_step_during_a_run_pauses_at_the_current_step(self):
        commands = StepOnceCommands()
        with mock.patch.object(engine, "PageDriver", StubDriver):
            code = engine.run_scenario(
                self.scenario, REPO, headless=True, jsonl=True,
                events=self.capture, run_dir=self.root / "step-pause",
                commands=commands)
        self.assertEqual(code, 0)
        paused = [event for event in self.capture.events
                  if event["event"] == "run.paused"]
        self.assertEqual(len(paused), 1)
        self.assertEqual(paused[0]["stepId"], "s1")
        self.assertEqual(paused[0]["nextStepId"], "s2")
        self.assertEqual(paused[0]["reason"], "step")

    def test_user_step_is_reported_but_not_executed(self):
        scenario = make_scenario()
        scenario["steps"].insert(3, {
            "id": "u1", "at": "2026-11-07T03:30:00+00:00",
            "user": {"action": "Operating Mode", "label": "Advance on",
                     "room": "Bedroom 1", "screen": "home",
                     "control": "advance", "gesture": "tap",
                     "advance": "A", "seq": 8038},
        })
        path = self.root / "user.json"
        path.write_text(json.dumps(scenario, indent=2) + "\n", encoding="utf-8")
        with mock.patch.object(engine, "PageDriver", StubDriver):
            code = engine.run_scenario(
                path, REPO, headless=True, jsonl=True,
                events=self.capture, run_dir=self.root / "user",
                speed=120, fold_to_marker=True, pause_at_marker=True,
                commands=self.commands)
        self.assertEqual(code, 0)
        started = [event for event in self.capture.events
                   if event["event"] == "step.started"]
        user = next(event for event in started if event["stepId"] == "u1")
        self.assertEqual(user["actor"], "user")
        passed = [event for event in self.capture.events
                  if event["event"] == "step.finished" and event["status"] == "passed"]
        self.assertIn("u1", [event["stepId"] for event in passed])
        self.assertEqual(StubDriver.instances[0].raws, [])

    def test_a_failed_step_reports_its_message_on_finish(self):
        failing = self.root / "failing.json"
        failing.write_text(json.dumps({
            "schemaVersion": 1,
            "name": "Failing",
            "clock": {"start": "2026-11-07T01:00:00Z", "timeZone": "UTC"},
            "home": {"map": make_map(), "profile": "Weekday"},
            "steps": [{"id": "f1", "at": "2026-11-07T01:00:00+00:00",
                       "expect": {"target": "summary.title", "visible": True}}],
        }, indent=2) + "\n", encoding="utf-8")
        with mock.patch.object(engine, "PageDriver", FailingDriver):
            code = engine.run_scenario(
                failing, REPO, headless=True, jsonl=True,
                events=self.capture, run_dir=self.root / "fail")
        self.assertEqual(code, 1)
        finished = [event for event in self.capture.events
                    if event["event"] == "run.finished"]
        self.assertEqual(len(finished), 1)
        self.assertEqual(finished[0]["status"], "failed")
        self.assertIn("summary.title", finished[0]["failure"]["message"])


if __name__ == "__main__":
    unittest.main()
