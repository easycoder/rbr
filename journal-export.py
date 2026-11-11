#!/usr/bin/env python3
"""journal-export.py - make a compact scenario bundle from one journal day.

Runs on the controller. Reads <journal-root>/<YYYY>/<MM>/<YYYY-MM-DD>.jsonl,
copies the map snapshots it references and the last snapshot before the day
(the map in force at midnight), drops repeated sensor readings that did not
change value, and writes a tar.gz bundle in the same format as the
RBR Studio importer:

    <journal-root>/exports/<system>-<YYYY-MM-DD>.tar.gz
    manifest.json
    events/<YYYY>/<MM>/<YYYY-MM-DD>.jsonl
    maps/<sha256>.json
    reports/heatlog/<room>/<YYYY>/<MM>/<DD>.csv

The bundle also carries the day's heating CSVs when heat logging is enabled,
so the same archive serves RBR Studio and the statistics role without a
second transfer. The raw journal stays local until retention removes it. Email
is opt-in through `journal-export-config.json` (see `load_config`), and
`--email-now` sends one bundle regardless of that toggle. `--now` exports
today's file as it stands, as a partial bundle under `exports/requests/`, for
the PWA's **Send journal now** action. Run it as a systemd timer (see
rbr-journal-export.timer) or by hand:

    python3 journal-export.py --day 2026-11-06
    python3 journal-export.py --day 2026-11-06 --mode full --out /tmp/exports
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import shutil
import socket
import sys
import tarfile
import tempfile

# The mail merge rule is shared with rbr-backup.py so the two senders cannot
# disagree about which credentials value wins.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rbr_mail  # noqa: E402 - beside this script, not on the caller's path

BUNDLE_FORMAT = "rbr-journal-bundle"
BUNDLE_VERSION = 1
DEFAULT_KEEP = 14
CONFIG_NAME = "journal-export-config.json"
DEFAULT_MAX_EMAIL_MB = 25
TRUE_VALUES = {"1", "on", "true", "yes", "enabled"}


def resolve_root(cli_root):
    if cli_root:
        return pathlib.Path(cli_root).expanduser()
    for name in ("journal-root",):
        path = pathlib.Path(name)
        if path.is_file():
            value = path.read_text(encoding="utf-8").strip()
            if value:
                return pathlib.Path(value).expanduser()
    heatlog = pathlib.Path("heatlog-root")
    if heatlog.is_file():
        value = heatlog.read_text(encoding="utf-8").strip()
        if value:
            return pathlib.Path(value).expanduser() / "events"
    raise SystemExit("journal-export.py: no --root, journal-root or heatlog-root")


def day_path(root, day):
    return root / f"{day.year:04d}" / f"{day.month:02d}" / f"{day.isoformat()}.jsonl"


def last_map_before(root, day):
    """The newest map hash in a journal day before `day`, or "".

    A day whose journal has no `mapHash` event — the controller booted earlier
    and the map did not change — still needs a base map for the Studio. The
    last snapshot before the day is the map in force at midnight, so copying
    it makes the bundle stand alone. Days are visited newest first and the
    search stops at the first one that has a snapshot.
    """
    root = pathlib.Path(root)
    candidates = sorted(root.glob("[0-9][0-9][0-9][0-9]/[0-9][0-9]/*.jsonl"), reverse=True)
    for path in candidates:
        try:
            file_day = datetime.date.fromisoformat(path.stem)
        except ValueError:
            continue
        if file_day >= day:
            continue
        latest = None
        try:
            with path.open(encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    digest = (event.get("data") or {}).get("mapHash")
                    if not digest:
                        continue
                    key = (event.get("tsMs") or 0, event.get("seq") or 0)
                    if latest is None or key > latest[0]:
                        latest = (key, digest)
        except OSError:
            continue
        if latest:
            return latest[1]
    return ""


def _last_sensor(changed, event):
    data = event.get("data") or {}
    key = data.get("sensor") or data.get("room")
    previous = changed.get(key)
    current = (data.get("temp"), data.get("humidity"), data.get("battery"))
    if previous is None or previous != current:
        changed[key] = current
        return True
    return False


def filter_lines(lines, mode):
    """Yield the raw JSONL lines to keep, preserving the controller's own text."""
    changed = {}
    for line in lines:
        text = line.strip()
        if not text:
            continue
        try:
            event = json.loads(text)
        except json.JSONDecodeError:
            continue
        kind = event.get("type")
        if mode == "scenario" and kind == "sensor.reading":
            if not _last_sensor(changed, event):
                continue
        elif mode == "summary" and kind == "sensor.reading":
            continue
        yield text


def _sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _slug(text):
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", str(text or "")).strip("-")
    return value or "rbr"


def resolve_heatlog_root(cli_root, journal_root):
    """Find the heating-CSV root: --heatlog-root, heatlog-root, then <root>/events."""
    if cli_root:
        return pathlib.Path(cli_root).expanduser()
    marker = pathlib.Path("heatlog-root")
    if marker.is_file():
        value = marker.read_text(encoding="utf-8").strip()
        if value:
            return pathlib.Path(value).expanduser()
    root = pathlib.Path(journal_root)
    if root.name == "events":
        candidate = root.parent
        if candidate.is_dir():
            return candidate
    return None


def heatlog_files(root, day):
    """Bundle-relative paths mapped to the day's heatlog CSVs, or {} if there are none."""
    if root is None:
        return {}
    root = pathlib.Path(root)
    if not root.is_dir():
        return {}
    relative_day = f"{day.year:04d}/{day.month:02d}/{day.day:02d}.csv"
    reports = {}
    for room in sorted(root.iterdir()):
        if not room.is_dir():
            continue
        source = room / relative_day
        if source.is_file():
            reports[f"reports/heatlog/{room.name}/{relative_day}"] = source
    return reports


def export_day(root, day, out, mode="scenario", keep=DEFAULT_KEEP, force=False,
               heatlog_root=None, mac=None, partial=False, label=None,
               requested_at=None):
    source = day_path(root, day)
    if not source.is_file():
        raise SystemExit(f"journal-export.py: no journal day at {source}")
    original = source.read_text(encoding="utf-8", errors="replace").splitlines()
    kept = list(filter_lines(original, mode))
    if not kept:
        raise SystemExit(f"journal-export.py: no events to export in {source}")
    events = [json.loads(line) for line in kept]
    session = next((event for event in events if event.get("type") == "session.start"), {})
    session_data = session.get("data") or {}
    system = session_data.get("system") or "rbr"
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    suffix = f"-{label.replace(':', '')}" if partial and label else ""
    archive = out / f"{_slug(system)}-{day.isoformat()}{suffix}.tar.gz"
    if archive.exists() and not force:
        raise SystemExit(f"journal-export.py: {archive} exists (use --force)")

    with tempfile.TemporaryDirectory(prefix="rbr-journal-export-") as tmp:
        bundle = pathlib.Path(tmp)
        events_dir = bundle / "events" / f"{day.year:04d}" / f"{day.month:02d}"
        events_dir.mkdir(parents=True)
        day_file = events_dir / source.name
        day_file.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
        maps_dir = bundle / "maps"
        maps_dir.mkdir()
        hashes = []
        for event in events:
            value = (event.get("data") or {}).get("mapHash")
            if value and value not in hashes:
                hashes.append(value)
        # The map in force at the start of the day is the base the Studio
        # begins from. A day whose first snapshot comes later (a schedule edit
        # at 15:59, say) must not use that later map as its base, or the UI
        # shows the edited schedule for the whole morning.
        base_map = last_map_before(root, day)
        if base_map and base_map not in hashes:
            hashes.insert(0, base_map)
        map_rows = []
        for digest in hashes:
            source_map = root / "maps" / f"{digest}.json"
            if not source_map.is_file():
                continue
            shutil.copyfile(source_map, maps_dir / source_map.name)
            map_rows.append({"hash": digest, "bytes": source_map.stat().st_size,
                             "sha256": _sha(source_map)})
        report_rows = []
        report_sources = heatlog_files(heatlog_root, day)
        for relative, source_report in sorted(report_sources.items()):
            parts = pathlib.PurePosixPath(relative).parts
            target = bundle.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_report, target)
            row = {"kind": "heatlog", "path": relative,
                   "bytes": source_report.stat().st_size, "sha256": _sha(source_report)}
            if len(parts) >= 3:
                row["room"] = parts[2]
            report_rows.append(row)
        first = events[0] if events else {}
        last = events[-1] if events else {}
        manifest = {
            "format": BUNDLE_FORMAT,
            "version": BUNDLE_VERSION,
            "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "source": f"controller-export:{root}",
            "day": day.isoformat(),
            "mac": mac,
            "partial": bool(partial),
            "label": label,
            "requestedAt": requested_at,
            "events": len(events),
            "eventsBytes": day_file.stat().st_size,
            "eventsSha256": _sha(day_file),
            "firstSeq": first.get("seq"),
            "lastSeq": last.get("seq"),
            "firstTs": first.get("ts"),
            "lastTs": last.get("ts"),
            "system": session_data.get("system"),
            "profile": session_data.get("profile"),
            "profileIndex": session_data.get("profileIndex"),
            "baseMapHash": base_map or session_data.get("mapHash"),
            "tzOffsetMinutes": first.get("tzOffsetMinutes"),
            "maps": map_rows,
            "reports": report_rows,
            "eventsPath": day_file.relative_to(bundle).as_posix(),
            "mode": mode,
        }
        (bundle / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        with tarfile.open(archive, "w:gz") as tar:
            for name in ("manifest.json", "events", "maps"):
                tar.add(bundle / name, arcname=name)
            if (bundle / "reports").is_dir():
                tar.add(bundle / "reports", arcname="reports")

    _prune_exports(out, keep)
    return archive, manifest


def _prune_exports(out, keep):
    if keep <= 0:
        return
    archives = sorted((path for path in out.glob("*.tar.gz") if path.is_file()),
                      key=lambda path: path.stat().st_mtime, reverse=True)
    for path in archives[keep:]:
        try:
            path.unlink()
        except OSError:
            pass


def load_config(path):
    """Read the opt-in config, or {} when it is absent or unusable."""
    path = pathlib.Path(path)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        # Always visible: a config that exists but cannot be read would
        # otherwise look exactly like an opted-out installation.
        print(f"journal-export: cannot read {path}: {exc}", file=sys.stderr, flush=True)
        return {}
    return data if isinstance(data, dict) else {}


def config_enabled(config):
    value = config.get("enabled")
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in TRUE_VALUES


def _log(quiet):
    if quiet:
        return lambda message: None
    return lambda message: print(f"journal-export: {message}", flush=True)


def send_bundle(archive, manifest, config, rbr_dir, to="", smtp_port=0,
                max_email_mb=DEFAULT_MAX_EMAIL_MB, quiet=False):
    """Email one exported bundle. Returns (sent, error_message)."""
    log = _log(quiet)
    size = pathlib.Path(archive).stat().st_size
    if max_email_mb > 0 and size > max_email_mb * 1024 * 1024:
        return False, (f"{pathlib.Path(archive).name} is {size} bytes, over the "
                       f"{max_email_mb} MB mail limit — kept locally only")
    local = rbr_mail.load_local_credentials(rbr_dir, log)
    cloud = rbr_mail.fetch_cloud(rbr_dir, log)
    settings = rbr_mail.mail_settings(local, cloud)
    if smtp_port:
        settings["mail_port"] = smtp_port
    recipient = rbr_mail.resolve_recipient(
        to or config.get("address", ""), cloud, local)
    day = manifest.get("day") or "unknown day"
    system = manifest.get("system") or socket.gethostname()
    mac = str(manifest.get("mac") or "").strip()
    label = mac or system
    partial = bool(manifest.get("partial"))
    stamp = str(manifest.get("label") or "").strip()
    suffix = f" {stamp}" if partial and stamp else ""
    subject = f"RBR journal {label} {day}{suffix}"
    body = (
        f"Attached is the Room By Room journal bundle for {day} ({system}, {mac or 'MAC unknown'})"
        f"{', up to ' + stamp if partial and stamp else ''}.\n\n"
        f"{manifest.get('events', 0)} events, {len(manifest.get('maps') or [])} "
        f"map snapshot(s), {len(manifest.get('reports') or [])} heatlog CSV(s), "
        f"mode {manifest.get('mode') or 'scenario'}.\n\n"
        "It contains room and device identifiers, schedules, sensor readings "
        "and the UI requests the controller received. Keep it private.\n\n"
        "RBR Studio scans ~/RBR-journal at startup, so a mail filter can "
        "save this attachment there and the day will appear in its Journal "
        "group. The bundle can also be imported by hand with journal_ingest.py.\n")
    sent, error = rbr_mail.send_files(
        settings, recipient, subject, body, [archive], log=log)
    if not sent:
        print(f"journal-export: {error}", file=sys.stderr, flush=True)
    return sent, error


def main(argv=None):
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    parser = argparse.ArgumentParser(prog="journal-export.py",
                                     description="Export one journal day as an RBR Studio bundle")
    parser.add_argument("--root", help="journal root (default: journal-root, then <heatlog-root>/events)")
    parser.add_argument("--heatlog-root", help="heating-CSV root (default: heatlog-root, then <root>/.. for an events root)")
    parser.add_argument("--day", help="day to export (YYYY-MM-DD; default: yesterday)")
    parser.add_argument("--now", action="store_true",
                        help="export today's journal up to this moment, as a partial bundle")
    parser.add_argument("--out", help="export directory (default: <root>/exports, or <root>/exports/requests with --now)")
    parser.add_argument("--mode", choices=("scenario", "summary", "full"), default="scenario",
                        help="scenario drops unchanged sensor repeats; summary drops sensors; full keeps all")
    parser.add_argument("--keep", type=int, default=DEFAULT_KEEP,
                        help="keep this many archives, newest first (0 disables; default: 14)")
    parser.add_argument("--force", action="store_true", help="overwrite an existing archive")
    parser.add_argument("--dir", help="controller directory holding credentials and the email config "
                                     "(default: the current directory)")
    parser.add_argument("--config", help=f"email config (default: <dir>/{CONFIG_NAME})")
    email = parser.add_mutually_exclusive_group()
    email.add_argument("--email-now", action="store_true",
                       help="email this bundle even when the config has email switched off")
    email.add_argument("--no-email", action="store_true", help="never email this run")
    parser.add_argument("--to", help="recipient, overriding the config, the cloud and `mail_to`")
    parser.add_argument("--smtp-port", type=int, default=0,
                        help="SMTP port, overriding mail_port (default: mail_port or 465)")
    parser.add_argument("--max-email-mb", type=int, default=DEFAULT_MAX_EMAIL_MB,
                        help=f"do not email bundles larger than this (0 disables; default: {DEFAULT_MAX_EMAIL_MB})")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    if args.now and args.day:
        parser.error("--now and --day cannot be used together")
    root = resolve_root(args.root)
    heatlog_root = resolve_heatlog_root(args.heatlog_root, root)
    rbr_dir = pathlib.Path(args.dir).expanduser() if args.dir else pathlib.Path.cwd()
    mac = rbr_mail.local_mac(rbr_dir)
    partial = bool(args.now)
    label = None
    requested_at = None
    if args.now:
        now = datetime.datetime.now().astimezone()
        day = now.date()
        label = now.strftime("%H:%M:%S")
        requested_at = now.isoformat(timespec="seconds")
    else:
        day = datetime.date.fromisoformat(args.day) if args.day else yesterday
    if args.out:
        out = pathlib.Path(args.out).expanduser()
    elif partial:
        out = root / "exports" / "requests"
    else:
        out = root / "exports"
    archive, manifest = export_day(
        root, day, out, args.mode, args.keep, args.force,
        heatlog_root=heatlog_root, mac=mac, partial=partial, label=label,
        requested_at=requested_at)
    if not args.quiet:
        print(f"journal-export.py: {archive}")
        print(f"  {manifest['events']} events, {len(manifest['maps'])} map(s), "
              f"{len(manifest['reports'])} heatlog CSV(s), mode {manifest['mode']}"
              + (f", partial to {label}" if partial else ""))

    config_path = (pathlib.Path(args.config).expanduser() if args.config
                   else rbr_dir / CONFIG_NAME)
    config = load_config(config_path)
    if args.no_email:
        wanted = False
    elif args.email_now:
        wanted = True
    else:
        wanted = config_enabled(config)
    if wanted:
        send_bundle(archive, manifest, config, rbr_dir, args.to, args.smtp_port,
                    args.max_email_mb, args.quiet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
