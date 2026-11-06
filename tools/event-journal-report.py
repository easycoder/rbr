#!/usr/bin/env python3
"""
event-journal-report.py - measure the RBR event journal.

Reads <root>/<YYYY>/<MM>/<YYYY-MM-DD>.jsonl and prints bytes, events and
breakdowns by day and event type, plus a linear 30-day projection. Map
snapshots under <root>/maps/ are counted separately.

Usage:
  python3 tools/event-journal-report.py /data/rbr-events
  watch -n 10 python3 tools/event-journal-report.py /data/rbr-events
  python3 tools/event-journal-report.py /data/rbr-events --json
"""

import argparse
import datetime
import json
import pathlib
import sys
from collections import Counter, defaultdict


def journal_days(root):
    """Yield (date, path) for every daily JSONL file under root."""
    for path in sorted(pathlib.Path(root).glob("*/*/*.jsonl")):
        try:
            day = datetime.date.fromisoformat(path.stem)
        except ValueError:
            continue
        yield day, path


def measure(root, days=None):
    root = pathlib.Path(root)
    today = datetime.date.today()
    by_day = {}
    by_type = Counter()
    bytes_by_type = defaultdict(int)
    rooms = Counter()
    total_bytes = 0
    total_lines = 0
    bad_lines = 0

    for day, path in journal_days(root):
        if days is not None and (today - day).days >= days:
            continue
        size = path.stat().st_size
        lines = 0
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                lines += 1
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    bad_lines += 1
                    continue
                kind = event.get("type", "unknown")
                by_type[kind] += 1
                bytes_by_type[kind] += len(line.encode("utf-8"))
                room = (event.get("data") or {}).get("room")
                if room:
                    rooms[room] += 1
        by_day[str(day)] = {"path": str(path), "bytes": size, "events": lines}
        total_bytes += size
        total_lines += lines

    maps_dir = root / "maps"
    map_files = list(maps_dir.glob("*.json")) if maps_dir.is_dir() else []
    map_bytes = sum(p.stat().st_size for p in map_files)
    average = total_bytes / total_lines if total_lines else 0
    return {
        "root": str(root),
        "days": by_day,
        "totalBytes": total_bytes,
        "totalEvents": total_lines,
        "badLines": bad_lines,
        "averageBytesPerEvent": round(average, 1),
        "projected30DayBytes": round(average * total_lines / max(len(by_day), 1) * 30) if by_day else 0,
        "byType": dict(by_type.most_common()),
        "bytesByType": dict(sorted(bytes_by_type.items(), key=lambda item: item[1], reverse=True)),
        "topRooms": dict(rooms.most_common(12)),
        "maps": {"files": len(map_files), "bytes": map_bytes},
    }


def human(size):
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GiB"


def print_report(report):
    print(f"journal: {report['root']}")
    print(f"days: {len(report['days'])}  events: {report['totalEvents']}  bytes: {human(report['totalBytes'])}"
          f"  avg/event: {report['averageBytesPerEvent']} B")
    print(f"maps: {report['maps']['files']} file(s), {human(report['maps']['bytes'])}")
    if report["badLines"]:
        print(f"WARNING: {report['badLines']} unparseable line(s)")
    print(f"projected 30 days at this rate: {human(report['projected30DayBytes'])}")
    print()
    print("by day:")
    for day, row in report["days"].items():
        print(f"  {day}  {row['events']:>7} events  {human(row['bytes']):>10}")
    print()
    print("by event type:")
    for kind, count in report["byType"].items():
        print(f"  {kind:<24} {count:>8}  {human(report['bytesByType'].get(kind, 0)):>10}")
    if report["topRooms"]:
        print()
        print("busiest rooms:")
        for room, count in report["topRooms"].items():
            print(f"  {room:<24} {count:>8} events")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="event-journal-report.py",
                                     description="Measure the RBR event journal")
    parser.add_argument("root", help="journal root directory")
    parser.add_argument("--days", type=int, default=None,
                        help="only include days younger than N days")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)
    if not pathlib.Path(args.root).exists():
        print(f"event-journal-report.py: no such directory: {args.root}", file=sys.stderr)
        return 2
    report = measure(args.root, args.days)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
