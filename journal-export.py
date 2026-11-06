#!/usr/bin/env python3
"""journal-export.py - make a compact scenario bundle from one journal day.

Runs on the controller. Reads <journal-root>/<YYYY>/<MM>/<YYYY-MM-DD>.jsonl,
copies the map snapshots it references, drops repeated sensor readings that did
not change value, and writes a tar.gz bundle in the same format as the
Scenario Studio importer:

    <journal-root>/exports/<system>-<YYYY-MM-DD>.tar.gz
    manifest.json
    events/<YYYY>/<MM>/<YYYY-MM-DD>.jsonl
    maps/<sha256>.json

The archive is what an SSH pull, email or a future cloud upload should carry;
the raw journal stays local until retention removes it. Run it as a systemd
timer (see rbr-journal-export.timer) or by hand:

    python3 journal-export.py --day 2026-11-06
    python3 journal-export.py --day 2026-11-06 --mode full --out /tmp/exports
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import re
import shutil
import sys
import tarfile
import tempfile

BUNDLE_FORMAT = "rbr-journal-bundle"
BUNDLE_VERSION = 1
DEFAULT_KEEP = 14


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


def export_day(root, day, out, mode="scenario", keep=DEFAULT_KEEP, force=False):
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
    archive = out / f"{_slug(system)}-{day.isoformat()}.tar.gz"
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
        map_rows = []
        for digest in hashes:
            source_map = root / "maps" / f"{digest}.json"
            if not source_map.is_file():
                continue
            shutil.copyfile(source_map, maps_dir / source_map.name)
            map_rows.append({"hash": digest, "bytes": source_map.stat().st_size,
                             "sha256": _sha(source_map)})
        first = events[0] if events else {}
        last = events[-1] if events else {}
        manifest = {
            "format": BUNDLE_FORMAT,
            "version": BUNDLE_VERSION,
            "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "source": f"controller-export:{root}",
            "day": day.isoformat(),
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
            "baseMapHash": session_data.get("mapHash"),
            "tzOffsetMinutes": first.get("tzOffsetMinutes"),
            "maps": map_rows,
            "eventsPath": day_file.relative_to(bundle).as_posix(),
            "mode": mode,
        }
        (bundle / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        with tarfile.open(archive, "w:gz") as tar:
            for name in ("manifest.json", "events", "maps"):
                tar.add(bundle / name, arcname=name)

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


def main(argv=None):
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    parser = argparse.ArgumentParser(prog="journal-export.py",
                                     description="Export one journal day as a Scenario Studio bundle")
    parser.add_argument("--root", help="journal root (default: journal-root, then <heatlog-root>/events)")
    parser.add_argument("--day", help="day to export (YYYY-MM-DD; default: yesterday)")
    parser.add_argument("--out", help="export directory (default: <root>/exports)")
    parser.add_argument("--mode", choices=("scenario", "summary", "full"), default="scenario",
                        help="scenario drops unchanged sensor repeats; summary drops sensors; full keeps all")
    parser.add_argument("--keep", type=int, default=DEFAULT_KEEP,
                        help="keep this many archives, newest first (0 disables; default: 14)")
    parser.add_argument("--force", action="store_true", help="overwrite an existing archive")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    root = resolve_root(args.root)
    day = datetime.date.fromisoformat(args.day) if args.day else yesterday
    out = pathlib.Path(args.out).expanduser() if args.out else root / "exports"
    archive, manifest = export_day(root, day, out, args.mode, args.keep, args.force)
    if not args.quiet:
        print(f"journal-export.py: {archive}")
        print(f"  {manifest['events']} events, {len(manifest['maps'])} map(s), mode {manifest['mode']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
