#!/usr/bin/env python3
"""Tests for rbr-backup.py and rbr-restore.py.

The archive is the thing that has to work on a bad day, so these tests
exercise the two properties that matter rather than the CLI text: a backup
contains what a restore needs (including the secrets that rejoin the mesh,
and nothing from the release), and restoring it onto a fresh directory
reproduces the files, their permissions, and a usable map.
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


backup = load_module("rbr_backup", "rbr-backup.py")
restore = load_module("rbr_restore", "rbr-restore.py")

CONTROLLER = os.path.join(ROOT, "controller.allspeak")

PROBE_HEADER = """\
info `backup state probe`

script BackupStateProbe

dictionary Map
dictionary B
dictionary BackupConfig
variable BackupConfigText
dictionary BackupInfo
dictionary BackupInfoCopy
variable BackupInfoText
dictionary BackupStatus
variable BackupStatusText
variable BackupAddress
variable BackupEnabled
variable LastBackupInfoText
variable MapHasChanged

put `{}` into Map
gosub to LoadBackupState
put `{}` into B
if Map has entry `backup` put entry `backup` of Map into B
if B has entry `enabled` log `PROBE enabled=` cat entry `enabled` of B
else log `PROBE enabled=`
if B has entry `address` log `PROBE address=` cat entry `address` of B
else log `PROBE address=`
if B has entry `last_display` log `PROBE last=` cat entry `last_display` of B
else log `PROBE last=`
if B has entry `emailed` log `PROBE emailed=` cat entry `emailed` of B
else log `PROBE emailed=`
! The second call is the steady-state path. It must compare cleanly and
! leave the published record alone.
gosub to LoadBackupState
log `PROBE done`
stop
"""


def extract_routine(label):
    """Return the routine and its body, verbatim, from controller.allspeak."""
    with open(CONTROLLER, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    try:
        start = lines.index(label + ":")
    except ValueError:
        raise AssertionError(f"{label}: not found at column 0 in controller.allspeak")
    end = start + 1
    while end < len(lines) and not lines[end].startswith("!! "):
        end += 1
    return "\n".join(lines[start:end]).rstrip()


class Fixture:
    def __init__(self, base):
        self.rbr = os.path.join(base, "rbr")
        self.z2m = os.path.join(base, "zigbee2mqtt", "data")
        self.out = os.path.join(self.rbr, "backup")
        os.makedirs(os.path.join(self.rbr, "map-history"), exist_ok=True)
        os.makedirs(os.path.join(self.z2m, "log"), exist_ok=True)
        os.makedirs(os.path.join(self.z2m, "external_converters"), exist_ok=True)

        self.map = {
            "name": "Test System",
            "profile": 0,
            "rooms": [{"name": "Kitchen", "sensor": "AA:BB", "relays": ["Relay"]}],
            "profiles": [{"name": "Default", "rooms": {"Kitchen": {"mode": "timed"}}}],
        }
        self.write("map.json", self.map)
        self.write("map-last-good.json", self.map)
        self.write("map-history/map-20260101-010101.json", self.map)
        self.write("credentials", {
            "broker": "localhost", "port": 1883,
            "username": "user", "password": "mqtt-secret",
            "mail_server": "smtp.example.com", "mail_login": "noreply@example.com",
            "mail_password": "", "mail_from": "noreply@example.com",
        })
        self.write("zigbee-config.json", {"password": "zigbee-secret"})
        self.write(".mac_override", "aa:bb:cc:dd:ee:ff\n", raw=True)
        self.write(".mqtt_token", "token-secret\n", raw=True)
        self.write(".mqtt_password", "mqtt-password\n", raw=True)
        self.write(".version", "2611010000\n", raw=True)
        self.write("backup-config.json", {"enabled": "off", "address": "owner@example.com"})
        self.write("controller.allspeak", "! code is restored from the release, not here\n", raw=True)

        self.write_z2m("configuration.yaml",
                       "advanced:\n  network_key: SECRET-KEY\n")
        self.write_z2m("coordinator_backup.json", {"key": "coordinator-secret"})
        self.write_z2m("log/2026-11-01.log", "noise\n", raw=True)
        self.write_z2m("external_converters/custom.js", "// converter\n", raw=True)
        conn = sqlite3.connect(os.path.join(self.z2m, "database.db"))
        conn.execute("CREATE TABLE devices (ieee TEXT PRIMARY KEY)")
        conn.execute("INSERT INTO devices VALUES ('0x00124b00')")
        conn.commit()
        conn.close()

    def write(self, rel, value, raw=False):
        path = os.path.join(self.rbr, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(value if raw else json.dumps(value))

    def write_z2m(self, rel, value, raw=False):
        path = os.path.join(self.z2m, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(value if raw else json.dumps(value))


class BackupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def make(self, keep=12):
        return backup.create_archive(self.fx.rbr, self.fx.z2m, self.fx.out, keep, quiet=True)

    def test_archive_has_state_secrets_and_no_release_code(self):
        archive, manifest, warnings = self.make()
        self.assertTrue(os.path.isfile(archive))
        self.assertEqual(stat.S_IMODE(os.stat(archive).st_mode), 0o600)
        with zipfile.ZipFile(archive) as zf:
            names = set(zf.namelist())
            self.assertIn("rbr/map.json", names)
            self.assertIn("rbr/map-history/map-20260101-010101.json", names)
            self.assertIn("rbr/credentials", names)
            self.assertIn("rbr/.mqtt_token", names)
            self.assertIn("zigbee2mqtt/configuration.yaml", names)
            self.assertIn("zigbee2mqtt/database.db", names)
            self.assertIn("zigbee2mqtt/coordinator_backup.json", names)
            self.assertIn("zigbee2mqtt/external_converters/custom.js", names)
            self.assertNotIn("zigbee2mqtt/log/2026-11-01.log", names)
            self.assertNotIn("rbr/controller.allspeak", names)
            self.assertIn(backup.MANIFEST, names)
            self.assertIn(backup.README, names)
            stored = json.loads(zf.read(backup.MANIFEST))
            self.assertEqual(stored["rbr_version"], "2611010000")
            self.assertTrue(stored["files"])
        self.assertEqual(manifest["format"], 1)
        self.assertFalse([w for w in warnings if "database.db" in w])

    def test_sqlite_snapshot_is_readable(self):
        archive, _manifest, _warnings = self.make()
        with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(archive) as zf:
            target = os.path.join(tmp, "database.db")
            with open(target, "wb") as fh:
                fh.write(zf.read("zigbee2mqtt/database.db"))
            conn = sqlite3.connect(target)
            rows = conn.execute("SELECT ieee FROM devices").fetchall()
            conn.close()
        self.assertEqual(rows, [("0x00124b00",)])

    def test_retention_keeps_the_newest_archives(self):
        os.makedirs(self.fx.out, exist_ok=True)
        old = []
        for index in range(3):
            path = os.path.join(self.fx.out, f"{backup.PREFIX}2026010{index}-000000.zip")
            with open(path, "wb") as fh:
                fh.write(b"old")
            os.utime(path, (index + 1, index + 1))
            old.append(path)
        current = os.path.join(self.fx.out, f"{backup.PREFIX}20260201-000000.zip")
        with open(current, "wb") as fh:
            fh.write(b"new")
        backup.prune(self.fx.out, 2, current, quiet=True)
        remaining = sorted(name for name in os.listdir(self.fx.out)
                           if name.startswith(backup.PREFIX))
        self.assertEqual(remaining, [os.path.basename(old[-1]), os.path.basename(current)])

    def test_local_mail_settings_win_over_cloud_placeholders(self):
        local = {
            "mail_server": "smtp.pobox.com", "mail_login": "gt@pobox.com",
            "mail_password": "real-secret", "mail_from": "gt@pobox.com",
        }
        cloud = {
            "mail_server": "smtp.example.com",
            "mail_login": "noreply@rbrheating.com",
            "mail_password": "REPLACE_WITH_SMTP_PASSWORD",
            "mail_from": "noreply@rbrheating.com",
        }
        settings = backup.mail_settings(local, cloud)
        self.assertEqual(settings["mail_server"], "smtp.pobox.com")
        self.assertEqual(settings["mail_password"], "real-secret")
        self.assertEqual(backup.mail_problem(settings), "")

    def test_cloud_fills_only_what_the_local_file_has_not_configured(self):
        local = {
            "mail_server": "smtp.example.com", "mail_login": "",
            "mail_password": "", "mail_from": "",
        }
        cloud = {
            "mail_server": "smtp.real.example.net", "mail_login": "login",
            "mail_password": "secret", "mail_from": "from@example.net",
        }
        settings = backup.mail_settings(local, cloud)
        self.assertEqual(settings["mail_server"], "smtp.real.example.net")
        self.assertEqual(settings["mail_login"], "login")
        self.assertEqual(settings["mail_password"], "secret")

    def test_mail_problem_names_the_missing_or_placeholder_field(self):
        self.assertIn("mail_server", backup.mail_problem({}))
        self.assertIn("mail_server", backup.mail_problem({
            "mail_server": "smtp.example.com", "mail_login": "x", "mail_password": "y"}))
        self.assertIn("mail_password", backup.mail_problem({
            "mail_server": "smtp.real.example.net", "mail_login": "x",
            "mail_password": "REPLACE_WITH_SMTP_PASSWORD"}))
        self.assertEqual(backup.mail_problem({
            "mail_server": "smtp.real.example.net", "mail_login": "x",
            "mail_password": "y"}), "")

    def test_recipient_prefers_config_then_cloud_then_local(self):
        self.assertEqual(
            backup.resolve_recipient("me@example.com", {"email": "cloud@example.com"},
                                     {"mail_to": "local@example.com"}),
            "me@example.com")
        self.assertEqual(
            backup.resolve_recipient("", {"email": "cloud@example.com"},
                                     {"mail_to": "local@example.com"}),
            "cloud@example.com")
        self.assertEqual(backup.resolve_recipient("", {}, {"mail_to": "local@example.com"}),
                         "local@example.com")
        self.assertEqual(backup.resolve_recipient("", {}, {}), "")

    def test_restore_round_trip_into_a_fresh_install(self):
        archive, _manifest, _warnings = self.make()
        fresh_rbr = os.path.join(self.tmp.name, "fresh", "rbr")
        fresh_z2m = os.path.join(self.tmp.name, "fresh", "zigbee2mqtt", "data")
        os.makedirs(fresh_rbr)
        os.makedirs(fresh_z2m)
        # An existing file must be kept in the pre-restore snapshot.
        with open(os.path.join(fresh_rbr, "map.json"), "w", encoding="utf-8") as fh:
            fh.write('{"profiles": []}')

        argv = ["rbr-restore.py", archive, "--dir", fresh_rbr,
                "--z2m-dir", fresh_z2m, "--yes", "--no-services"]
        out = io.StringIO()
        with contextlib.redirect_stdout(out), \
                mock.patch.object(sys, "argv", argv):
            result = restore.main()
        self.assertEqual(result, 0, out.getvalue())

        with open(os.path.join(fresh_rbr, "map.json"), encoding="utf-8") as fh:
            restored_map = json.load(fh)
        with open(os.path.join(fresh_rbr, "credentials"), encoding="utf-8") as fh:
            restored_creds = json.load(fh)
        self.assertEqual(restored_map["name"], "Test System")
        self.assertEqual(restored_creds["password"], "mqtt-secret")
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(fresh_rbr, "credentials")).st_mode), 0o640)
        self.assertTrue(os.path.isfile(os.path.join(fresh_z2m, "database.db")))
        self.assertTrue(os.path.isfile(os.path.join(fresh_z2m, "configuration.yaml")))
        snapshots = [name for name in os.listdir(fresh_rbr) if name.startswith("pre-restore-")]
        self.assertEqual(len(snapshots), 1)
        snap_map = os.path.join(fresh_rbr, snapshots[0], "rbr", "map.json")
        with open(snap_map, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), {"profiles": []})

    def test_restore_refuses_a_path_that_escapes(self):
        nasty = os.path.join(self.fx.out, "nasty.zip")
        os.makedirs(self.fx.out, exist_ok=True)
        with zipfile.ZipFile(nasty, "w") as zf:
            zf.writestr(backup.MANIFEST, json.dumps({"format": 1, "files": []}))
            zf.writestr("rbr/../evil.txt", "x")
        with zipfile.ZipFile(nasty) as zf:
            with self.assertRaises(ValueError):
                restore.safe_members(zf)

    def test_restore_refuses_a_checksum_mismatch(self):
        archive, _manifest, _warnings = self.make()
        tampered = os.path.join(self.fx.out, "tampered.zip")
        with zipfile.ZipFile(archive) as src, zipfile.ZipFile(tampered, "w") as dst:
            for info in src.infolist():
                blob = src.read(info)
                if info.filename == "rbr/map.json":
                    blob = blob.replace(b"Test System", b"Other System")
                dst.writestr(info, blob)
        with zipfile.ZipFile(tampered) as zf:
            members = restore.safe_members(zf)
            with self.assertRaises(ValueError):
                restore.verify_archive(zf, members)


class BackupStateProbeTest(unittest.TestCase):
    """Run the controller's own LoadBackupState, not a mirrored copy.

    The first version of this routine compared an unset LastBackupInfoText on
    the live controller and stopped every start with "Both items must have a
    value for comparison". Compiling does not catch that, so this probe does:
    it calls the extracted routine twice with no backup files at all, then with
    the two files populated.
    """

    def run_probe(self, files):
        binary = os.environ.get("ALLSPEAK", "allspeak")
        if not shutil.which(binary.split()[0]):
            raise unittest.SkipTest(f"{binary} not found — install AllSpeak to run this test")
        with tempfile.TemporaryDirectory() as tmp:
            for name, content in files.items():
                with open(os.path.join(tmp, name), "w", encoding="utf-8") as fh:
                    fh.write(content)
            probe = os.path.join(tmp, "backup-state-probe.allspeak")
            with open(probe, "w", encoding="utf-8") as fh:
                fh.write(PROBE_HEADER + "\n" + extract_routine("LoadBackupState")
                         + "\n\nscript end\n")
            proc = subprocess.run([binary, probe], cwd=tmp, capture_output=True,
                                  text=True, timeout=60)
        output = proc.stdout + proc.stderr
        self.assertNotIn("Compile error", output)
        self.assertNotIn("Runtime Error", output)
        self.assertIn("PROBE done", output)
        return output

    def test_unset_status_text_is_safe_on_the_first_call(self):
        self.run_probe({})

    def test_config_and_status_populate_the_published_record(self):
        output = self.run_probe({
            "backup-config.json": json.dumps({"enabled": "on", "address": "owner@example.com"}),
            "backup-status.json": json.dumps({
                "last_display": "1 Nov 2026 at 03:00", "emailed": "yes", "ok": "yes"}),
        })
        self.assertIn("PROBE enabled=on", output)
        self.assertIn("PROBE address=owner@example.com", output)
        self.assertIn("PROBE last=1 Nov 2026 at 03:00", output)
        self.assertIn("PROBE emailed=yes", output)


if __name__ == "__main__":
    unittest.main()
