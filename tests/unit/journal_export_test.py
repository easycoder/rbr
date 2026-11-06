#!/usr/bin/env python3
"""Tests for journal-export.py and its bundle compatibility with the importer."""

import datetime as dt
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
STUDIO = REPO / "tools" / "scenario-studio"
sys.path.insert(0, str(STUDIO))
import journal_bundle  # noqa: E402

spec = importlib.util.spec_from_file_location("journal_export", REPO / "journal-export.py")
journal_export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(journal_export)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="rbr-export-test-")
        self.root = pathlib.Path(self._tmp.name) / "events"
        self.out = pathlib.Path(self._tmp.name) / "exports"
        self.day = dt.date(2026, 11, 6)
        day_dir = self.root / "2026" / "11"
        day_dir.mkdir(parents=True)
        (self.root / "maps").mkdir()
        base = {"name": "Test", "profile": 0, "rooms": [], "profiles": [{"name": "Weekday", "rooms": {}}]}
        raw = json.dumps(base, sort_keys=True, separators=(",", ":")).encode()
        self.digest = __import__("hashlib").sha256(raw).hexdigest()
        (self.root / "maps" / f"{self.digest}.json").write_bytes(raw)
        start = int(dt.datetime(2026, 11, 6, 11, 0, tzinfo=dt.timezone.utc).timestamp() * 1000)
        events = [
            {"v": 1, "tsMs": start, "seq": 1, "type": "session.start",
             "data": {"system": "Test home", "profile": "Weekday", "profileIndex": 0, "mapHash": self.digest},
             "ts": "2026-11-06T11:00:00+00:00", "tzOffsetMinutes": 0},
            {"v": 1, "tsMs": start + 60000, "seq": 2, "type": "sensor.reading",
             "data": {"room": "Kitchen", "sensor": "k", "temp": 1840, "humidity": 50, "battery": 90},
             "ts": "2026-11-06T11:01:00+00:00", "tzOffsetMinutes": 0},
            {"v": 1, "tsMs": start + 120000, "seq": 3, "type": "sensor.reading",
             "data": {"room": "Kitchen", "sensor": "k", "temp": 1840, "humidity": 50, "battery": 90},
             "ts": "2026-11-06T11:02:00+00:00", "tzOffsetMinutes": 0},
            {"v": 1, "tsMs": start + 180000, "seq": 4, "type": "sensor.reading",
             "data": {"room": "Kitchen", "sensor": "k", "temp": 1850, "humidity": 50, "battery": 90},
             "ts": "2026-11-06T11:03:00+00:00", "tzOffsetMinutes": 0},
            {"v": 1, "tsMs": start + 240000, "seq": 5, "type": "room.state",
             "data": {"room": "Kitchen", "mode": "timed", "relay": "off"},
             "ts": "2026-11-06T11:04:00+00:00", "tzOffsetMinutes": 0},
        ]
        (day_dir / "2026-11-06.jsonl").write_text(
            "".join(json.dumps(event, separators=(",", ":")) + "\n" for event in events),
            encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_scenario_mode_drops_repeated_sensor_values_and_preserves_bundle(self):
        archive, manifest = journal_export.export_day(
            self.root, self.day, self.out, mode="scenario", keep=2)
        self.assertTrue(archive.is_file())
        self.assertEqual(manifest["events"], 4)  # session, 2 sensor values, room state
        opened = journal_bundle.open_bundle(archive)
        try:
            self.assertEqual(opened.manifest["day"], "2026-11-06")
            self.assertEqual(opened.manifest["system"], "Test home")
            self.assertEqual(opened.load_map(self.digest)["name"], "Test")
            events = journal_bundle.read_events(opened.events_path)
            self.assertEqual([event["type"] for event in events],
                             ["session.start", "sensor.reading", "sensor.reading", "room.state"])
            self.assertEqual([event["data"].get("temp") for event in events
                              if event["type"] == "sensor.reading"], [1840, 1850])
        finally:
            opened.close()

    def test_full_and_summary_modes(self):
        _, full = journal_export.export_day(self.root, self.day, self.out / "full",
                                           mode="full", keep=0)
        self.assertEqual(full["events"], 5)
        _, summary = journal_export.export_day(self.root, self.day, self.out / "summary",
                                              mode="summary", keep=0)
        self.assertEqual(summary["events"], 2)  # session and room state

    def test_export_retention_keeps_newest_archives(self):
        first = self.out / "old.tar.gz"
        second = self.out / "new.tar.gz"
        self.out.mkdir(parents=True)
        first.write_text("old", encoding="utf-8")
        second.write_text("new", encoding="utf-8")
        import os
        os.utime(first, (1, 1))
        os.utime(second, (2, 2))
        journal_export._prune_exports(self.out, 1)
        self.assertFalse(first.exists())
        self.assertTrue(second.exists())


if __name__ == "__main__":
    unittest.main()
