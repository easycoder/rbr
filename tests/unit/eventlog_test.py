#!/usr/bin/env python3
"""
eventlog_test.py - unit tests for eventlog.py (the RBR event-journal writer).

Run directly:  python3 tests/unit/eventlog_test.py
or as part of: tests/unit/run-unit-tests.sh
Uses only stdlib; writes only under temporary directories.
"""

import json
import os
import pathlib
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
import eventlog  # noqa: E402


class DatePathTests(unittest.TestCase):
    """The daily file must be derived from each event's own timestamp, local time."""

    @classmethod
    def setUpClass(cls):
        cls._old_tz = os.environ.get("TZ")
        os.environ["TZ"] = "UTC"
        try:
            time.tzset()
        except AttributeError:
            pass

    @classmethod
    def tearDownClass(cls):
        if cls._old_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = cls._old_tz
        try:
            time.tzset()
        except AttributeError:
            pass

    def ts(self, y, mo, d, h, mi, s=0):
        return int(time.mktime((y, mo, d, h, mi, s, 0, 0, 0)) * 1000)

    def test_midnight_boundary(self):
        self.assertEqual(eventlog.day_path("ROOT", self.ts(2026, 2, 28, 23, 59)),
                         pathlib.Path("ROOT/2026/02/2026-02-28.jsonl"))
        self.assertEqual(eventlog.day_path("ROOT", self.ts(2026, 3, 1, 0, 1)),
                         pathlib.Path("ROOT/2026/03/2026-03-01.jsonl"))

    def test_year_rollover(self):
        self.assertEqual(eventlog.day_path("ROOT", self.ts(2025, 12, 31, 23, 59)),
                         pathlib.Path("ROOT/2025/12/2025-12-31.jsonl"))
        self.assertEqual(eventlog.day_path("ROOT", self.ts(2026, 1, 1, 0, 1)),
                         pathlib.Path("ROOT/2026/01/2026-01-01.jsonl"))

    def test_leap_day_and_padding(self):
        self.assertEqual(eventlog.day_path("ROOT", self.ts(2024, 2, 29, 12, 0)),
                         pathlib.Path("ROOT/2024/02/2024-02-29.jsonl"))
        self.assertEqual(eventlog.day_path("ROOT", self.ts(2026, 9, 2, 8, 30)),
                         pathlib.Path("ROOT/2026/09/2026-09-02.jsonl"))


class AppendTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def event(self, kind="sensor.reading", **data):
        return {"type": kind, "tsMs": 1788177600000, "seq": 1, "boot": "b1", "data": data}

    def test_appends_compact_json_lines(self):
        eventlog.append_events(self.root, [self.event(temp=1840), self.event(temp=1850)])
        path = eventlog.day_path(self.root, 1788177600000)
        lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        first = json.loads(lines[0])
        self.assertEqual(first["type"], "sensor.reading")
        self.assertEqual(first["data"]["temp"], 1840)
        self.assertEqual(first["v"], 1)
        self.assertIn("ts", first)
        self.assertIn("tzOffsetMinutes", first)
        self.assertNotIn("\n", lines[0])

    def test_split_across_midnight_uses_each_event_timestamp(self):
        before = {"type": "room.state", "tsMs": int(time.mktime((2026, 3, 1, 23, 59, 0, 0, 0, 0)) * 1000)}
        after = {"type": "room.state", "tsMs": int(time.mktime((2026, 3, 2, 0, 1, 0, 0, 0, 0)) * 1000)}
        eventlog.append_events(self.root, [before, after])
        files = sorted(p.name for p in self.root.glob("*/*/*.jsonl"))
        self.assertEqual(files, ["2026-03-01.jsonl", "2026-03-02.jsonl"])

    def test_invalid_events_are_skipped(self):
        written, skipped = eventlog.append_events(
            self.root, [{"no": "type"}, "not a dict", self.event()])
        self.assertEqual((written, skipped), (1, 2))

    def test_map_snapshot_is_content_addressed_and_removed_from_the_line(self):
        event = self.event("session.start", system="Home", map={"rooms": [{"name": "Kitchen"}]})
        eventlog.append_events(self.root, [event])
        line = json.loads(eventlog.day_path(self.root, 1788177600000).read_text(encoding="utf-8"))
        data = line["data"]
        self.assertNotIn("map", data)
        self.assertIn("mapHash", data)
        self.assertGreater(data["mapBytes"], 0)
        stored = self.root / "maps" / f"{data['mapHash']}.json"
        self.assertEqual(json.loads(stored.read_text(encoding="utf-8"))["rooms"][0]["name"], "Kitchen")

    def test_identical_maps_share_one_file(self):
        payload = {"rooms": [{"name": "Kitchen"}]}
        eventlog.append_events(self.root, [
            self.event("session.start", map=payload),
            self.event("plan.snapshot", map=payload),
        ])
        maps = list((self.root / "maps").glob("*.json"))
        self.assertEqual(len(maps), 1)

    def test_batch_file_is_removed_after_processing(self):
        batch = self.root / "batch.json"
        batch.write_text(json.dumps([self.event()]), encoding="utf-8")
        self.assertEqual(eventlog.main(["--root", str(self.root), "--batch", str(batch), "--quiet"]), 0)
        self.assertFalse(batch.exists())
        self.assertEqual(len(eventlog.day_path(self.root, 1788177600000).read_text().splitlines()), 1)

    def test_parse_size_suffixes(self):
        self.assertEqual(eventlog.parse_size("1024"), 1024)
        self.assertEqual(eventlog.parse_size("1K"), 1024)
        self.assertEqual(eventlog.parse_size("2M"), 2 * 1024 ** 2)
        self.assertEqual(eventlog.parse_size("1G"), 1024 ** 3)
        self.assertEqual(eventlog.parse_size("junk", 7), 7)

    def test_effective_cap_takes_the_smaller_limit(self):
        gib = 1024 ** 3
        self.assertEqual(eventlog.effective_cap(self.root, gib, 10, free_bytes=4 * gib), int(4 * gib * 10 / 100))
        self.assertEqual(eventlog.effective_cap(self.root, gib, 10, free_bytes=20 * gib), gib)
        self.assertEqual(eventlog.effective_cap(self.root, 0, 0), None)

    def test_prune_deletes_oldest_days_and_keeps_the_current_one(self):
        day1 = self.root / "2026" / "11" / "2026-11-01.jsonl"
        day2 = self.root / "2026" / "11" / "2026-11-02.jsonl"
        day3 = self.root / "2026" / "11" / "2026-11-03.jsonl"
        for path in (day1, day2, day3):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x" * 100, encoding="utf-8")
        result = eventlog.prune(self.root, max_bytes=250, max_free_percent=0, keep=[day3])
        self.assertFalse(day1.exists())
        self.assertTrue(day2.exists())
        self.assertTrue(day3.exists())
        self.assertEqual(result["deletedDays"], [str(day1)])
        self.assertLessEqual(result["totalAfter"], 250)

    def test_prune_removes_maps_only_the_deleted_day_referenced(self):
        digest_a = "a" * 64
        digest_b = "b" * 64
        day1 = self.root / "2026" / "11" / "2026-11-01.jsonl"
        day2 = self.root / "2026" / "11" / "2026-11-02.jsonl"
        day1.parent.mkdir(parents=True, exist_ok=True)
        day1.write_text(json.dumps({"type": "session.start", "data": {"mapHash": digest_a}}), encoding="utf-8")
        day2.write_text(json.dumps({"type": "session.start", "data": {"mapHash": digest_b}}), encoding="utf-8")
        maps = self.root / "maps"
        maps.mkdir()
        for digest in (digest_a, digest_b):
            (maps / f"{digest}.json").write_text("y" * 100, encoding="utf-8")
        result = eventlog.prune(self.root, max_bytes=250, max_free_percent=0, keep=[day2])
        self.assertFalse(day1.exists())
        self.assertTrue(day2.exists())
        self.assertFalse((maps / f"{digest_a}.json").exists())
        self.assertTrue((maps / f"{digest_b}.json").exists())
        self.assertIn(str(maps / f"{digest_a}.json"), result["deletedMaps"])

    def test_prune_keeps_the_current_day_even_when_it_is_over_the_cap(self):
        day = self.root / "2026" / "11" / "2026-11-03.jsonl"
        day.parent.mkdir(parents=True, exist_ok=True)
        day.write_text("x" * 100, encoding="utf-8")
        result = eventlog.prune(self.root, max_bytes=10, max_free_percent=0, keep=[day])
        self.assertTrue(day.exists())
        self.assertTrue(result["over"])

    def test_main_prunes_before_and_after_writing(self):
        old = self.root / "2026" / "08" / "2026-08-01.jsonl"
        old.parent.mkdir(parents=True, exist_ok=True)
        old.write_text("x" * 200, encoding="utf-8")
        batch = self.root / "batch.json"
        event = self.event()
        batch.write_text(json.dumps([event]), encoding="utf-8")
        status = eventlog.main(["--root", str(self.root), "--batch", str(batch),
                                "--max-bytes", "250", "--max-free-percent", "0", "--quiet"])
        self.assertEqual(status, 0)
        self.assertFalse(old.exists())
        self.assertTrue(eventlog.day_path(self.root, event["tsMs"]).exists())

    def test_keep_batch_leaves_the_file(self):
        batch = self.root / "batch.json"
        batch.write_text(json.dumps([self.event()]), encoding="utf-8")
        self.assertEqual(eventlog.main(
            ["--root", str(self.root), "--batch", str(batch), "--keep-batch", "--quiet"]), 0)
        self.assertTrue(batch.exists())


if __name__ == "__main__":
    unittest.main()
