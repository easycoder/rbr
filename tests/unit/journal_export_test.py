#!/usr/bin/env python3
"""Tests for journal-export.py and its bundle compatibility with the importer."""

import datetime as dt
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
STUDIO = REPO / "tools" / "rbr-studio"
sys.path.insert(0, str(STUDIO))
import journal_bundle  # noqa: E402

spec = importlib.util.spec_from_file_location("journal_export", REPO / "journal-export.py")
journal_export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(journal_export)


class FakeSMTP:
    """The smallest SMTP client the sender touches, recording messages."""

    sent = []

    def __init__(self, host, port, timeout=None, context=None):
        self.host = host
        self.port = port

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def login(self, login, password):
        self.login_pair = (login, password)

    def starttls(self, context=None):
        pass

    def send_message(self, message):
        type(self).sent.append(message)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="rbr-export-test-")
        self.rbr_dir = pathlib.Path(self._tmp.name)
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

    def test_day_without_a_map_snapshot_carries_the_last_known_map(self):
        # The controller booted on an earlier day and the map did not change,
        # so this day's journal has no mapHash event of its own. The bundle
        # must still carry the map in force at midnight.
        day_dir = self.root / "2026" / "11"
        start = int(dt.datetime(2026, 11, 7, 0, 0, tzinfo=dt.timezone.utc).timestamp() * 1000)
        events = [
            {"v": 1, "tsMs": start, "seq": 10, "type": "room.state",
             "data": {"room": "Kitchen", "mode": "timed", "relay": "off"},
             "ts": "2026-11-07T00:00:00+00:00", "tzOffsetMinutes": 0},
            {"v": 1, "tsMs": start + 60000, "seq": 11, "type": "sensor.reading",
             "data": {"room": "Kitchen", "sensor": "k", "temp": 1850, "humidity": 50, "battery": 90},
             "ts": "2026-11-07T00:01:00+00:00", "tzOffsetMinutes": 0},
        ]
        (day_dir / "2026-11-07.jsonl").write_text(
            "".join(json.dumps(event, separators=(",", ":")) + "\n" for event in events),
            encoding="utf-8")
        archive, manifest = journal_export.export_day(
            self.root, dt.date(2026, 11, 7), self.out / "no-map", mode="scenario", keep=0)
        self.assertEqual([row["hash"] for row in manifest["maps"]], [self.digest])
        self.assertEqual(manifest["baseMapHash"], self.digest)
        opened = journal_bundle.open_bundle(archive)
        try:
            self.assertEqual(opened.load_map(self.digest)["name"], "Test")
        finally:
            opened.close()

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

    def test_now_exports_a_partial_bundle_into_the_requests_folder(self):
        today = dt.date.today()
        day_dir = self.root / f"{today.year:04d}" / f"{today.month:02d}"
        day_dir.mkdir(parents=True, exist_ok=True)
        source = self.root / "2026" / "11" / "2026-11-06.jsonl"
        target = day_dir / f"{today.isoformat()}.jsonl"
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        status = journal_export.main([
            "--root", str(self.root), "--now", "--no-email", "--dir", str(self.rbr_dir),
            "--quiet",
        ])
        self.assertEqual(status, 0)
        archives = list((self.root / "exports" / "requests").glob("*.tar.gz"))
        self.assertEqual(len(archives), 1, archives)
        opened = journal_bundle.open_bundle(archives[0])
        try:
            self.assertTrue(opened.manifest["partial"])
            self.assertRegex(opened.manifest["label"], r"^\d{2}:\d{2}:\d{2}$")
            self.assertEqual(opened.manifest["day"], today.isoformat())
        finally:
            opened.close()

    def test_partial_now_bundle_is_labelled_and_subject_carries_the_time(self):
        self.write_controller(None)
        archive, manifest = journal_export.export_day(
            self.root, self.day, self.out, partial=True, label="12:34:56",
            requested_at="2026-11-06T12:34:56+00:00", mac="00:e0:27:5b:31:40")
        self.assertTrue(archive.name.endswith("-123456.tar.gz"), archive.name)
        self.assertTrue(manifest["partial"])
        self.assertEqual(manifest["label"], "12:34:56")
        self.assertEqual(manifest["requestedAt"], "2026-11-06T12:34:56+00:00")
        with mock.patch.object(journal_export.rbr_mail, "fetch_cloud", return_value={}):
            with mock.patch.object(journal_export.rbr_mail, "send_files",
                                   return_value=(True, "")) as send:
                journal_export.send_bundle(
                    archive, manifest, {"address": "owner@example.com"},
                    self.rbr_dir, quiet=True)
        subject = send.call_args[0][2]
        self.assertEqual(subject,
                         "RBR journal 00:e0:27:5b:31:40 2026-11-06 12:34:56")

    def test_bundle_carries_the_day_heatlog_csvs(self):
        heatlog = pathlib.Path(self._tmp.name) / "heating-data"
        kitchen = heatlog / "Kitchen" / "2026" / "11"
        office = heatlog / "Office" / "2026" / "11"
        kitchen.mkdir(parents=True)
        office.mkdir(parents=True)
        (kitchen / "06.csv").write_text("30504123,207,205,p\n", encoding="utf-8")
        (office / "06.csv").write_text("30504123,200,190,c\n", encoding="utf-8")
        (kitchen / "05.csv").write_text("30504000,200,200,o\n", encoding="utf-8")

        archive, manifest = journal_export.export_day(
            self.root, self.day, self.out, heatlog_root=heatlog)
        self.assertEqual([row["room"] for row in manifest["reports"]], ["Kitchen", "Office"])
        self.assertTrue(all(row["kind"] == "heatlog" for row in manifest["reports"]))

        opened = journal_bundle.open_bundle(archive)
        try:
            self.assertEqual(
                (opened.reports_dir / "heatlog" / "Kitchen" / "2026" / "11" / "06.csv")
                .read_text(encoding="utf-8"),
                "30504123,207,205,p\n")
            self.assertFalse(
                (opened.reports_dir / "heatlog" / "Kitchen" / "2026" / "11" / "05.csv").exists())
        finally:
            opened.close()

    def test_bundle_without_heatlog_root_has_no_reports(self):
        _, manifest = journal_export.export_day(
            self.root, self.day, self.out, heatlog_root=None)
        self.assertEqual(manifest["reports"], [])

    # --- email delivery -------------------------------------------------

    def write_controller(self, config=None, **credentials):
        base = {
            "mail_server": "smtp.example.net",
            "mail_port": 465,
            "mail_login": "login@example.net",
            "mail_password": "secret",
            "mail_from": "login@example.net",
        }
        base.update(credentials)
        (self.rbr_dir / "credentials").write_text(json.dumps(base), encoding="utf-8")
        path = self.rbr_dir / "journal-export-config.json"
        if config is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(json.dumps(config), encoding="utf-8")

    def run_export(self, *extra):
        FakeSMTP.sent = []
        arguments = ["--root", str(self.root), "--day", "2026-11-06",
                     "--out", str(self.out), "--dir", str(self.rbr_dir), "--quiet"]
        arguments.extend(extra)
        with mock.patch.object(journal_export.rbr_mail, "fetch_cloud", return_value={}):
            with mock.patch.object(journal_export.rbr_mail.smtplib, "SMTP", FakeSMTP):
                with mock.patch.object(journal_export.rbr_mail.smtplib, "SMTP_SSL", FakeSMTP):
                    return journal_export.main(arguments)

    def test_enabled_config_emails_the_exported_bundle(self):
        self.write_controller({"enabled": "yes", "address": "owner@example.com"})
        (self.rbr_dir / ".mac_override").write_text("00:e0:27:5b:31:40\n", encoding="utf-8")
        status = self.run_export()
        self.assertEqual(status, 0)
        self.assertEqual(len(FakeSMTP.sent), 1)
        message = FakeSMTP.sent[0]
        self.assertEqual(message["Subject"], "RBR journal 00:e0:27:5b:31:40 2026-11-06")
        self.assertEqual(message["To"], "owner@example.com")
        attachments = list(message.iter_attachments())
        self.assertEqual(len(attachments), 1)
        self.assertTrue(attachments[0].get_filename().endswith(".tar.gz"))
        archive = next(self.out.glob("*.tar.gz"))
        self.assertEqual(attachments[0].get_content(), archive.read_bytes())
        opened = journal_bundle.open_bundle(archive)
        try:
            self.assertEqual(opened.manifest["mac"], "00:e0:27:5b:31:40")
        finally:
            opened.close()

    def test_email_stays_off_without_an_enabled_config(self):
        self.write_controller(None)
        self.run_export()
        self.assertEqual(FakeSMTP.sent, [])
        self.write_controller({"enabled": "no", "address": "owner@example.com"})
        self.run_export("--force")
        self.assertEqual(FakeSMTP.sent, [])

    def test_flags_override_the_config(self):
        self.write_controller({"enabled": "no", "address": "owner@example.com"})
        self.run_export("--email-now")
        self.assertEqual(len(FakeSMTP.sent), 1)
        self.write_controller({"enabled": "yes", "address": "owner@example.com"})
        self.run_export("--no-email", "--force")
        self.assertEqual(FakeSMTP.sent, [])

    def test_a_send_failure_leaves_the_archive_and_exits_zero(self):
        self.write_controller({"enabled": "yes"})
        status = self.run_export()
        self.assertEqual(status, 0)
        self.assertEqual(FakeSMTP.sent, [])
        self.assertTrue(any(self.out.glob("*.tar.gz")))


if __name__ == "__main__":
    unittest.main()
