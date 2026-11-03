#!/usr/bin/env python3
"""rbr-restore.py — restore an archive made by rbr-backup.py.

Intended for the moment after a fresh install, when the controller and
Zigbee2MQTT have been set up but the house's plan, credentials and Zigbee
mesh are missing. The archive is the one rbr-backup.py wrote (or emailed).

What it does, in order:

  1. validates the archive — its manifest, every file's SHA-256, and that no
     member can escape the destination directories;
  2. prints what it is about to restore and asks for confirmation, unless
     --yes was given;
  3. stops controller.service, rbr-zigbee-bridge.service and
     zigbee2mqtt.service (if systemd is available);
  4. copies whatever is already in the destination into
     <rbr-dir>/pre-restore-<timestamp>/ first, so the restore itself is
     reversible;
  5. unpacks the controller files over the controller directory and the
     Zigbee2MQTT data over its data directory, restoring the archive's
     ownership and permissions (credentials stay private);
  6. starts the services again and reports whether map.json is usable.

Usage
-----
    sudo python3 rbr-restore.py rbr-backup-20261101-030000.zip
    sudo python3 rbr-restore.py backup.zip --dir ~/rbr --z2m-dir /opt/zigbee2mqtt/data

--dry-run lists the files and changes nothing. --no-services leaves the
services alone, for a machine where they are not installed or are managed
some other way.
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

MANIFEST = "MANIFEST.json"
FORMAT = 1
STOP_SERVICES = ("controller.service", "rbr-zigbee-bridge.service",
                 "zigbee2mqtt.service")
START_SERVICES = ("zigbee2mqtt.service", "rbr-zigbee-bridge.service",
                  "controller.service")
PRIVATE_FILES = {
    "credentials": 0o640,
    ".mqtt_password": 0o600,
    ".mqtt_token": 0o600,
    ".mac_override": 0o644,
}


def log(message):
    print(f"restore: {message}", flush=True)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def z2m_data_dir(explicit):
    if explicit:
        return os.path.abspath(explicit)
    for candidate in ("/opt/zigbee2mqtt/data", "/userdata/zigbee2mqtt/data"):
        if os.path.isdir(candidate):
            return candidate
    return "/opt/zigbee2mqtt/data"


def safe_members(zf):
    """[(ZipInfo, 'rbr'|'zigbee2mqtt', relative path)] with escape checks."""
    members = []
    seen = set()
    for info in zf.infolist():
        name = info.filename
        if name in (MANIFEST, "README.txt"):
            continue
        if name.endswith("/"):
            continue
        if name.startswith("/") or "\\" in name:
            raise ValueError(f"unsafe path in archive: {name}")
        parts = name.split("/")
        if any(part in ("", ".", "..") for part in parts):
            raise ValueError(f"unsafe path in archive: {name}")
        if parts[0] not in ("rbr", "zigbee2mqtt"):
            raise ValueError(f"unexpected member in archive: {name}")
        if name in seen:
            raise ValueError(f"duplicate member in archive: {name}")
        seen.add(name)
        mode = info.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise ValueError(f"symbolic link in archive: {name}")
        members.append((info, parts[0], "/".join(parts[1:])))
    if not members:
        raise ValueError("archive contains no files")
    return members


def verify_archive(zf, members):
    """Check the manifest and every recorded digest. Returns (manifest, data)."""
    try:
        manifest = json.loads(zf.read(MANIFEST))
    except KeyError:
        raise ValueError(f"{MANIFEST} is missing — this is not an RBR backup")
    if manifest.get("format") != FORMAT:
        raise ValueError(f"unsupported backup format {manifest.get('format')!r}")
    recorded = {entry["path"]: entry for entry in manifest.get("files", [])}
    data = {}
    for info, root, rel in members:
        blob = zf.read(info)
        arcname = f"{root}/{rel}"
        entry = recorded.get(arcname)
        if entry is None:
            raise ValueError(f"{arcname} is not in the manifest")
        if entry.get("bytes") != len(blob) or entry.get("sha256") != sha256_bytes(blob):
            raise ValueError(f"{arcname} does not match its recorded checksum")
        data[(root, rel)] = blob
    missing = set(recorded) - {f"{root}/{rel}" for root, rel in data}
    if missing:
        raise ValueError("archive is missing " + ", ".join(sorted(missing)))
    return manifest, data


def map_summary(blob):
    """(profiles, rooms) if this looks like a usable map, else raise."""
    try:
        data = json.loads(blob)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError(f"map.json is not valid JSON ({exc})")
    if not isinstance(data, dict) or not isinstance(data.get("profiles"), list):
        raise ValueError("map.json has no profiles list")
    rooms = data.get("rooms")
    return len(data["profiles"]), len(rooms) if isinstance(rooms, list) else 0


def run_systemctl(action, services):
    try:
        result = subprocess.run(["systemctl", action, *services],
                                capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        log(f"systemctl {action} failed: {exc}")
        return False
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        log(f"systemctl {action} {', '.join(services)}: "
            f"{detail[0] if detail else 'failed'}")
        return False
    log(f"systemctl {action}: {', '.join(services)}")
    return True


def snapshot_existing(entries, rbr_dir, stamp, dry_run):
    """Copy files about to be overwritten into pre-restore-<stamp>."""
    root = os.path.join(rbr_dir, f"pre-restore-{stamp}")
    saved = 0
    for dest, _root_name, rel, _info in entries:
        if not os.path.isfile(dest):
            continue
        saved += 1
        if dry_run:
            continue
        target = os.path.join(root, _root_name, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(dest, target)
    if saved and not dry_run:
        log(f"kept {saved} existing file(s) in {root}")
    return saved


def destination_owner(path):
    try:
        info = os.stat(path)
        return info.st_uid, info.st_gid
    except OSError:
        return None


def restore_one(dest, blob, mode, owner, dry_run):
    if dry_run:
        return
    directory = os.path.dirname(dest)
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".restore-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(blob)
        os.chmod(tmp, mode)
        os.replace(tmp, dest)
    except OSError:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    if owner and hasattr(os, "chown"):
        try:
            os.chown(dest, owner[0], owner[1])
        except PermissionError:
            pass


def main():
    parser = argparse.ArgumentParser(
        description="Restore an RBR controller backup made by rbr-backup.py.")
    parser.add_argument("archive", help="the .zip written by rbr-backup.py")
    parser.add_argument("--dir", default=os.path.dirname(os.path.abspath(__file__)),
                        help="controller directory to restore into (default: this script's)")
    parser.add_argument("--z2m-dir", default="",
                        help="Zigbee2MQTT data directory (default: autodetect)")
    parser.add_argument("--owner", default="",
                        help="owner for controller files, user:group (default: current owner of --dir)")
    parser.add_argument("--z2m-owner", default="",
                        help="owner for Zigbee2MQTT files (default: current owner of --z2m-dir)")
    parser.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    parser.add_argument("--dry-run", action="store_true",
                        help="list what would be restored, change nothing")
    parser.add_argument("--no-services", action="store_true",
                        help="do not stop or start any systemd service")
    parser.add_argument("--force", action="store_true",
                        help="restore even if map.json does not look usable")
    args = parser.parse_args()

    rbr_dir = os.path.abspath(args.dir)
    z2m_dir = z2m_data_dir(args.z2m_dir)
    archive = os.path.abspath(args.archive)
    if not os.path.isfile(archive):
        log(f"no such archive: {archive}")
        return 1

    try:
        with zipfile.ZipFile(archive) as zf:
            members = safe_members(zf)
            manifest, data = verify_archive(zf, members)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        log(f"cannot use {archive}: {exc}")
        return 1

    map_blob = data.get(("rbr", "map.json"))
    if map_blob is None:
        log("archive has no rbr/map.json — refusing to restore")
        return 1
    try:
        profiles, rooms = map_summary(map_blob)
    except ValueError as exc:
        if not args.force:
            log(f"{exc}; use --force only if you know the archive is otherwise good")
            return 1
        profiles = rooms = 0
        log(f"warning: {exc} — restoring anyway (--force)")

    entries = []
    for (root, rel), blob in data.items():
        base = rbr_dir if root == "rbr" else z2m_dir
        dest = os.path.join(base, rel)
        entries.append((dest, root, rel, blob))
    entries.sort(key=lambda entry: entry[0])

    print()
    print("Room By Room — restore")
    print("======================")
    print(f"  archive:      {archive}")
    print(f"  made:         {manifest.get('created', 'unknown')} "
          f"on {manifest.get('hostname', 'unknown')}")
    print(f"  release:      {manifest.get('rbr_version') or 'unknown'}")
    print(f"  controller:   {rbr_dir}")
    print(f"  zigbee2mqtt:  {z2m_dir}")
    print(f"  map:          {profiles} profile(s), {rooms} room(s)")
    for warning in manifest.get("warnings", []):
        print(f"  warning:      {warning}")
    print(f"  files:        {len(entries)}")

    if args.dry_run:
        for dest, _root, rel, blob in entries:
            print(f"    would restore {dest} ({len(blob)} bytes)")
        return 0

    if not args.yes:
        if not sys.stdin.isatty():
            log("no terminal to ask for confirmation; re-run with --yes")
            return 2
        answer = input("Restore these files, replacing what is there now? [y/N]: ").strip()
        if answer.lower() not in ("y", "yes"):
            log("cancelled")
            return 2

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    snapshot_existing(entries, rbr_dir, stamp, args.dry_run)

    services = not args.no_services
    if services:
        run_systemctl("stop", STOP_SERVICES)

    default_rbr_owner = destination_owner(rbr_dir)
    default_z2m_owner = destination_owner(z2m_dir) or default_rbr_owner

    explicit_rbr = args.owner or ""
    explicit_z2m = args.z2m_owner or args.owner or ""
    rbr_owner = _parse_owner(explicit_rbr) or default_rbr_owner
    z2m_owner = _parse_owner(explicit_z2m) or default_z2m_owner

    restored = 0
    for dest, root, rel, blob in entries:
        mode = PRIVATE_FILES.get(rel, None) if root == "rbr" else None
        if mode is None:
            mode = 0o644
        owner = rbr_owner if root == "rbr" else z2m_owner
        try:
            restore_one(dest, blob, mode, owner, dry_run=False)
        except OSError as exc:
            log(f"failed to write {dest}: {exc}")
            return 1
        restored += 1
    log(f"restored {restored} file(s)")

    if services:
        run_systemctl("start", START_SERVICES)

    check = os.path.join(rbr_dir, "map.json")
    try:
        with open(check, "rb") as fh:
            profiles, rooms = map_summary(fh.read())
        log(f"map.json is usable ({profiles} profile(s), {rooms} room(s))")
    except (OSError, ValueError) as exc:
        log(f"warning: restored map.json is not usable: {exc}")

    print()
    print("Restore complete. Check that Zigbee2MQTT and the controller are running:")
    print("  systemctl status zigbee2mqtt rbr-zigbee-bridge controller")
    print("Then open the app; the plan should return and the paired devices rejoin.")
    return 0


def _parse_owner(value):
    if not value:
        return None
    try:
        import pwd
        import grp
        user, _, group = value.partition(":")
        uid = pwd.getpwnam(user).pw_uid
        gid = grp.getgrnam(group).gr_gid if group else pwd.getpwnam(user).pw_gid
        return uid, gid
    except (KeyError, ImportError):
        log(f"unknown owner {value!r}; keeping the destination's current owner")
        return None


if __name__ == "__main__":
    sys.exit(main())
