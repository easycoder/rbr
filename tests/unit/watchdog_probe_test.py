#!/usr/bin/env python3
"""
watchdog_probe_test.py - the controller health probe must see a wedged session.

Run directly:  python3 tests/unit/watchdog_probe_test.py
or as part of: tests/unit/run-unit-tests.sh

Why this exists. `is-active` cannot tell a controller that is working from one
that subscribed to the broker and never started: both processes are alive and
both answer systemd. The 2026-11-17 report had two of those (107 minutes and
70+ minutes) and the watchdog restarted neither, because its controller probe
returned success unconditionally. The probe now reads the unit's own log for
`Subscribed to topic` (the MQTT client is up) and `Load the system map` (the
script's start-up ran); this test runs the real script with a fake systemctl,
journalctl and logger, and checks which of those logs earn a restart.
"""

import os
import pathlib
import stat
import subprocess
import tempfile
import time
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
WATCHDOG = REPO / "rbr-watchdog.sh"

SYSTEMCTL = """\
#!/bin/sh
case "$1" in
    is-enabled) exit 0 ;;
    is-active) exit 0 ;;
    enable) exit 0 ;;
    restart) printf 'restart %s\\n' "$2" >> "$RBR_TEST_STATE"; exit 0 ;;
esac
exit 0
"""

JOURNALCTL = """\
#!/bin/sh
cat "$RBR_TEST_JOURNAL"
"""

LOGGER = """\
#!/bin/sh
exit 0
"""


def journal(*lines):
    """Build journalctl -o short-unix lines: "EPOCH.AGE host unit[pid]: text"."""
    now = time.time()
    return "".join(
        "%.6f hvac01 controller[%d]: %s\n" % (now - age, 1000 + i, text)
        for i, (age, text) in enumerate(lines))


class WatchdogProbe(unittest.TestCase):
    def run_watchdog(self, log):
        tmp = pathlib.Path(tempfile.mkdtemp())
        bindir = tmp / "bin"
        bindir.mkdir()
        for name, body in (("systemctl", SYSTEMCTL),
                           ("journalctl", JOURNALCTL),
                           ("logger", LOGGER)):
            path = bindir / name
            path.write_text(body, encoding="utf-8")
            path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        journal_path = tmp / "journal.log"
        journal_path.write_text(log, encoding="utf-8")
        state_path = tmp / "state"
        state_path.write_text("", encoding="utf-8")
        env = {
            "PATH": "%s:/usr/bin:/bin" % bindir,
            "RBR_WATCH_SERVICES": "controller",
            "RBR_WATCH_HEAT": "0",
            "RBR_TEST_JOURNAL": str(journal_path),
            "RBR_TEST_STATE": str(state_path),
        }
        proc = subprocess.run(["bash", str(WATCHDOG)], env=env,
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0,
                         "the watchdog did not finish cleanly:\n" + proc.stdout + proc.stderr)
        return state_path.read_text(encoding="utf-8")

    def test_a_started_session_is_not_restarted(self):
        state = self.run_watchdog(journal(
            (8, "Started controller.service - RBR Controller."),
            (7, "Subscribed to topic: 40:b0:34:33:22:11 with QoS 1"),
            (7, "Load the system map")))
        self.assertNotIn("restart controller", state)

    def test_a_subscribed_session_that_never_loaded_the_map_is_restarted(self):
        # The reported failure: connected, alive, and idle for ever.
        state = self.run_watchdog(journal(
            (300, "Started controller.service - RBR Controller."),
            (299, "Subscribed to topic: 40:b0:34:33:22:11 with QoS 1")))
        self.assertIn("restart controller", state)

    def test_a_session_still_starting_is_left_alone(self):
        # A healthy start finishes in seconds; the two-minute grace covers it.
        state = self.run_watchdog(journal(
            (10, "Started controller.service - RBR Controller."),
            (9, "Subscribed to topic: 40:b0:34:33:22:11 with QoS 1")))
        self.assertNotIn("restart controller", state)

    def test_an_earlier_map_load_does_not_vouch_for_a_new_session(self):
        # The crash loop's shape: each session loads its map, then dies; the
        # next one must still prove itself.
        state = self.run_watchdog(journal(
            (300, "Started controller.service - RBR Controller."),
            (299, "Subscribed to topic: 40:b0:34:33:22:11 with QoS 1"),
            (299, "Load the system map"),
            (200, "Started controller.service - RBR Controller."),
            (199, "Subscribed to topic: 40:b0:34:33:22:11 with QoS 1")))
        self.assertIn("restart controller", state)

    def test_an_empty_journal_is_not_a_reason_to_restart(self):
        state = self.run_watchdog("")
        self.assertNotIn("restart controller", state)


if __name__ == "__main__":
    unittest.main(verbosity=2)
