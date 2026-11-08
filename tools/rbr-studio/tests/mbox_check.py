#!/usr/bin/env python3
"""Tests for journal_mbox.py — extract RBR attachments from an mbox.

Run directly:
    python3 tools/rbr-studio/tests/mbox_check.py

The mailbox and bundle are synthetic; no mail client, network or controller is
needed.
"""

import datetime as dt
import json
import mailbox
import pathlib
import subprocess
import sys
import tempfile
import unittest
from email.message import EmailMessage

STUDIO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(STUDIO))

import journal_bundle  # noqa: E402
import journal_mbox  # noqa: E402

DAY = "2026-11-06"
MAC = "00:e0:27:5b:31:40"


def make_bundle(root: pathlib.Path, mac: str | None = MAC) -> pathlib.Path:
    root.mkdir(parents=True, exist_ok=True)
    day = root / f"{DAY}.jsonl"
    stamp = int(dt.datetime(2026, 11, 6, 12, 0, tzinfo=dt.timezone.utc).timestamp() * 1000)
    day.write_text(json.dumps({
        "v": 1, "tsMs": stamp, "seq": 1, "type": "session.start",
        "data": {"system": "Test home", "mapHash": "0" * 64},
        "ts": "2026-11-06T12:00:00+00:00", "tzOffsetMinutes": 0,
    }) + "\n", encoding="utf-8")
    bundle = root / "bundle"
    archive = root / "Test-2026-11-06.tar.gz"
    journal_bundle.write_bundle(bundle, day, {}, "test", archive=archive, mac=mac)
    return archive


def add_message(box: mailbox.mbox, subject: str, attachment: pathlib.Path | None,
                filename: str | None = None, body: str = "bundle"):
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = "controller@example.com"
    message["To"] = "owner@example.com"
    message.set_content(body)
    if attachment is not None:
        message.add_attachment(attachment.read_bytes(), maintype="application",
                               subtype="gzip", filename=filename or attachment.name)
    box.add(message)


class MboxTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="rbr-mbox-")
        self.root = pathlib.Path(self._tmp.name)
        self.archive = make_bundle(self.root / "build")
        self.inbox = self.root / "inbox"

    def tearDown(self):
        self._tmp.cleanup()

    def _mbox(self, name="mail.mbox"):
        return self.root / name

    def test_extracts_a_valid_attachment_into_the_mac_folder(self):
        path = self._mbox()
        box = mailbox.mbox(str(path), create=True)
        add_message(box, f"RBR journal {MAC} {DAY}", self.archive)
        box.flush()
        box.close()
        stats = journal_mbox.extract(path, self.inbox, quiet=True)
        saved = self.inbox / MAC / self.archive.name
        self.assertTrue(saved.is_file())
        self.assertEqual(saved.read_bytes(), self.archive.read_bytes())
        self.assertEqual(stats["saved"], 1)
        self.assertEqual(stats["removed"], 0)

    def test_duplicate_attachment_is_not_written_twice(self):
        path = self._mbox()
        box = mailbox.mbox(str(path), create=True)
        add_message(box, f"RBR journal {MAC} {DAY}", self.archive)
        add_message(box, f"RBR journal {MAC} {DAY}", self.archive)
        box.flush()
        box.close()
        stats = journal_mbox.extract(path, self.inbox, quiet=True)
        self.assertEqual(stats["saved"], 1)
        self.assertEqual(stats["duplicates"], 1)
        self.assertEqual(len(list((self.inbox / MAC).iterdir())), 1)

    def test_subject_mac_falls_back_to_the_manifest(self):
        path = self._mbox()
        box = mailbox.mbox(str(path), create=True)
        add_message(box, "RBR journal", self.archive)
        box.flush()
        box.close()
        journal_mbox.extract(path, self.inbox, quiet=True)
        self.assertTrue((self.inbox / MAC / self.archive.name).is_file())

    def test_non_rbr_attachments_are_skipped(self):
        path = self._mbox()
        notes = self.root / "notes.txt"
        notes.write_text("not a bundle", encoding="utf-8")
        box = mailbox.mbox(str(path), create=True)
        add_message(box, "RBR journal", notes, filename="notes.txt")
        box.flush()
        box.close()
        stats = journal_mbox.extract(path, self.inbox, quiet=True)
        self.assertEqual(stats["saved"], 0)
        self.assertEqual(stats["skipped"], 0)
        self.assertFalse(self.inbox.exists())

    def test_dry_run_changes_nothing(self):
        path = self._mbox()
        box = mailbox.mbox(str(path), create=True)
        add_message(box, f"RBR journal {MAC} {DAY}", self.archive)
        box.flush()
        box.close()
        stats = journal_mbox.extract(path, self.inbox, dry_run=True, quiet=True)
        self.assertEqual(stats["saved"], 1)
        self.assertFalse(self.inbox.exists())

    def test_remove_rewrites_the_mailbox_without_the_handled_message(self):
        path = self._mbox()
        box = mailbox.mbox(str(path), create=True)
        add_message(box, f"RBR journal {MAC} {DAY}", self.archive)
        add_message(box, "Something else", None, body="keep me")
        box.flush()
        box.close()
        stats = journal_mbox.extract(path, self.inbox, remove=True, quiet=True)
        self.assertEqual(stats["removed"], 1)
        self.assertTrue((self.inbox / MAC / self.archive.name).is_file())
        remaining = mailbox.mbox(str(path))
        try:
            self.assertEqual(len(remaining), 1)
            key = next(iter(remaining.keys()))
            self.assertEqual(remaining.get_message(key)["Subject"], "Something else")
        finally:
            remaining.close()

    def test_system_filter_and_list_reads_mailbox_from_config(self):
        path = self._mbox()
        box = mailbox.mbox(str(path), create=True)
        add_message(box, f"RBR journal {MAC} {DAY}", self.archive)
        box.flush()
        box.close()
        config = self.root / "studio-config.json"
        config.write_text(json.dumps({
            "journalInbox": str(self.inbox),
            "systems": {MAC: "Home"},
            "mailboxes": {MAC: str(path)},
        }), encoding="utf-8")
        result = subprocess.run([
            sys.executable, str(STUDIO / "journal_mbox.py"),
            "--system", MAC, "--config", str(config), "--root", str(self.inbox),
            "--list", "--limit", "5", "--quiet",
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"JOURNAL {self.archive.name}", result.stdout)
        self.assertTrue((self.inbox / MAC / self.archive.name).is_file())

    def test_directory_of_mboxes_is_scanned(self):
        profile = self.root / "thunderbird-profile"
        folder = profile / "Mail" / "Local Folders"
        folder.mkdir(parents=True)
        path = folder / "RBR-journal"
        box = mailbox.mbox(str(path), create=True)
        add_message(box, f"RBR journal {MAC} {DAY}", self.archive)
        box.flush()
        box.close()
        config = self.root / "studio-config.json"
        config.write_text(json.dumps({
            "journalInbox": str(self.inbox),
            "systems": {MAC: "Home"},
            "mailboxes": {MAC: str(profile)},
        }), encoding="utf-8")
        result = subprocess.run([
            sys.executable, str(STUDIO / "journal_mbox.py"),
            "--system", MAC, "--config", str(config), "--root", str(self.inbox),
            "--list", "--limit", "5", "--quiet",
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"JOURNAL {self.archive.name}", result.stdout)
        self.assertTrue((self.inbox / MAC / self.archive.name).is_file())

    def test_missing_path_is_reported_without_a_traceback(self):
        result = subprocess.run([
            sys.executable, str(STUDIO / "journal_mbox.py"),
            "--mbox", str(self.root / "missing"), "--quiet",
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("no such mbox or folder", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("AttributeError", result.stderr)

    def test_cli_help_parses(self):
        result = subprocess.run(
            [sys.executable, str(STUDIO / "journal_mbox.py"), "--help"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--remove", result.stdout)


if __name__ == "__main__":
    unittest.main()
