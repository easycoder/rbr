#!/usr/bin/env python3
"""
bundle_copy_test.py - checks for the rbr-bundle-copy service.

Builds small valid journal bundles in a temporary directory and drives the
service's one-pass mode against an mbox and a folder of saved attachments.
Checks the yearly destination, byte-for-byte copying, the skip-existing rule,
the dry-run mode, and the config/schedule helpers.

Run directly:  python3 tests/unit/bundle_copy_test.py
or as part of: tests/unit/run-unit-tests.sh
"""

import contextlib
import datetime
import email.message
import importlib.util
import io
import json
import mailbox
import pathlib
import tarfile
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO / "rbr-bundle-copy.py"
MAC = "00:e0:27:5b:31:40"


def load_module():
    spec = importlib.util.spec_from_file_location("rbr_bundle_copy", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_bundle(day, mac=MAC, system="QED6"):
    """A minimal valid journal bundle, as the controller emails it."""
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w:gz") as tar:
        manifest = json.dumps({
            "format": "rbr-journal-bundle",
            "version": 1,
            "day": day,
            "mac": mac,
            "system": system,
        }).encode("utf-8")
        info = tarfile.TarInfo("manifest.json")
        info.size = len(manifest)
        tar.addfile(info, io.BytesIO(manifest))
        events = b'{"type":"session.start","data":{"system":"QED6"}}\n'
        info = tarfile.TarInfo("events/%s/%s/%s.jsonl"
                               % (day[:4], day[5:7], day))
        info.size = len(events)
        tar.addfile(info, io.BytesIO(events))
    return raw.getvalue()


def write_config(path, email_path, save_path, run_at="03:30"):
    path.write_text(
        "[bundle-copy]\n"
        "email_path = %s\n"
        "save_path = %s\n"
        "run_at = %s\n" % (email_path, save_path, run_at),
        encoding="utf-8")


class BundleCopyTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.temp = tempfile.TemporaryDirectory(prefix="rbr-bundle-copy-test-")
        self.root = pathlib.Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _mbox(self, messages, name="QED6", parent=None):
        path = (parent or self.root) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        box = mailbox.mbox(str(path))
        try:
            for subject, filename, payload in messages:
                message = email.message.EmailMessage()
                message["Subject"] = subject
                message["From"] = "controller@example.test"
                message["To"] = "owner@example.test"
                message.set_content("RBR journal bundle")
                message.add_attachment(payload, maintype="application",
                                       subtype="gzip", filename=filename)
                box.add(message)
            box.flush()
        finally:
            box.close()
        return path

    def test_mbox_copies_to_installation_year_and_skips_existing(self):
        payload = make_bundle("2026-11-07")
        mbox = self._mbox([
            ("RBR journal %s 2026-11-07" % MAC, "qed6-2026-11-07.tar.gz", payload),
            ("RBR journal %s 2026-11-08" % MAC, "broken.tar.gz", b"not a tarball"),
        ])
        archive = self.root / "archive"

        stats = self.module.run_once(mbox, archive, quiet=True)
        target = archive / "QED6" / "2026" / "qed6-2026-11-07.tar.gz"
        self.assertEqual(stats["copied"], 1)
        self.assertEqual(stats["invalid"], 1)
        self.assertTrue(target.is_file())
        self.assertEqual(target.read_bytes(), payload)
        self.assertFalse((archive / "2026").exists())
        self.assertFalse((archive / "QED6" / "2026" / "broken.tar.gz").exists())

        before = target.stat().st_mtime_ns
        stats = self.module.run_once(mbox, archive, quiet=True)
        self.assertEqual(stats["copied"], 0)
        self.assertEqual(stats["existing"], 1)
        self.assertEqual(target.stat().st_mtime_ns, before)

    def test_multiple_installations_in_a_parent_folder(self):
        parent = self.root / "Bundles.sbd"
        first = make_bundle("2026-11-07", system="Different")
        second = make_bundle("2026-11-08", mac="aa:bb:cc:dd:ee:ff", system="Whatever")
        self._mbox([
            ("RBR journal %s 2026-11-07" % MAC, "bundle.tar.gz", first),
        ], name="QED6", parent=parent)
        self._mbox([
            ("RBR journal aa:bb:cc:dd:ee:ff 2026-11-08", "bundle.tar.gz", second),
        ], name="OTHER", parent=parent)
        archive = self.root / "archive"

        stats = self.module.run_once(parent, archive, quiet=True)
        self.assertEqual(stats["copied"], 2)
        self.assertTrue((archive / "QED6" / "2026" / "bundle.tar.gz").is_file())
        self.assertTrue((archive / "OTHER" / "2026" / "bundle.tar.gz").is_file())
        self.assertEqual((archive / "QED6" / "2026" / "bundle.tar.gz").read_bytes(),
                         first)
        self.assertEqual((archive / "OTHER" / "2026" / "bundle.tar.gz").read_bytes(),
                         second)

    def test_bare_attachments_and_dry_run(self):
        payload = make_bundle("2026-11-09", mac="aa:bb:cc:dd:ee:ff", system="Other")
        source = self.root / "saved-attachments"
        source.mkdir()
        (source / "other-2026-11-09.tar.gz").write_bytes(payload)
        archive = self.root / "archive"

        stats = self.module.run_once(source, archive, dry_run=True, quiet=True)
        self.assertEqual(stats["would-copy"], 1)
        self.assertFalse((archive / "Other" / "2026" / "other-2026-11-09.tar.gz").exists())

        stats = self.module.run_once(source, archive, quiet=True)
        self.assertEqual(stats["copied"], 1)
        self.assertEqual(
            (archive / "Other" / "2026" / "other-2026-11-09.tar.gz").read_bytes(),
            payload)

        single = self.root / "single-2026-11-09.tar.gz"
        single.write_bytes(payload)
        archive = self.root / "archive-single"
        stats = self.module.run_once(single, archive, quiet=True)
        self.assertEqual(stats["copied"], 1)
        self.assertTrue((archive / "Other" / "2026" / "single-2026-11-09.tar.gz").is_file())

    def test_config_and_schedule_helpers(self):
        config = self.root / "bundle-copy.conf"
        write_config(config, self.root / "mail", self.root / "archive", "3:05")
        settings = self.module.load_config(config)
        self.assertEqual(settings["email_path"], self.root / "mail")
        self.assertEqual(settings["save_path"], self.root / "archive")
        self.assertEqual(settings["run_at"], datetime.time(3, 5))

        self.assertEqual(self.module.parse_run_at("03:30"), datetime.time(3, 30))
        with self.assertRaises(ValueError):
            self.module.parse_run_at("24:00")
        with self.assertRaises(ValueError):
            self.module.parse_run_at("quarter past three")

        before = datetime.datetime(2026, 11, 9, 2, 0)
        after = datetime.datetime(2026, 11, 9, 4, 0)
        self.assertEqual(self.module._next_run(before, datetime.time(3, 30)),
                         datetime.datetime(2026, 11, 9, 3, 30))
        self.assertEqual(self.module._next_run(after, datetime.time(3, 30)),
                         datetime.datetime(2026, 11, 10, 3, 30))

        self.assertEqual(self.module._safe_name("../../evil.tar.gz", "", {"day": "2026-11-07"}),
                         "evil.tar.gz")
        self.assertEqual(self.module._safe_name("", MAC, {"day": "2026-11-07"}),
                         "00-e0-27-5b-31-40-2026-11-07.tar.gz")
        self.assertEqual(self.module._year({"day": "2026-11-07"}), "2026")
        self.assertEqual(self.module._safe_folder("QED6"), "QED6")
        self.assertEqual(self.module._safe_folder("00:e0:27:5b:31:40"),
                         "00-e0-27-5b-31-40")
        self.assertEqual(self.module._safe_folder("../x"), "x")
        self.assertEqual(self.module._safe_folder(""), "")
        self.assertEqual(self.module._manifest_installation({"system": "QED6"}), "QED6")
        self.assertEqual(self.module._manifest_installation({"mac": MAC}),
                         "00-e0-27-5b-31-40")
        self.assertEqual(self.module._manifest_installation({}), "rbr")

    def test_missing_mail_path_fails_the_once_mode(self):
        config = self.root / "missing.conf"
        write_config(config, self.root / "no-such-mail", self.root / "archive")
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            status = self.module.main(["--once", "--config", str(config)])
        self.assertEqual(status, 1)
        with self.assertRaises(FileNotFoundError):
            self.module.run_once(self.root / "no-such-mail", self.root / "archive",
                                 quiet=True)


if __name__ == "__main__":
    unittest.main()
