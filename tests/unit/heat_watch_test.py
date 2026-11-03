#!/usr/bin/env python3
"""Tests for heatwatch.py — the no-temperature-rise watchdog.

The detector works from the same two files the running system already writes:
`map.json` (the plan, with the controller's persisted `period` and modes) and
`thermometers.json` (the fresh readings), plus the heating log when
`heatlog-root` is configured. These tests build those files in a temporary RBR
directory and drive `heatwatch.run()` with a fixed clock, so no service is
ever touched.
"""

import datetime
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import heatwatch  # noqa: E402


MONDAY = datetime.datetime(2026, 11, 2, 8, 0)
SATURDAY = datetime.datetime(2026, 11, 7, 8, 0)


def epoch(dt):
    return dt.timestamp()


def minute(dt):
    return int(dt.timestamp() // 60)


def timed_map(period=0, periods=None, target="21.0", relay=True):
    """A one-room map in the shared-room-list format."""
    if periods is None:
        periods = [{"on": "07:00", "off": "09:00", "temp": target}]
    room_state = {"mode": "timed", "period": period, "periods": periods}
    if target is not None:
        room_state["target"] = target
    identity = {"name": "Kitchen", "sensor": "Kitchen-thermometer", "linked": "yes"}
    if relay:
        identity["relays"] = ["Kitchen-radiator"]
    else:
        identity["relays"] = []
    return {
        "profiles": [{"name": "Weekday", "rooms": {"Kitchen": room_state}}],
        "profile": 0,
        "calendar": "off",
        "rooms": [identity],
    }


class Fixture:
    """A temporary controller directory holding map, readings and heat log."""

    def __init__(self, directory):
        self.rbr = Path(directory)
        self.state = self.rbr / "heat-watch-state.json"

    def write_map(self, data):
        (self.rbr / "map.json").write_text(json.dumps(data), encoding="utf-8")

    def write_thermometers(self, temp_c, now, sensor="Kitchen-thermometer", age_ms=60_000):
        data = {
            sensor: {
                "temp": int(round(temp_c * 100)),
                "ts": int(now * 1000) - age_ms,
            }
        }
        (self.rbr / "thermometers.json").write_text(json.dumps(data), encoding="utf-8")

    def write_bridge_temperatures(self, temp_c, now, sensor="Kitchen-thermometer", age_ms=60_000):
        data = {
            sensor: {
                "temp": int(round(temp_c * 100)),
                "ts": int(now * 1000) - age_ms,
            }
        }
        (self.rbr / "zigbee-temperatures.json").write_text(json.dumps(data), encoding="utf-8")

    def enable_heatlog(self, root=None):
        (self.rbr / "heatlog-root").write_text(str(root or self.rbr / "heating"), encoding="utf-8")

    def write_heatlog(self, rows, day=None):
        day = day or MONDAY.date()
        path = (
            self.rbr
            / "heating"
            / heatwatch.sanitise_room("Kitchen")
            / f"{day.year:04d}"
            / f"{day.month:02d}"
            / f"{day.day:02d}.csv"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(",".join(str(value) for value in row) + "\n")

    def write_state(self, data):
        self.state.write_text(json.dumps(data), encoding="utf-8")


class Quiet:
    """Run a callable with stdout captured, so test output stays readable."""

    def __enter__(self):
        self._buffer = io.StringIO()
        self._redirect = redirect_stdout(self._buffer)
        self._redirect.__enter__()
        return self

    def __exit__(self, *exc_info):
        self._redirect.__exit__(*exc_info)
        self.output = self._buffer.getvalue()


def no_restart():
    raise AssertionError("restart must not be called")


class TargetTests(unittest.TestCase):
    def test_timed_period_target_uses_the_persisted_period_index(self):
        room = {"mode": "timed", "period": 0, "periods": [
            {"on": "07:00", "off": "09:00", "temp": "21.0"},
        ]}
        self.assertEqual(heatwatch.scheduled_target(room, MONDAY), 21.0)

    def test_background_timed_room_outside_a_period_is_not_scheduled_on(self):
        room = {"mode": "timed", "period": -1, "periods": [
            {"on": "07:00", "off": "09:00", "temp": "21.0"},
        ]}
        self.assertIsNone(heatwatch.scheduled_target(room, MONDAY.replace(hour=10, minute=0)))

    def test_a_disabled_period_is_not_a_target(self):
        room = {"mode": "timed", "period": 0, "periods": [
            {"on": "07:00", "off": "09:00", "temp": "21.0", "enabled": False},
        ]}
        self.assertIsNone(heatwatch.scheduled_target(room, MONDAY))

    def test_background_map_with_a_running_natural_period_uses_the_schedule(self):
        room = {"mode": "timed", "period": -1, "periods": [
            {"on": "07:00", "off": "09:00", "temp": "21.0"},
        ]}
        self.assertEqual(heatwatch.scheduled_target(room, MONDAY), 21.0)

    def test_an_advance_in_background_is_not_overridden(self):
        room = {"mode": "timed", "period": -1, "advance": "A", "periods": [
            {"on": "07:00", "off": "09:00", "temp": "21.0"},
        ]}
        self.assertIsNone(heatwatch.scheduled_target(room, MONDAY))

    def test_a_one_off_override_in_background_is_not_overridden(self):
        room = {"mode": "timed", "period": -1, "periods": [
            {"on": "07:00", "off": "09:00", "temp": "21.0"},
        ]}
        self.assertIsNone(heatwatch.scheduled_target(room, MONDAY, override_active=True))

    def test_on_mode_uses_the_room_target(self):
        self.assertEqual(heatwatch.scheduled_target({"mode": "on", "target": "19.5"}, MONDAY), 19.5)

    def test_expired_boost_is_not_scheduled_on(self):
        room = {"mode": "boost", "target": "22.0", "until": int(epoch(MONDAY) * 1000) - 1}
        self.assertIsNone(heatwatch.scheduled_target(room, MONDAY))

    def test_period_containment_wraps_midnight(self):
        self.assertTrue(heatwatch.period_contains(23 * 60 + 30, 22 * 60, 2 * 60))
        self.assertTrue(heatwatch.period_contains(60, 22 * 60, 2 * 60))
        self.assertFalse(heatwatch.period_contains(12 * 60, 22 * 60, 2 * 60))


class ProfileTests(unittest.TestCase):
    def test_calendar_selects_the_weekend_profile(self):
        map_data = {
            "profiles": [
                {"name": "Weekday", "rooms": {}},
                {"name": "Weekend", "rooms": {}},
            ],
            "profile": 0,
            "calendar": "on",
            "calendar-data": [
                {"day0-profile": "Weekday"},
                {"day1-profile": "Weekday"},
                {"day2-profile": "Weekday"},
                {"day3-profile": "Weekday"},
                {"day4-profile": "Weekday"},
                {"day5-profile": "Weekend"},
                {"day6-profile": "Weekend"},
            ],
        }
        self.assertEqual(heatwatch.active_profile(map_data, SATURDAY.weekday())["name"], "Weekend")

    def test_calendar_off_uses_the_selected_profile_index(self):
        map_data = {
            "profiles": [{"name": "A", "rooms": {}}, {"name": "B", "rooms": {}}],
            "profile": 1,
            "calendar": "off",
        }
        self.assertEqual(heatwatch.active_profile(map_data, MONDAY.weekday())["name"], "B")

    def test_profile_rooms_accepts_the_old_list_form(self):
        profile = {"rooms": [{"name": "Kitchen"}, {"name": "Hall"}]}
        self.assertEqual(sorted(heatwatch.profile_rooms(profile)), ["Hall", "Kitchen"])


class HeatlogTests(unittest.TestCase):
    def test_run_starts_at_the_earliest_consecutive_demand_row(self):
        rows = [
            (minute(MONDAY) - 90, 210, 190, "o"),
            (minute(MONDAY) - 60, 210, 190, "p"),
            (minute(MONDAY) - 30, 210, 190, "p"),
        ]
        run = heatwatch.heatlog_run(rows, minute(MONDAY))
        self.assertEqual(run.start_min, minute(MONDAY) - 60)
        self.assertEqual(run.baseline_tenths, 190)
        self.assertEqual(run.max_tenths, 190)

    def test_run_stops_at_an_off_row(self):
        rows = [
            (minute(MONDAY) - 90, 210, 190, "p"),
            (minute(MONDAY) - 60, 190, 190, "o"),
            (minute(MONDAY) - 30, 210, 190, "p"),
        ]
        run = heatwatch.heatlog_run(rows, minute(MONDAY))
        self.assertEqual(run.start_min, minute(MONDAY) - 30)

    def test_a_satisfied_room_is_not_a_demand_run(self):
        rows = [(minute(MONDAY) - 60, 210, 210, "p")]
        self.assertIsNone(heatwatch.heatlog_run(rows, minute(MONDAY)))

    def test_previous_day_is_read_as_well(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Fixture(directory)
            yesterday = MONDAY.date() - datetime.timedelta(days=1)
            fixture.write_heatlog([(minute(MONDAY) - 60, 210, 190, "p")], day=yesterday)
            fixture.write_heatlog([(minute(MONDAY) - 10, 210, 191, "p")], day=MONDAY.date())
            rows = heatwatch.read_heatlog_rows(fixture.rbr / "heating", "Kitchen", MONDAY)
            self.assertEqual([row[2] for row in rows], [190, 191])


class RunTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.fixture = Fixture(self._tmp.name)
        self.restarts = []

    def restart(self):
        self.restarts.append(True)
        return []

    def run_watch(self, now=MONDAY, dry_run=False):
        with Quiet():
            return heatwatch.run(
                self.fixture.rbr,
                now=epoch(now),
                dry_run=dry_run,
                restart=self.restart,
            )

    def test_a_scheduled_room_with_no_rise_restarts_every_core_service(self):
        self.fixture.write_map(timed_map())
        self.fixture.write_thermometers(19.0, epoch(MONDAY))
        self.fixture.enable_heatlog()
        self.fixture.write_heatlog([
            (minute(MONDAY) - 60, 210, 190, "p"),
            (minute(MONDAY) - 30, 210, 190, "p"),
        ])

        outcome = self.run_watch()

        self.assertEqual(len(outcome.failures), 1)
        self.assertTrue(outcome.restarted)
        self.assertEqual(len(self.restarts), 1)
        state = json.loads(self.fixture.state.read_text(encoding="utf-8"))
        self.assertEqual(state["last_restart"], epoch(MONDAY))

    def test_a_rise_of_the_threshold_is_enough(self):
        self.fixture.write_map(timed_map())
        self.fixture.write_thermometers(19.2, epoch(MONDAY))
        self.fixture.enable_heatlog()
        self.fixture.write_heatlog([
            (minute(MONDAY) - 60, 210, 190, "p"),
            (minute(MONDAY) - 30, 210, 192, "p"),
        ])

        outcome = self.run_watch()

        self.assertEqual(outcome.failures, [])
        self.assertFalse(outcome.restarted)

    def test_a_stale_thermometer_is_ignored(self):
        self.fixture.write_map(timed_map())
        self.fixture.write_thermometers(19.0, epoch(MONDAY), age_ms=50 * 60 * 1000)
        self.fixture.enable_heatlog()
        self.fixture.write_heatlog([(minute(MONDAY) - 60, 210, 190, "p")])

        outcome = self.run_watch()

        self.assertEqual(outcome.failures, [])
        self.assertFalse(outcome.restarted)

    def test_the_bridge_reading_is_used_when_the_controller_file_is_stale(self):
        self.fixture.write_map(timed_map())
        self.fixture.write_thermometers(19.0, epoch(MONDAY), age_ms=50 * 60 * 1000)
        self.fixture.write_bridge_temperatures(19.0, epoch(MONDAY))
        self.fixture.enable_heatlog()
        self.fixture.write_heatlog([(minute(MONDAY) - 60, 210, 190, "p")])

        outcome = self.run_watch()

        self.assertEqual(len(outcome.failures), 1)
        self.assertTrue(outcome.restarted)

    def test_a_room_only_a_tenth_below_target_is_ignored(self):
        self.fixture.write_map(timed_map())
        self.fixture.write_thermometers(20.6, epoch(MONDAY))
        self.fixture.enable_heatlog()
        self.fixture.write_heatlog([(minute(MONDAY) - 60, 210, 206, "p")])

        outcome = self.run_watch()

        self.assertEqual(outcome.failures, [])
        self.assertFalse(outcome.restarted)

    def test_a_room_with_no_actuator_is_ignored(self):
        self.fixture.write_map(timed_map(relay=False))
        self.fixture.write_thermometers(19.0, epoch(MONDAY))
        self.fixture.enable_heatlog()
        self.fixture.write_heatlog([(minute(MONDAY) - 60, 210, 190, "p")])

        outcome = self.run_watch()

        self.assertEqual(outcome.failures, [])
        self.assertFalse(outcome.restarted)

    def test_a_controller_stuck_before_a_period_is_caught_by_the_natural_schedule(self):
        # The map still says background because the controller did not process
        # the 07:00 boundary; the heating log's last row is an off row for the
        # same reason. The schedule itself says the room should be warming.
        self.fixture.write_map(timed_map(period=-1))
        self.fixture.enable_heatlog()
        self.fixture.write_heatlog([(minute(MONDAY) - 90, 190, 190, "o")])

        first = MONDAY - datetime.timedelta(minutes=45)  # 07:15
        self.fixture.write_thermometers(19.0, epoch(first))
        self.assertEqual(self.run_watch(now=first).failures, [])

        second = first + datetime.timedelta(minutes=61)  # 08:16
        self.fixture.write_thermometers(19.0, epoch(second))
        outcome = self.run_watch(now=second)

        self.assertEqual(len(outcome.failures), 1)
        self.assertTrue(outcome.restarted)

    def test_the_cooldown_suppresses_a_second_restart(self):
        self.fixture.write_map(timed_map())
        self.fixture.write_thermometers(19.0, epoch(MONDAY))
        self.fixture.enable_heatlog()
        self.fixture.write_heatlog([(minute(MONDAY) - 60, 210, 190, "p")])
        self.fixture.write_state({"last_restart": epoch(MONDAY) - 600, "rooms": {}})

        outcome = self.run_watch()

        self.assertEqual(len(outcome.failures), 1)
        self.assertTrue(outcome.suppressed)
        self.assertFalse(outcome.restarted)
        self.assertEqual(self.restarts, [])

    def test_the_daily_restart_cap_stops_a_persistent_fault(self):
        self.fixture.write_map(timed_map())
        self.fixture.write_thermometers(19.0, epoch(MONDAY))
        self.fixture.enable_heatlog()
        self.fixture.write_heatlog([(minute(MONDAY) - 60, 210, 190, "p")])
        self.fixture.write_state({
            "restarts": [
                epoch(MONDAY) - 3600,
                epoch(MONDAY) - 7200,
                epoch(MONDAY) - 10800,
            ],
            "rooms": {},
        })

        outcome = self.run_watch()

        self.assertEqual(len(outcome.failures), 1)
        self.assertTrue(outcome.suppressed)
        self.assertFalse(outcome.restarted)
        self.assertEqual(self.restarts, [])

    def test_dry_run_changes_nothing(self):
        self.fixture.write_map(timed_map())
        self.fixture.write_thermometers(19.0, epoch(MONDAY))
        self.fixture.enable_heatlog()
        self.fixture.write_heatlog([(minute(MONDAY) - 60, 210, 190, "p")])

        outcome = self.run_watch(dry_run=True)

        self.assertEqual(len(outcome.failures), 1)
        self.assertFalse(outcome.restarted)
        self.assertEqual(self.restarts, [])
        self.assertFalse(self.fixture.state.exists())

    def test_without_heatlog_the_state_file_supplies_the_baseline(self):
        self.fixture.write_map(timed_map())
        later = MONDAY + datetime.timedelta(minutes=61)

        self.fixture.write_thermometers(19.0, epoch(MONDAY))
        first = self.run_watch()
        self.assertEqual(first.failures, [])

        self.fixture.write_thermometers(19.0, epoch(later))
        second = self.run_watch(now=later)

        self.assertEqual(len(second.failures), 1)
        self.assertTrue(second.restarted)

    def test_calendar_weekend_profile_is_used(self):
        map_data = timed_map()
        weekday_rooms = map_data["profiles"][0]["rooms"]
        map_data["profiles"].append({
            "name": "Weekend",
            "rooms": json.loads(json.dumps(weekday_rooms)),
        })
        map_data["calendar"] = "on"
        map_data["calendar-data"] = [
            {"day0-profile": "Weekday"},
            {"day1-profile": "Weekday"},
            {"day2-profile": "Weekday"},
            {"day3-profile": "Weekday"},
            {"day4-profile": "Weekday"},
            {"day5-profile": "Weekend"},
            {"day6-profile": "Weekend"},
        ]
        self.fixture.write_map(map_data)
        self.fixture.write_thermometers(19.0, epoch(SATURDAY))
        self.fixture.enable_heatlog()
        self.fixture.write_heatlog(
            [(minute(SATURDAY) - 60, 210, 190, "p")],
            day=SATURDAY.date(),
        )

        outcome = self.run_watch(now=SATURDAY)

        self.assertEqual(len(outcome.failures), 1)


class RestartTests(unittest.TestCase):
    def test_restart_touches_all_four_core_services(self):
        calls = []

        def fake_run(command, **kwargs):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout="loaded\n", stderr="")

        with mock.patch.object(heatwatch.subprocess, "run", side_effect=fake_run):
            with Quiet():
                failed = heatwatch.restart_services()

        self.assertEqual(failed, [])
        restarted = [command[2] for command in calls if command[1] == "restart"]
        self.assertEqual(restarted, list(heatwatch.SERVICES))

    def test_a_missing_unit_is_skipped_not_failed(self):
        calls = []

        def fake_run(command, **kwargs):
            calls.append(command)
            if command[1] == "show" and command[-1] == "controller":
                return SimpleNamespace(returncode=0, stdout="not-found\n", stderr="")
            return SimpleNamespace(returncode=0, stdout="loaded\n", stderr="")

        with mock.patch.object(heatwatch.subprocess, "run", side_effect=fake_run):
            with Quiet():
                failed = heatwatch.restart_services()

        self.assertEqual(failed, [])
        restarted = [command[2] for command in calls if command[1] == "restart"]
        self.assertNotIn("controller", restarted)
        self.assertEqual(len(restarted), 3)


if __name__ == "__main__":
    unittest.main()
