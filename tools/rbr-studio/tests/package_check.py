#!/usr/bin/env python3
"""Tests for the portable Studio package and its first-run configuration.

Run directly:
    python3 tools/rbr-studio/tests/package_check.py

The package is built into a temporary directory, unpacked, and inspected. It
is not started: the GUI and the pip/Chromium bootstrap are the machine's job.
"""

import json
import pathlib
import stat
import subprocess
import sys
import tarfile
import tempfile
import unittest

STUDIO = pathlib.Path(__file__).resolve().parent.parent
REPO = STUDIO.parent.parent
sys.path.insert(0, str(STUDIO))

import journal_inbox  # noqa: E402


class PackageTests(unittest.TestCase):
    def test_package_contains_the_studio_and_its_journal_tools(self):
        with tempfile.TemporaryDirectory(prefix="rbr-studio-package-") as tmp:
            out = pathlib.Path(tmp) / "out"
            result = subprocess.run(
                [str(STUDIO / "package-studio.sh"), "--dir", str(out)],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            archive = pathlib.Path(result.stdout.strip().splitlines()[-1])
            self.assertTrue(archive.is_file())
            with tarfile.open(archive, "r:gz") as tar:
                names = {member.name.split("/", 1)[1]
                         for member in tar.getmembers()
                         if "/" in member.name}
                package = next(member for member in tar.getmembers()
                               if member.name.endswith("/run-studio.sh"))
                self.assertTrue(package.mode & stat.S_IXUSR)
                self.assertFalse(any(name.startswith("fixtures/") for name in names))
                self.assertNotIn("map.json", names)
                self.assertNotIn("ai-config.json", names)
            for required in ("studio.allspeak", "run-studio.sh", "configure-studio.py",
                             "journal_inbox.py", "journal_import.py", "journal_bundle.py",
                             "scenario_library.py", "requirements-studio.txt",
                             "scenario_runner/__main__.py", "docs/examples/advance.json",
                             "PACKAGE.txt"):
                self.assertIn(required, names)

    def test_launcher_scripts_parse(self):
        for script in ("run-studio.sh", "package-studio.sh"):
            result = subprocess.run(["bash", "-n", str(STUDIO / script)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, f"{script}: {result.stderr}")

    def test_configure_writes_the_inbox_and_creates_the_folders(self):
        with tempfile.TemporaryDirectory(prefix="rbr-studio-config-") as tmp:
            root = pathlib.Path(tmp)
            config = root / "studio-config.json"
            local = root / "local"
            inbox = root / "incoming"
            result = subprocess.run([
                sys.executable, str(STUDIO / "configure-studio.py"),
                "--config", str(config), "--local-dir", str(local),
                "--inbox", str(inbox), "--system", "00:e0:27:5b:31:40=Home",
                "--no-prompt",
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(data["journalInbox"], str(inbox.absolute()))
            self.assertEqual(data["systems"]["00:e0:27:5b:31:40"], "Home")
            self.assertTrue((local / "journal").is_dir())
            self.assertTrue(inbox.is_dir())
            self.assertTrue((inbox / "00:e0:27:5b:31:40").is_dir())
            self.assertEqual(journal_inbox.resolve_inbox(
                pointer=root / "missing", config=config), inbox.absolute())
            self.assertEqual(journal_inbox.config_systems(config),
                             {"00:e0:27:5b:31:40": "Home"})

    def test_explicit_inbox_wins_over_config(self):
        with tempfile.TemporaryDirectory(prefix="rbr-studio-config-") as tmp:
            root = pathlib.Path(tmp)
            config = root / "studio-config.json"
            config.write_text(json.dumps({"journalInbox": str(root / "configured")}),
                              encoding="utf-8")
            self.assertEqual(
                journal_inbox.resolve_inbox(explicit=str(root / "explicit"),
                                            pointer=root / "missing", config=config),
                (root / "explicit").absolute())


if __name__ == "__main__":
    unittest.main()
