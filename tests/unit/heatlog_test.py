#!/usr/bin/env python3
"""
heatlog_test.py - unit tests for heatlog.py (the RBR heating-data CSV writer).

Run directly:  python3 tests/unit/heatlog_test.py
or as part of: tests/unit/run-unit-tests.sh
Uses only stdlib; writes only under temporary directories.
"""

import datetime
import os
import pathlib
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
import heatlog  # noqa: E402

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent


def utc_minutes(y, mo, d, h, mi):
    """Epoch minutes for a UTC instant (tests pin TZ=UTC)."""
    stamp = int(datetime.datetime(y, mo, d, h, mi, tzinfo=datetime.timezone.utc).timestamp())
    return stamp // 60


class DatePathTests(unittest.TestCase):
    """The day file must be derived from the row's own timestamp, local time."""

    @classmethod
    def setUpClass(cls):
        cls._old_tz = os.environ.get("TZ")
        os.environ["TZ"] = "UTC"
        try:
            time.tzset()
        except AttributeError:  # non-POSIX
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

    def rel(self, ts):
        return heatlog.day_csv_path("ROOT", "Kitchen", ts)

    def test_midnight_boundary(self):
        # 23:59 on 28 Feb 2026 stays in Feb; 00:05 on 1 Mar rolls over.
        self.assertEqual(self.rel(utc_minutes(2026, 2, 28, 23, 59)),
                         pathlib.Path("ROOT/Kitchen/2026/02/28.csv"))
        self.assertEqual(self.rel(utc_minutes(2026, 3, 1, 0, 5)),
                         pathlib.Path("ROOT/Kitchen/2026/03/01.csv"))

    def test_year_rollover(self):
        self.assertEqual(self.rel(utc_minutes(2025, 12, 31, 23, 59)),
                         pathlib.Path("ROOT/Kitchen/2025/12/31.csv"))
        self.assertEqual(self.rel(utc_minutes(2026, 1, 1, 0, 1)),
                         pathlib.Path("ROOT/Kitchen/2026/01/01.csv"))

    def test_leap_day(self):
        self.assertEqual(self.rel(utc_minutes(2024, 2, 29, 12, 0)),
                         pathlib.Path("ROOT/Kitchen/2024/02/29.csv"))

    def test_zero_padding(self):
        self.assertEqual(self.rel(utc_minutes(2026, 9, 2, 8, 30)),
                         pathlib.Path("ROOT/Kitchen/2026/09/02.csv"))


class SanitiseTests(unittest.TestCase):
    def test_path_separators_replaced(self):
        self.assertNotIn("/", heatlog.sanitise_room("a/b"))
        self.assertNotIn("\\", heatlog.sanitise_room("a\\b"))
        self.assertNotIn("..", heatlog.day_csv_path("R", "../evil", 1000).parts)

    def test_blank_falls_back(self):
        self.assertEqual(heatlog.sanitise_room(""), "unnamed")
        self.assertEqual(heatlog.sanitise_room(".."), "unnamed")

    def test_spaces_kept(self):
        self.assertEqual(heatlog.sanitise_room("Main Bedroom"), "Main Bedroom")


class AppendTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_creates_tree_and_appends(self):
        ts = utc_minutes(2026, 9, 2, 8, 30)
        p1 = heatlog.append_row(self.root, "Kitchen", ts, 207, 205, "p")
        p2 = heatlog.append_row(self.root, "Kitchen", ts + 20, 207, 206, "p")
        self.assertEqual(p1, self.root / "Kitchen" / "2026" / "09" / "02.csv")
        self.assertEqual(p2, p1)
        lines = p1.read_text(encoding="ascii").splitlines()
        self.assertEqual(lines, [f"{ts},207,205,p", f"{ts + 20},207,206,p"])

    def test_rooms_kept_separate(self):
        ts = utc_minutes(2026, 9, 2, 8, 30)
        heatlog.append_row(self.root, "Kitchen", ts, 207, 205, "p")
        heatlog.append_row(self.root, "Main Bedroom", ts, 190, 188, "o")
        self.assertTrue((self.root / "Kitchen" / "2026" / "09" / "02.csv").is_file())
        self.assertTrue((self.root / "Main Bedroom" / "2026" / "09" / "02.csv").is_file())

    def test_append_through_symlinked_root(self):
        """A symlinked root must behave identically to a real directory."""
        real = pathlib.Path(self._tmp.name) / "real"
        link = pathlib.Path(self._tmp.name) / "link"
        real.mkdir()
        link.symlink_to(real, target_is_directory=True)
        ts = utc_minutes(2026, 9, 2, 8, 30)
        heatlog.append_row(link, "Kitchen", ts, 207, 205, "p")
        target = real / "Kitchen" / "2026" / "09" / "02.csv"
        self.assertTrue(target.is_file())
        self.assertEqual(target.read_text(encoding="ascii").strip(), f"{ts},207,205,p")


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        self._old_cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self._old_cwd)
        self._tmp.cleanup()

    def test_cli_end_to_end(self):
        ts = utc_minutes(2026, 9, 2, 8, 30)
        rc = heatlog.main(["--root", str(self.root), "--room", "Kitchen",
                           "--ts", str(ts), "--target", "207", "--actual", "205", "--mode", "p"])
        self.assertEqual(rc, 0)
        f = self.root / "Kitchen" / "2026" / "09" / "02.csv"
        self.assertEqual(f.read_text(encoding="ascii").strip(), f"{ts},207,205,p")

    def test_mode_defaults_to_off(self):
        ts = utc_minutes(2026, 9, 2, 8, 30)
        heatlog.main(["--root", str(self.root), "--room", "Hall", "--ts", str(ts),
                      "--target", "200", "--actual", "200"])
        f = self.root / "Hall" / "2026" / "09" / "02.csv"
        self.assertTrue(f.read_text(encoding="ascii").strip().endswith(",o"))

    def test_bad_values_rejected(self):
        ts = utc_minutes(2026, 9, 2, 8, 30)
        self.assertEqual(heatlog.main(["--root", str(self.root), "--room", "Kitchen",
                                       "--ts", str(ts), "--target", "x", "--actual", "1"]), 2)
        self.assertEqual(heatlog.main(["--root", str(self.root), "--room", "Kitchen",
                                       "--ts", str(ts), "--target", "1", "--actual", "1",
                                       "--mode", "z"]), 2)
        self.assertEqual(heatlog.main(["--root", str(self.root), "--room", "Kitchen",
                                       "--ts", "-1", "--target", "1", "--actual", "1"]), 2)

    def test_root_resolution_order(self):
        ts = utc_minutes(2026, 9, 2, 8, 30)
        # 1. --root wins.
        heatlog.main(["--root", str(self.root), "--room", "A", "--ts", str(ts),
                      "--target", "1", "--actual", "1"])
        self.assertTrue((self.root / "A" / "2026" / "09" / "02.csv").is_file())
        # 2. Without --root, a heatlog-root file in the cwd is honoured.
        os.chdir(self._tmp.name)
        config_dir = pathlib.Path(self._tmp.name) / "cfg"
        config_dir.mkdir()
        pathlib.Path("heatlog-root").write_text(str(config_dir), encoding="utf-8")
        try:
            self.assertEqual(heatlog.resolve_root(None), config_dir)
            heatlog.main(["--room", "B", "--ts", str(ts), "--target", "1", "--actual", "1"])
            self.assertTrue((config_dir / "B" / "2026" / "09" / "02.csv").is_file())
        finally:
            os.chdir(self._old_cwd)


if __name__ == "__main__":
    unittest.main(verbosity=2)
