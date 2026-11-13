#!/usr/bin/env python3
"""Tests for rbr-doctor.py.

The doctor is only useful if it reports the right thing on a bad day, so the
tests here pin the two judgements that matter rather than the wording of the
report:

* a controller session that logs `Subscribed to topic` and then no
  `Load the system map` is a failure, because that is the "connected but
  silent" state the UI shows as "Reconnecting..." (2026-11-12 report);
* the MQTT round-trip probe survives both paho API versions and reports a
  reply, a refused connection and a timeout distinctly.

Nothing here talks to systemd, the broker or a controller.
"""
import importlib.util
import json
import os
import sys
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


doctor = load_module("rbr_doctor", "rbr-doctor.py")


SICK_SESSION = """\
2026-11-12T04:15:18+0000 hvac01 systemd[1]: Started RBR Controller.
2026-11-12T04:15:20+0000 hvac01 allspeak[1429914]: Run Controller
2026-11-12T04:15:20+0000 hvac01 allspeak[1429914]: AllSpeak version 2610142212
2026-11-12T04:15:20+0000 hvac01 allspeak[1429914]: MAC address is 40:b0:34:33:22:11
2026-11-12T04:15:20+0000 hvac01 allspeak[1429914]: Client 6c3d3457 connected
2026-11-12T04:15:20+0000 hvac01 allspeak[1429914]: Subscribed to topic: 40:b0:34:33:22:11
"""

HEALTHY_SESSION = SICK_SESSION + """\
2026-11-12T04:15:20+0000 hvac01 allspeak[1429914]: Load the system map
2026-11-12T04:15:20+0000 hvac01 allspeak[1429914]: Heat logging disabled (no heatlog-root file)
"""


class HumanAgeTest(unittest.TestCase):
    def test_units_read_like_a_person(self):
        self.assertEqual(doctor.human_age(42), "42 s")
        self.assertEqual(doctor.human_age(15 * 60), "15 min")
        self.assertEqual(doctor.human_age(2 * 3600 + 15 * 60), "2 h 15 min")
        self.assertEqual(doctor.human_age(3 * 86400 + 4 * 3600), "3 d 4 h")
        self.assertEqual(doctor.human_age(None), "unknown")

    def test_freshness_thresholds(self):
        self.assertEqual(doctor.freshness_level(30, 300, 900), "ok")
        self.assertEqual(doctor.freshness_level(600, 300, 900), "warn")
        self.assertEqual(doctor.freshness_level(1200, 300, 900), "fail")
        self.assertEqual(doctor.freshness_level(None, 300, 900), "note")


class ControllerLogTest(unittest.TestCase):
    def test_connected_but_never_started_is_a_failure(self):
        analysis = doctor.analyse_controller_log(SICK_SESSION)
        levels = [level for level, _ in analysis["findings"]]
        self.assertIn("fail", levels)
        self.assertIsNone(analysis["map_index"])
        self.assertEqual(analysis["topic"], "40:b0:34:33:22:11")
        self.assertEqual(analysis["mac"], "40:b0:34:33:22:11")
        self.assertEqual(analysis["runtime"], "2610142212")
        text = " ".join(message for _level, message in analysis["findings"])
        self.assertIn("never reached its main loop", text)

    def test_a_map_load_after_the_subscription_is_healthy(self):
        analysis = doctor.analyse_controller_log(HEALTHY_SESSION)
        levels = [level for level, _ in analysis["findings"]]
        self.assertNotIn("fail", levels)
        self.assertIn("ok", levels)
        self.assertGreater(analysis["map_index"], analysis["topic_index"])

    def test_a_map_load_from_an_earlier_session_does_not_count(self):
        log = HEALTHY_SESSION + SICK_SESSION
        analysis = doctor.analyse_controller_log(log)
        levels = [level for level, _ in analysis["findings"]]
        self.assertIn("fail", levels)

    def test_compile_and_credential_errors_are_named(self):
        log = ("Run Controller\n"
               "Compile error: Duplicate symbol name\n"
               "Error: Unable to load credentials from file or server\n")
        analysis = doctor.analyse_controller_log(log)
        text = " ".join(message for _level, message in analysis["findings"])
        self.assertIn("compiler error", text)
        self.assertIn("could not load credentials", text)

    def test_an_empty_journal_says_so_instead_of_crashing(self):
        analysis = doctor.analyse_controller_log("")
        self.assertEqual(analysis["rows"], 0)
        self.assertEqual(analysis["findings"][0][0], "note")

    def test_restart_starts_and_exit_reasons_are_collected(self):
        log = """\
2026-11-12T19:30:00+0000 host systemd[1]: Started controller.service - RBR Controller.
2026-11-12T19:30:00+0000 host allspeak[1]: Run Controller
2026-11-12T19:31:00+0000 host systemd[1]: controller.service: Main process exited, code=exited, status=0/SUCCESS
2026-11-12T19:31:00+0000 host systemd[1]: controller.service: Scheduled restart job, restart counter is at 1.
2026-11-12T19:35:00+0000 host systemd[1]: Started controller.service - RBR Controller.
2026-11-12T19:35:00+0000 host allspeak[2]: Run Controller
2026-11-12T19:36:00+0000 host systemd[1]: controller.service: Failed with result 'exit-code'.
2026-11-12T19:40:00+0000 host systemd[1]: Started controller.service - RBR Controller.
2026-11-12T19:40:00+0000 host allspeak[3]: Run Controller
"""
        analysis = doctor.analyse_controller_log(log)
        self.assertEqual(analysis["starts"], 3)
        self.assertEqual(len(analysis["start_lines"]), 3)
        self.assertEqual(len(analysis["exit_lines"]), 3)
        text = " ".join(analysis["exit_lines"])
        self.assertIn("status=0/SUCCESS", text)
        self.assertIn("Failed with result", text)
        # The error field is case-insensitive: systemd writes 'Failed', not
        # 'failed', and the old regex missed it.
        self.assertIn("Failed with result", analysis["error"])


class FakeClient:
    """A paho-compatible client that answers the probe in-process."""

    def __init__(self, reply=b'{"profiles": []}', connect_code=0,
                 granted=(1,), *args, **kwargs):
        self.reply = reply
        self.connect_code = connect_code
        self.granted = granted
        self.subscribed = []
        self.published = []
        self.on_connect = None
        self.on_subscribe = None
        self.on_message = None
        self.on_publish = None

    def username_pw_set(self, *args):
        self.credentials = args

    def connect(self, host, port, keepalive):
        self.connected_to = (host, port)

    def loop_start(self):
        # paho calls on_connect from its network thread. VERSION2 passes a
        # ReasonCode-like object, v1 an int; an int exercises both.
        if self.on_connect:
            self.on_connect(self, None, {}, self.connect_code, None)

    def subscribe(self, topic, qos=0):
        self.subscribed.append(topic)
        if self.granted is not None and self.on_subscribe:
            self.on_subscribe(self, None, 1, list(self.granted), None)

    def publish(self, topic, payload, qos=0):
        self.published.append((topic, payload, qos))
        if self.on_publish:
            self.on_publish(self, None, 1, 0, None)
        if self.reply is not None and self.on_message:
            message = types.SimpleNamespace(payload=self.reply, topic=topic)
            self.on_message(self, None, message)

    def loop_stop(self):
        pass

    def disconnect(self):
        pass


def fake_paho(client_factory):
    """Install a fake paho.mqtt.client for the duration of a probe."""
    client_module = types.ModuleType("paho.mqtt.client")
    client_module.Client = client_factory
    client_module.MQTTv311 = 4
    client_module.CallbackAPIVersion = types.SimpleNamespace(VERSION2=2)
    mqtt_module = types.ModuleType("paho.mqtt")
    mqtt_module.client = client_module
    paho_module = types.ModuleType("paho")
    paho_module.mqtt = mqtt_module
    return {"paho": paho_module, "paho.mqtt": mqtt_module,
            "paho.mqtt.client": client_module}


CREDS = {"broker": "broker.example", "username": "u", "password": "p"}
MAC = "40:b0:34:33:22:11"


class MqttProbeTest(unittest.TestCase):
    def probe(self, factory):
        with mock.patch.dict(sys.modules, fake_paho(factory)):
            return doctor.mqtt_probe(CREDS, MAC, timeout=0.5)

    def test_a_reply_is_reported(self):
        result, reason = self.probe(FakeClient)
        self.assertEqual(reason, "")
        self.assertTrue(result["connected"])
        self.assertTrue(result["published"])
        self.assertEqual(result["reply"], b'{"profiles": []}')
        self.assertEqual(result["granted"], [1])
        self.assertIsNotNone(result["connect_elapsed"])
        self.assertIsNotNone(result["reply_elapsed"])
        self.assertEqual(result["sender"], "%s/doctor-%d" % (MAC, os.getpid()))

    def test_a_refused_subscription_is_visible(self):
        result, _reason = self.probe(lambda *a, **k: FakeClient(granted=(128,)))
        self.assertEqual(result["granted"], [128])

    def test_no_suback_is_not_mistaken_for_a_grant(self):
        result, _reason = self.probe(lambda *a, **k: FakeClient(granted=None))
        self.assertIsNone(result["granted"])

    def test_every_result_is_a_pair_so_the_caller_can_unpack_it(self):
        # The live 2026-11-12 report crashed on `result, reason = mqtt_probe(...)`
        # because a successful probe returned a bare dict. Pin the shape.
        for factory in (FakeClient, lambda *a, **k: FakeClient(connect_code=5)):
            outcome = self.probe(factory)
            self.assertIsInstance(outcome, tuple)
            self.assertEqual(len(outcome), 2)

    def test_the_sender_topic_is_used_for_the_subscription(self):
        client = FakeClient()

        def factory(*args, **kwargs):
            return client

        self.probe(factory)
        self.assertEqual(client.subscribed, ["%s/doctor-%d" % (MAC, os.getpid())])
        self.assertEqual(client.published[0][0], MAC)
        payload = json.loads(client.published[0][1].decode())
        self.assertEqual(payload["action"], "first")
        self.assertEqual(payload["sender"]["name"], client.subscribed[0])

    def test_a_refused_connection_is_not_reported_as_a_reply(self):
        result, reason = self.probe(lambda *a, **k: FakeClient(connect_code=5))
        self.assertEqual(reason, "")
        self.assertFalse(result["connected"])
        self.assertIsNone(result["reply"])

    def test_missing_paho_skips_instead_of_crashing(self):
        with mock.patch.dict(sys.modules, {"paho": None, "paho.mqtt": None,
                                           "paho.mqtt.client": None}):
            result, reason = doctor.mqtt_probe(CREDS, MAC, timeout=0.5)
        self.assertIsNone(result)
        self.assertIn("paho", reason)


class LinuxParseTest(unittest.TestCase):
    SS = """\
State  Recv-Q Send-Q Local Address:Port  Peer Address:Port Process
ESTAB  0      0      192.168.1.10:42312  1.2.3.4:1883      users:(("allspeak",pid=1429914,fd=5))
ESTAB  0      0      192.168.1.10:42313  1.2.3.4:443
LISTEN 0      128    127.0.0.1:1883        0.0.0.0:*
"""

    def test_only_established_mqtt_connections_are_counted(self):
        peers = doctor.parse_established(self.SS, 1883)
        self.assertEqual(peers, ["1.2.3.4:1883"])
        self.assertEqual(doctor.parse_established(self.SS, 443), ["1.2.3.4:443"])

    def test_failed_units_are_named(self):
        text = """\
nginx.service loaded failed failed A high performance web server
\u25cf foo.mount loaded failed failed /mnt/foo
not a unit line
"""
        self.assertEqual(doctor.parse_failed_units(text),
                         ["nginx.service", "foo.mount"])

    def test_inode_percentage_is_read_from_df(self):
        text = """\
Filesystem      Inodes  IUsed   IFree IUse% Mounted on
/dev/sda1       655360   1000  654360    1% /
"""
        self.assertEqual(doctor.inode_use_percent(text), 1)
        self.assertIsNone(doctor.inode_use_percent(""))


class DashboardCheckTest(unittest.TestCase):
    def test_the_service_flag_disables_the_dashboard_check(self):
        self.assertFalse(doctor.dashboard_enabled(
            "/usr/bin/python3 /home/qed6/.local/bin/allspeak controller.allspeak --no-dashboard"))
        self.assertTrue(doctor.dashboard_enabled(
            "/usr/bin/python3 /home/qed6/.local/bin/allspeak controller.allspeak"))



class RoundTripReportTest(unittest.TestCase):
    def setUp(self):
        doctor.lines[:] = []
        doctor.hints[:] = []
        doctor.facts.clear()
        doctor.facts["controller_uptime"] = 600

    def tearDown(self):
        doctor.lines[:] = []
        doctor.hints[:] = []
        doctor.facts.clear()

    def run_report(self, client):
        with mock.patch.dict(sys.modules, fake_paho(lambda *a, **k: client)):
            doctor.check_round_trip(CREDS, MAC, timeout=0.5)
        return "\n".join("%s %s" % (level, text) for level, text in doctor.lines)

    def test_a_reply_is_reported_without_crashing(self):
        text = self.run_report(FakeClient())
        self.assertIn("probe connected to the broker", text)
        self.assertIn("probe subscription granted", text)
        self.assertIn("the controller replied", text)
        self.assertNotIn("no reply", text)

    def test_a_missing_reply_is_reported_as_a_failure(self):
        text = self.run_report(FakeClient(reply=None))
        self.assertIn("no reply from the controller", text)
        self.assertIn("fail", text)

    def test_a_refused_subscription_is_not_reported_as_controller_silence(self):
        text = self.run_report(FakeClient(granted=(128,)))
        self.assertIn("refused the probe's subscription", text)
        self.assertNotIn("no reply from the controller", text)


class ReportTest(unittest.TestCase):
    def tearDown(self):
        doctor.lines[:] = []
        doctor.hints[:] = []
        doctor.facts.clear()

    def test_the_report_carries_the_action_and_the_findings(self):
        doctor.say("fail", "the controller does not answer")
        doctor.hint("Restart the controller.")
        text = doctor.render_text()
        self.assertIn("[FAIL] the controller does not answer", text)
        self.assertIn("What this points at", text)
        self.assertIn("Work through the [FAIL] items", text)

    def test_root_run_does_not_ask_to_re_run_with_sudo(self):
        # The 2026-11-12 report was run as root and still ended with
        # "Re-run with sudo for the full journal".
        doctor.facts["controller"] = {"ActiveState": "active"}
        doctor.facts["controller_journal_note"] = ""
        with mock.patch.object(doctor.os, "geteuid", return_value=0):
            text = doctor.render_text()
        self.assertIn("run as root", text)
        self.assertNotIn("Re-run as root", text)
        self.assertNotIn("sudo ./rbr-doctor.py", text)

    def test_an_unreadable_journal_asks_for_root(self):
        doctor.facts["controller"] = {"ActiveState": "active"}
        doctor.facts["controller_journal_note"] = (
            "not readable as this user (not in systemd-journal or adm) — "
            "re-run the doctor with sudo")
        with mock.patch.object(doctor.os, "geteuid", return_value=1000):
            text = doctor.render_text()
        self.assertIn("Re-run as root", text)

    def test_a_healthy_report_says_no_action_needed(self):
        doctor.facts["controller"] = {"ActiveState": "active"}
        with mock.patch.object(doctor.os, "geteuid", return_value=0):
            text = doctor.render_text()
        self.assertIn("No action needed", text)

    def test_the_json_report_is_machine_readable_and_carries_no_secrets(self):
        doctor.facts["credentials_problem"] = "present"
        doctor.say("ok", "credentials present")
        text = doctor.render_json()
        report = json.loads(text)
        self.assertIn("facts", report)
        self.assertIn("lines", report)
        self.assertNotIn("password", text.lower())


if __name__ == "__main__":
    unittest.main()
