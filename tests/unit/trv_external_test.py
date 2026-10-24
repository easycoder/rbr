#!/usr/bin/env python3
"""
trv_external_test.py - unit tests for the bridge's TRV external-sensor command.

Run directly:  python3 tests/unit/trv_external_test.py
or as part of: tests/unit/run-unit-tests.sh

The controller can tell a TRV to follow a room thermometer rather than its own
sensor. That decision reaches zigbee2mqtt through the bridge's /trv endpoint,
whose query parser is deliberately pure so these tests can exercise it without
a broker or a valve. The state-capture tests then prove the bridge keeps the
reported external reading and sensor choice in zigbee-trv.json for diagnosis.
"""

import importlib.util
import json
import os
import pathlib
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
BRIDGE_PATH = REPO / "zigbee-bridge.py"


def load_bridge():
    """Import zigbee-bridge.py, whose hyphenated name is not a normal module."""
    spec = importlib.util.spec_from_file_location("zigbee_bridge", BRIDGE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ParseTrvCommandTests(unittest.TestCase):
    """The /trv query string is translated into the right zigbee2mqtt payload."""

    @classmethod
    def setUpClass(cls):
        cls.bridge = load_bridge()

    @staticmethod
    def params(**values):
        return {key: [value] for key, value in values.items()}

    def test_no_command_fields_is_a_read(self):
        payload, fields, error = self.bridge._parse_trv_command({})
        self.assertIsNone(payload)
        self.assertEqual(fields, {})
        self.assertIsNone(error)

    def test_setpoint_and_mode_only(self):
        payload, fields, error = self.bridge._parse_trv_command(
            self.params(setpoint="20", mode="heat"))
        self.assertIsNone(error)
        self.assertEqual(payload, {
            "system_mode": "heat",
            "occupied_heating_setpoint": 20.0,
        })
        self.assertEqual(fields, {"setpoint": 20.0, "mode": "heat"})

    def test_external_reading_selects_remote_sensor(self):
        payload, fields, error = self.bridge._parse_trv_command(
            self.params(external="19.77"))
        self.assertIsNone(error)
        self.assertEqual(payload, {
            "external_temperature_input": 19.8,
            "temperature_sensor_select": "remote_temperature",
        })
        self.assertEqual(fields, {"external": 19.8, "sensor": "remote"})

    def test_external_reading_can_explicitly_keep_local_sensor(self):
        payload, fields, error = self.bridge._parse_trv_command(
            self.params(external="19.77", sensor="local"))
        self.assertIsNone(error)
        self.assertEqual(payload, {
            "external_temperature_input": 19.8,
            "temperature_sensor_select": "local_temperature",
        })
        self.assertEqual(fields, {"external": 19.8, "sensor": "local"})

    def test_full_command_carries_all_fields(self):
        payload, fields, error = self.bridge._parse_trv_command(
            self.params(setpoint="20.5", mode="heat", external="19.77",
                        sensor="remote"))
        self.assertIsNone(error)
        self.assertEqual(payload, {
            "system_mode": "heat",
            "occupied_heating_setpoint": 20.5,
            "external_temperature_input": 19.8,
            "temperature_sensor_select": "remote_temperature",
        })
        self.assertEqual(fields, {
            "setpoint": 20.5,
            "mode": "heat",
            "external": 19.8,
            "sensor": "remote",
        })

    def test_sensor_only_is_a_command(self):
        payload, fields, error = self.bridge._parse_trv_command(
            self.params(sensor="local"))
        self.assertIsNone(error)
        self.assertEqual(payload, {
            "temperature_sensor_select": "local_temperature",
        })
        self.assertEqual(fields, {"sensor": "local"})

    def test_setpoint_rounds_to_half_degree(self):
        for raw, expected in (("20.2", 20.0), ("20.3", 20.5), ("40", 35.0)):
            with self.subTest(raw=raw):
                payload, _, error = self.bridge._parse_trv_command(
                    self.params(setpoint=raw, mode="heat"))
                self.assertIsNone(error)
                self.assertEqual(
                    payload["occupied_heating_setpoint"], expected)

    def test_external_clamps_and_rounds(self):
        for raw, expected in (("-5", 0.0), ("100", 99.9), ("19.77", 19.8)):
            with self.subTest(raw=raw):
                payload, _, error = self.bridge._parse_trv_command(
                    self.params(external=raw))
                self.assertIsNone(error)
                self.assertEqual(
                    payload["external_temperature_input"], expected)

    def test_invalid_values_are_rejected(self):
        cases = (
            ({"setpoint": "abc", "mode": "heat"}, "setpoint must be a number"),
            ({"setpoint": "20", "mode": "auto"}, "mode must be heat or off"),
            ({"external": "warm"}, "external must be a number"),
            ({"sensor": "radiator"}, "sensor must be local or remote"),
        )
        for values, message in cases:
            with self.subTest(values=values):
                payload, fields, error = self.bridge._parse_trv_command(
                    self.params(**values))
                self.assertIsNone(payload)
                self.assertEqual(fields, {})
                self.assertEqual(error, message)


class PublishTrvMessagesTests(unittest.TestCase):
    """The reading and the sensor selection must not share a set message.

    zigbee2mqtt runs one toZigbee converter per set message, and the TRVZB's
    two remote-temperature keys are one converter. A combined message applies
    only the first key, so the selection was silently dropped.
    """

    @classmethod
    def setUpClass(cls):
        cls.bridge = load_bridge()

    def test_combined_command_sends_reading_then_selection(self):
        payload, _, error = self.bridge._parse_trv_command(
            self.params(setpoint="20.5", mode="heat",
                        external="19.77", sensor="remote"))
        self.assertIsNone(error)
        messages = self.bridge._trv_publish_messages(payload)
        self.assertEqual(messages, [
            {
                "system_mode": "heat",
                "occupied_heating_setpoint": 20.5,
                "external_temperature_input": 19.8,
            },
            {"temperature_sensor_select": "remote_temperature"},
        ])

    def test_selection_alone_is_one_message(self):
        payload, _, _ = self.bridge._parse_trv_command(
            self.params(sensor="local"))
        self.assertEqual(
            self.bridge._trv_publish_messages(payload),
            [{"temperature_sensor_select": "local_temperature"}])

    def test_reading_alone_is_one_message(self):
        payload = {"external_temperature_input": 19.8}
        self.assertEqual(self.bridge._trv_publish_messages(payload), [payload])

    def test_control_alone_is_one_message(self):
        payload, _, _ = self.bridge._parse_trv_command(
            self.params(setpoint="20", mode="off"))
        self.assertEqual(self.bridge._trv_publish_messages(payload), [payload])

    @staticmethod
    def params(**values):
        return {key: [value] for key, value in values.items()}


class TrvStateCaptureTests(unittest.TestCase):
    """Reported TRV fields reach device_states and zigbee-trv.json."""

    def setUp(self):
        self.bridge = load_bridge()
        self.tmp = tempfile.TemporaryDirectory()
        self.bridge.device_states.clear()
        self.bridge.trv_commands.clear()
        self.bridge.temperatures_path = os.path.join(
            self.tmp.name, "zigbee-temperatures.json")
        self.bridge.trv_path = os.path.join(
            self.tmp.name, "zigbee-trv.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_external_reading_and_sensor_are_recorded(self):
        self.bridge._handle_device_update("LR-Rad", {
            "local_temperature": 21.0,
            "occupied_heating_setpoint": 20.0,
            "system_mode": "heat",
            "external_temperature_input": 19.8,
            "temperature_sensor_select": "remote_temperature",
            "battery": 100,
        })

        state = self.bridge.device_states["LR-Rad"]
        self.assertEqual(state["external_temperature"], 19.8)
        self.assertEqual(state["temperature_sensor_select"],
                         "remote_temperature")

        with open(self.bridge.trv_path) as f:
            trv = json.load(f)["LR-Rad"]
        self.assertEqual(trv["external_temperature"], 19.8)
        self.assertEqual(trv["temperature_sensor_select"],
                         "remote_temperature")


if __name__ == "__main__":
    unittest.main()
