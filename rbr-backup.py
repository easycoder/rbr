#!/usr/bin/env python3
"""rbr-backup.py — a restorable archive of the RBR controller and its Zigbee mesh.

Creates one ZIP holding the two things a fresh install cannot regenerate:

  * the controller's own state — map.json, its rolling history, the MQTT and
    mail credentials, the MAC override, zigbee-config.json and the backup
    settings;
  * Zigbee2MQTT's data directory — configuration.yaml (which carries the
    network key), database.db (the paired devices), coordinator_backup.json
    and any external converters.

The archive is restorable with rbr-restore.py. It deliberately contains
secrets: without the network key and the paired-device database a rebuilt
controller cannot rejoin the existing mesh, and without the MQTT credentials
it cannot reach the broker. Archives are written 0600 and are meant to be
treated as sensitive, whether they stay on the box or travel by email.

Scheduling
----------
Run as a one-shot from rbr-backup.service + rbr-backup.timer (installed by
rbr-setup.sh). The timer fires monthly; the service always writes a local
archive. Email is opt-in through the PWA's Backups sheet, which writes
backup-config.json:

    {"enabled": "on", "address": "owner@example.com"}

`--email-now` sends regardless of the toggle (the sheet's "Send a backup
now" button). `--no-email` never sends. With neither flag the toggle decides.

The recipient is the registered address: backup-config.json's `address`,
then the address the cloud holds for this controller (credentials.php, using
.mqtt_token), then `mail_to` in the local credentials file. Mail settings
come from the local `credentials` file and, where a value is missing there,
the cloud's copy. A real local value always wins: the cloud's host file can
still carry the placeholders from credentials.example.json, and letting those
override a working SMTP setup made every send report "not configured".

Usage
-----
    python3 rbr-backup.py [--dir RBR_DIR] [--z2m-dir DIR] [--out-dir DIR]
                         [--keep N] [--email-now | --no-email] [--to ADDR]
                         [--smtp-port PORT] [--quiet]

Exit status is 0 when the local archive was written, whether or not email
was configured or succeeded; 1 when the archive itself could not be created.
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import sqlite3
import socket
import subprocess
import sys
import tempfile
import urllib.parse
import zipfile

# The mail merge rule is shared with journal-export.py so the two senders
# cannot disagree about which credentials value wins.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rbr_mail  # noqa: E402 - beside this script, not on the caller's path

PREFIX = "rbr-backup-"
MANIFEST = "MANIFEST.json"
README = "README.txt"
FORMAT = 1
DEFAULT_KEEP = 12
DEFAULT_MAX_EMAIL_MB = 25

# Files that belong to this installation rather than to the release. The
# release itself is restorable from rbrheating.com, so no code is copied.
RBR_FILES = (
    "map.json",
    "map-last-good.json",
    "credentials",
    "zigbee-config.json",
    ".mac_override",
    ".mqtt_password",
    ".mqtt_token",
    "volatile-root",
    "heatlog-root",
    "journal-root",
    "journal-max-bytes",
    "journal-max-free-percent",
    "journal-export-config.json",
    "backup-config.json",
)
RBR_DIRS = ("map-history",)
Z2M_SKIP_DIRS = {"log", "logs", "node_modules"}
Z2M_SKIP_SUFFIXES = (".log", ".db-wal", ".db-shm", ".db-journal")


def log(message, quiet=False):
    if not quiet:
        print(f"backup: {message}", flush=True)


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def match_owner(path, template):
    """Give a root-written file the owner of the controller directory.

    The installed service runs as the controller user, where this does
    nothing. It matters when the archive is made by hand as root (or from the
    example unit): backup-status.json must stay readable by the controller,
    and the archive should belong to the person who owns the installation.
    """
    if not hasattr(os, "chown") or os.geteuid() != 0:
        return
    try:
        info = os.stat(template if os.path.exists(template) else os.path.dirname(template))
        os.chown(path, info.st_uid, info.st_gid)
    except OSError:
        pass


def atomic_write_json(path, data):
    """Write JSON via a temp file in the same directory, then rename."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".backup-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, path)
    except OSError:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# Kept here because the backup's tests and its own code speak these names;
# the implementations live in rbr_mail.py.
usable_mail_value = rbr_mail.usable_mail_value
mail_settings = rbr_mail.mail_settings
mail_problem = rbr_mail.mail_problem
resolve_recipient = rbr_mail.resolve_recipient


def z2m_data_dir(explicit):
    if explicit:
        return os.path.abspath(explicit)
    for candidate in ("/opt/zigbee2mqtt/data", "/userdata/zigbee2mqtt/data"):
        if os.path.isdir(candidate):
            return candidate
    return "/opt/zigbee2mqtt/data"


def snapshots_sqlite(src, dest):
    """Try a consistent SQLite copy; return dest on success, None otherwise."""
    try:
        uri = "file:%s?mode=ro" % urllib.parse.quote(os.path.abspath(src))
        source = sqlite3.connect(uri, uri=True, timeout=10)
        target = sqlite3.connect(dest)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        return dest
    except (sqlite3.Error, OSError):
        return None


def add_member(zf, src, arcname, manifest, snapshot_dir=None):
    """Add one file to the archive and record it in the manifest.

    A SQLite database is copied through SQLite's backup API first, so the
    archive holds a consistent snapshot even while Zigbee2MQTT is writing.
    """
    path = src
    if arcname.endswith("database.db") and snapshot_dir:
        fd, copy = tempfile.mkstemp(dir=snapshot_dir, prefix="z2m-db-", suffix=".db")
        os.close(fd)
        if snapshots_sqlite(src, copy):
            path = copy
        else:
            os.remove(copy)
    zf.write(path, arcname)
    manifest["files"].append({
        "path": arcname,
        "bytes": os.path.getsize(path),
        "sha256": sha256_file(path),
    })
    return path


def add_rbr_members(zf, rbr_dir, manifest, warnings):
    for name in RBR_FILES:
        path = os.path.join(rbr_dir, name)
        if os.path.isfile(path):
            add_member(zf, path, "rbr/" + name, manifest)
    for name in RBR_DIRS:
        root = os.path.join(rbr_dir, name)
        if not os.path.isdir(root):
            continue
        for folder, _dirs, files in os.walk(root):
            for member in sorted(files):
                path = os.path.join(folder, member)
                rel = os.path.relpath(path, rbr_dir)
                add_member(zf, path, "rbr/" + rel.replace(os.sep, "/"), manifest)
    if "map.json" not in [f["path"] for f in manifest["files"]]:
        warnings.append("map.json was not found — the archive has no plan")


def add_z2m_members(zf, z2m_dir, manifest, snapshot_dir, warnings):
    if not os.path.isdir(z2m_dir):
        warnings.append(f"Zigbee2MQTT data not found at {z2m_dir}")
        return
    for folder, dirs, files in os.walk(z2m_dir):
        dirs[:] = sorted(d for d in dirs if d not in Z2M_SKIP_DIRS)
        for member in sorted(files):
            if member.endswith(Z2M_SKIP_SUFFIXES):
                continue
            path = os.path.join(folder, member)
            rel = os.path.relpath(path, z2m_dir).replace(os.sep, "/")
            add_member(zf, path, "zigbee2mqtt/" + rel, manifest, snapshot_dir)
    if not any(f["path"] == "zigbee2mqtt/database.db" for f in manifest["files"]):
        warnings.append("Zigbee2MQTT's database.db was not found — paired devices may not restore")


def readme_text(hostname, z2m_dir):
    return f"""Room By Room — controller backup
================================

This archive was made on {hostname} and holds the controller's plan
(map.json and its history), its credentials and identity files, and the
Zigbee2MQTT data directory ({z2m_dir}) including the network key and the
paired-device database.

It therefore contains secrets. Keep it private: anyone holding this file can
join the Zigbee mesh and talk to the MQTT broker.

Restore it on a fresh install with:

    sudo python3 rbr-restore.py {PREFIX}...zip

rbr-restore.py stops the controller services, takes a snapshot of what is
already on the machine, unpacks the archive, restores the original ownership
and permissions, and starts the services again. Run it with --help for the
options.

The release code itself is not in this archive. A fresh install gets that
from rbrheating.com (get-controller.sh / rbr-updater.py).
"""


def create_archive(rbr_dir, z2m_dir, out_dir, keep, quiet):
    os.makedirs(out_dir, exist_ok=True)
    match_owner(out_dir, rbr_dir)
    now = datetime.datetime.now().astimezone()
    stamp = now.strftime("%Y%m%d-%H%M%S")
    archive = os.path.join(out_dir, f"{PREFIX}{stamp}.zip")

    fd, tmp = tempfile.mkstemp(dir=out_dir, prefix=".backup-", suffix=".zip")
    os.close(fd)
    snapshot_dir = tempfile.mkdtemp(prefix="rbr-backup-db-")
    warnings = []
    manifest = {
        "format": FORMAT,
        "created": now.isoformat(timespec="seconds"),
        "hostname": socket.gethostname(),
        "rbr_dir": os.path.abspath(rbr_dir),
        "z2m_dir": os.path.abspath(z2m_dir),
        "rbr_version": "",
        "files": [],
        "warnings": warnings,
    }
    version_file = os.path.join(rbr_dir, ".version")
    if os.path.isfile(version_file):
        with open(version_file, encoding="utf-8") as fh:
            manifest["rbr_version"] = fh.read().strip()

    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
            add_rbr_members(zf, rbr_dir, manifest, warnings)
            add_z2m_members(zf, z2m_dir, manifest, snapshot_dir, warnings)
            zf.writestr(README, readme_text(manifest["hostname"], z2m_dir))
            zf.writestr(MANIFEST, json.dumps(manifest, indent=2, sort_keys=True))
        os.chmod(tmp, 0o600)
        os.replace(tmp, archive)
        match_owner(archive, rbr_dir)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    finally:
        shutil.rmtree(snapshot_dir, ignore_errors=True)

    prune(out_dir, keep, archive, quiet)
    log(f"wrote {archive} ({os.path.getsize(archive)} bytes, "
        f"{len(manifest['files'])} files)")
    for warning in warnings:
        log(f"warning: {warning}", quiet)
    return archive, manifest, warnings


def prune(out_dir, keep, current, quiet):
    if keep <= 0:
        return
    entries = []
    for name in os.listdir(out_dir):
        if name.startswith(PREFIX) and name.endswith(".zip"):
            path = os.path.join(out_dir, name)
            if path != current:
                entries.append(path)
    entries.sort(key=os.path.getmtime)
    for path in entries[:max(0, len(entries) - (keep - 1))]:
        os.remove(path)
        log(f"pruned {os.path.basename(path)}", quiet)


def send_archive(archive, recipient, settings, quiet):
    """Email the archive. Returns (sent, error_message)."""
    subject = f"RBR backup — {socket.gethostname()} — {datetime.date.today().isoformat()}"
    body = (
        "Attached is the monthly backup of your Room By Room controller.\n\n"
        "It contains the heating plan, the Zigbee2MQTT data (including the "
        "network key) and the controller's credentials. Keep it private.\n\n"
        "To restore it on a fresh install:\n\n"
        f"    sudo python3 rbr-restore.py {os.path.basename(archive)}\n")
    return rbr_mail.send_files(settings, recipient, subject, body, [archive],
                               log=lambda message: log(message, quiet))


def write_status(path, archive, manifest, warnings, emailed, email_to, error):
    now = datetime.datetime.now().astimezone()
    status = {
        "last": now.isoformat(timespec="seconds"),
        "last_display": f"{now.day} {now.strftime('%b %Y at %H:%M')}",
        "ok": "yes",
        "archive": os.path.basename(archive),
        "bytes": os.path.getsize(archive),
        "files": len(manifest.get("files", [])),
        "emailed": "yes" if emailed else "no",
        "email_to": email_to,
        "error": error,
        "warnings": warnings,
    }
    atomic_write_json(path, status)
    match_owner(path, os.path.dirname(path))


def failure_status(path, error):
    now = datetime.datetime.now().astimezone()
    atomic_write_json(path, {
        "last": now.isoformat(timespec="seconds"),
        "last_display": f"{now.day} {now.strftime('%b %Y at %H:%M')}",
        "ok": "no",
        "emailed": "no",
        "error": str(error),
    })
    match_owner(path, os.path.dirname(path))


def main():
    parser = argparse.ArgumentParser(
        description="Create (and optionally email) a restorable RBR backup.")
    parser.add_argument("--dir", default=os.path.dirname(os.path.abspath(__file__)),
                        help="controller directory holding map.json (default: this script's)")
    parser.add_argument("--z2m-dir", default="",
                        help="Zigbee2MQTT data directory (default: autodetect)")
    parser.add_argument("--out-dir", default="",
                        help="where archives are written (default: <dir>/backup)")
    parser.add_argument("--keep", type=int, default=DEFAULT_KEEP,
                        help=f"archives to keep, 0 = all (default {DEFAULT_KEEP})")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--email-now", action="store_true",
                       help="email this backup even if the UI toggle is off")
    group.add_argument("--no-email", action="store_true",
                       help="never email this backup")
    parser.add_argument("--to", default="", help="override the recipient address")
    parser.add_argument("--smtp-port", type=int, default=0,
                       help="SMTP port (default: mail_port or 465)")
    parser.add_argument("--max-email-mb", type=int, default=DEFAULT_MAX_EMAIL_MB,
                        help=f"do not email archives larger than this (default {DEFAULT_MAX_EMAIL_MB})")
    parser.add_argument("--quiet", action="store_true",
                        help="only report changes and problems")
    args = parser.parse_args()

    rbr_dir = os.path.abspath(args.dir)
    z2m_dir = z2m_data_dir(args.z2m_dir)
    out_dir = os.path.abspath(args.out_dir or os.path.join(rbr_dir, "backup"))
    status_path = os.path.join(rbr_dir, "backup-status.json")

    try:
        archive, manifest, warnings = create_archive(
            rbr_dir, z2m_dir, out_dir, args.keep, args.quiet)
    except Exception as exc:  # noqa: BLE001 - the status file is the report
        log(f"failed: {exc}")
        failure_status(status_path, exc)
        return 1

    config = {}
    config_path = os.path.join(rbr_dir, "backup-config.json")
    if os.path.isfile(config_path):
        try:
            config = read_json(config_path)
        except (OSError, ValueError) as exc:
            warnings.append(f"backup-config.json is unreadable ({exc}); email left off")

    local = rbr_mail.load_local_credentials(
        rbr_dir, lambda message: log(message, args.quiet))
    cloud = rbr_mail.fetch_cloud(
        rbr_dir, lambda message: log(message, args.quiet))
    settings = mail_settings(local, cloud)
    if args.smtp_port:
        settings["mail_port"] = args.smtp_port
    recipient = resolve_recipient(args.to or config.get("address", ""), cloud, local)

    if args.email_now:
        want_email = True
    elif args.no_email:
        want_email = False
    else:
        want_email = str(config.get("enabled", "")).lower() in ("on", "true", "yes", "1")

    emailed, error = False, ""
    if want_email:
        if os.path.getsize(archive) > args.max_email_mb * 1024 * 1024:
            error = (f"archive is {os.path.getsize(archive)} bytes, over the "
                     f"{args.max_email_mb} MB mail limit — kept locally only")
        else:
            emailed, error = send_archive(archive, recipient, settings, args.quiet)
            if error:
                log(error)
    write_status(status_path, archive, manifest, warnings, emailed, recipient, error)
    return 0


if __name__ == "__main__":
    sys.exit(main())
