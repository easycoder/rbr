#!/usr/bin/env python3
"""Import one day of the controller event journal into an RBR Studio bundle.

The journal is local to the machine running this tool (a copy, a mounted share,
or a bundle already received by mail). It collects the map snapshots that day
references and writes the transport-neutral bundle consumed by
`journal_to_scenario.py`.

Examples:
    python3 journal_import.py --source /data/rbr-heating/events \
        --day 2026-11-06 --dest fixtures/local/journal/qed6-2026-11-06

    python3 journal_import.py --source ./incoming/2026-11-06 \
        --day 2026-11-06 --dest fixtures/local/journal/qed6-2026-11-06 \
        --archive fixtures/local/journal/qed6-2026-11-06.tar.gz

The tool only reads local files; it never writes to the controller and needs no
network access.
"""

from __future__ import annotations

import argparse
import datetime as _datetime
import pathlib
import shutil
import sys
import tempfile

import journal_bundle


def _day_path(root: str, day: str) -> str:
    try:
        stamp = _datetime.date.fromisoformat(day)
    except ValueError:
        raise SystemExit(f"journal_import.py: --day must be YYYY-MM-DD, got {day!r}")
    return f"{root.rstrip('/')}/{stamp.year:04d}/{stamp.month:02d}/{stamp.isoformat()}.jsonl"


def import_day(args) -> int:
    if not args.source:
        raise SystemExit("journal_import.py: --source is required")

    day = args.day
    root = str(pathlib.Path(args.source).expanduser())
    source_label = f"local:{pathlib.Path(root).resolve()}"

    remote_day = _day_path(root, day)
    local_day_text = pathlib.Path(remote_day).read_bytes()
    if not local_day_text.strip():
        raise SystemExit(f"journal_import.py: {remote_day} is empty or missing")

    with tempfile.TemporaryDirectory(prefix="rbr-journal-import-") as tmp:
        tmp_path = pathlib.Path(tmp)
        day_path = tmp_path / f"{day}.jsonl"
        day_path.write_bytes(local_day_text)
        events = journal_bundle.read_events(day_path)
        hashes = journal_bundle.collect_map_hashes(events)
        maps = {}
        missing = []
        for digest in hashes:
            map_remote = f"{root.rstrip('/')}/maps/{digest}.json"
            try:
                data = pathlib.Path(map_remote).read_bytes()
            except OSError as exc:  # a missing map is reported, not fatal
                missing.append(digest)
                continue
            map_path = tmp_path / f"{digest}.json"
            map_path.write_bytes(data)
            maps[digest] = map_path

        heatlog_root = None
        if args.heatlog_root:
            heatlog_root = pathlib.Path(args.heatlog_root).expanduser()
        elif pathlib.Path(args.source).name == "events":
            heatlog_root = pathlib.Path(args.source).expanduser().parent
        reports = journal_bundle.heatlog_files(heatlog_root, day) if heatlog_root else {}

        dest = pathlib.Path(args.dest).expanduser()
        if args.force and dest.exists():
            resolved = dest.resolve()
            if resolved in (pathlib.Path("/"), pathlib.Path.home().resolve(), pathlib.Path.cwd().resolve()):
                raise SystemExit(f"journal_import.py: refusing to delete {resolved} with --force")
            shutil.rmtree(dest)
        manifest = journal_bundle.write_bundle(
            dest, day_path, maps, source_label,
            pathlib.Path(args.archive).expanduser() if args.archive else None,
            reports=reports, mac=args.mac)

    print(f"imported {manifest['events']} events from {source_label}")
    print(f"  day:   {manifest['day']}  system: {manifest.get('system') or '?'}  profile: {manifest.get('profile') or '?'}")
    print(f"  maps:  {len(manifest['maps'])} snapshot(s)")
    print(f"  heatlog: {len(manifest.get('reports') or [])} CSV(s)")
    print(f"  bundle: {pathlib.Path(args.dest).resolve()}")
    if args.archive:
        print(f"  archive: {pathlib.Path(args.archive).resolve()}")
    if missing:
        print(f"  warning: {len(missing)} referenced map(s) were not found; use --map with the converter if the base map is missing")
        for digest in missing[:5]:
            print(f"    {digest}")
    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="journal_import.py",
        description="Import a controller journal day into an RBR Studio bundle")
    parser.add_argument("--source", required=True,
                        help="local journal root (containing YYYY/MM/... and maps/)")
    parser.add_argument("--heatlog-root", help="local heatlog root to copy the day's CSVs from "
                                             "(default: the parent of an --source named events)")
    parser.add_argument("--mac", help="system MAC to record in the manifest (used for a per-system "
                                     "inbox and display name in RBR Studio)")
    parser.add_argument("--day", required=True, help="journal day, YYYY-MM-DD")
    parser.add_argument("--dest", required=True, help="bundle directory to write")
    parser.add_argument("--archive", help="also write a .tar.gz bundle here")
    parser.add_argument("--force", action="store_true", help="replace a non-empty destination")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        return import_day(args)
    except FileNotFoundError as exc:
        print(f"journal_import.py: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"journal_import.py: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
