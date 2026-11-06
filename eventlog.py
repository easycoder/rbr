#!/usr/bin/env python3
"""
eventlog.py - append an RBR controller event batch to the event journal.

The controller buffers events in memory and hands them to this writer as a
JSON array in a temporary batch file. This script is the single writer for
the journal: it stamps each event with the local timezone offset, stores any
embedded map snapshot content-addressed under <root>/maps/, and appends the
event as one compact JSON line to

    <root>/<YYYY>/<MM>/<YYYY-MM-DD>.jsonl

All events for a day live in one file, in event order, so the journal can be
followed with `tail -f` and measured with `du` or the report tool. A batch
that lands across midnight is split by each event's own timestamp; the date
in the path is always local time, matching the controller's schedule clock.

Retention is bounded by an absolute size and a share of the filesystem's free
space: the defaults are 1 GiB and 10%, whichever is smaller. After writing, the
writer deletes the oldest day files and the map snapshots only they reference,
but always keeps the day just written. A one-line `journal-max-bytes` (accepts
`1G`, `512M`, or a byte count) or `journal-max-free-percent` in the working
directory overrides the default; `0` disables that half.

Usage:
  python3 eventlog.py --root /data/rbr-events --batch /run/rbr/journal-*.json
  python3 eventlog.py --root /data/rbr-events --batch a.json b.json
"""

import argparse
import datetime
import fcntl
import hashlib
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile
import time

SCHEMA_VERSION = 1
DEFAULT_MAX_BYTES = 1024 * 1024 * 1024
DEFAULT_MAX_FREE_PERCENT = 10
MAP_HASH_RE = re.compile(r'"mapHash"\s*:\s*"([0-9a-f]{64})"')


def local_datetime(ts_ms):
    """The controller's wall-clock time for an epoch-millisecond stamp."""
    return datetime.datetime.fromtimestamp(int(ts_ms) / 1000.0).astimezone()


def day_path(root, ts_ms):
    """Return <root>/<YYYY>/<MM>/<YYYY-MM-DD>.jsonl for an event timestamp."""
    stamp = local_datetime(ts_ms)
    return pathlib.Path(root) / f"{stamp.year:04d}" / f"{stamp.month:02d}" / f"{stamp:%Y-%m-%d}.jsonl"


def store_map(root, payload):
    """Write a map snapshot under <root>/maps/<sha256>.json and return (hash, bytes).

    The controller sends full map snapshots only at session start and after a
    plan-changing request. Hashing them keeps the journal line small and makes
    two identical snapshots share one file.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    directory = pathlib.Path(root) / "maps"
    path = directory / f"{digest}.json"
    if not path.exists():
        directory.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=directory, prefix=".map-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
            os.replace(tmp_name, path)
        except OSError:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
    return digest, len(canonical.encode("utf-8"))


def prepare_event(event, root):
    """Return a normalised event dict, or None when the record is unusable."""
    if not isinstance(event, dict):
        return None
    if not event.get("type"):
        return None
    try:
        ts_ms = int(event.get("tsMs") or event.get("ts_ms") or round(time.time() * 1000))
    except (TypeError, ValueError):
        ts_ms = round(time.time() * 1000)
    event["tsMs"] = ts_ms
    stamp = local_datetime(ts_ms)
    event.setdefault("ts", stamp.isoformat(timespec="milliseconds"))
    event.setdefault("tzOffsetMinutes", int(stamp.utcoffset().total_seconds() // 60))
    event.setdefault("v", SCHEMA_VERSION)

    data = event.get("data")
    if isinstance(data, dict) and isinstance(data.get("map"), (dict, list)):
        digest, size = store_map(root, data["map"])
        data["mapHash"] = digest
        data["mapBytes"] = size
        del data["map"]
    return event


def read_batch(path):
    """Read a batch file: a JSON array, a JSON object, or one JSON object per line."""
    text = pathlib.Path(path).read_text(encoding="utf-8")
    if not text.strip():
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            return [parsed]
    except json.JSONDecodeError:
        pass
    events = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            events.append({"type": "batch.invalid", "data": {"line": line[:500]}})
    return events


def append_events(root, events, written_paths=None):
    """Append prepared events, grouped by their local day file. Returns (written, skipped)."""
    root = pathlib.Path(root)
    grouped = {}
    written = 0
    skipped = 0
    for raw in events:
        event = prepare_event(raw, root)
        if event is None:
            skipped += 1
            continue
        grouped.setdefault(day_path(root, event["tsMs"]), []).append(event)
        written += 1

    for path, day_events in sorted(grouped.items()):
        if written_paths is not None:
            written_paths.add(path.resolve())
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = "".join(
            json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
            for event in day_events
        )
        # One O_APPEND write per day file. Separate controller processes (and
        # a manual replay) can therefore add batches without interleaving lines.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            # One writer at a time, so a second controller instance (or a
            # manual replay) cannot interleave a partial line into this batch.
            fcntl.flock(fd, fcntl.LOCK_EX)
            data = payload.encode("utf-8")
            while data:
                sent = os.write(fd, data)
                data = data[sent:]
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)
    return written, skipped


def _read_limit_file(name, default):
    """Read an integer limit from a one-line file in the working directory."""
    path = pathlib.Path(name)
    if not path.is_file():
        return default
    text = path.read_text(encoding="utf-8").strip()
    return parse_size(text, default)


def parse_size(text, default=0):
    """Parse '1073741824', '1024M', '1G' or '0'; return default on junk."""
    text = (text or "").strip().lower()
    if not text:
        return default
    match = re.fullmatch(r"([0-9]+)\s*([kmgt]?)(?:i?b)?", text)
    if not match:
        return default
    value = int(match.group(1))
    unit = match.group(2)
    factor = {"": 1, "k": 1024, "m": 1024 ** 2, "g": 1024 ** 3, "t": 1024 ** 4}[unit]
    return value * factor


def effective_cap(root, max_bytes, max_free_percent, free_bytes=None):
    """The smaller of the absolute cap and a share of the filesystem's free space.

    A zero or negative limit disables that half. Returning None means "no cap".
    """
    caps = []
    if max_bytes is not None and max_bytes > 0:
        caps.append(int(max_bytes))
    if max_free_percent is not None and max_free_percent > 0:
        if free_bytes is None:
            try:
                free_bytes = shutil.disk_usage(pathlib.Path(root)).free
            except OSError:
                free_bytes = None
        if free_bytes is not None:
            caps.append(int(free_bytes * max_free_percent / 100))
    return min(caps) if caps else None


def _event_files(root):
    return sorted((path for path in pathlib.Path(root).rglob("*.jsonl") if path.is_file()),
                  key=lambda path: str(path))


def _map_files(root):
    directory = pathlib.Path(root) / "maps"
    return sorted((path for path in directory.glob("*.json") if path.is_file()),
                  key=lambda path: str(path))


def _total_bytes(paths):
    total = 0
    for path in paths:
        try:
            total += path.stat().st_size
        except OSError:
            pass
    return total


def prune(root, max_bytes=DEFAULT_MAX_BYTES, max_free_percent=DEFAULT_MAX_FREE_PERCENT,
          keep=(), free_bytes=None):
    """Delete the oldest day files (and orphaned maps) until the journal fits.

    `keep` names day files written by this run; the newest day is always kept as
    well. The result is a dictionary suitable for logging and tests.
    """
    root = pathlib.Path(root)
    events = _event_files(root)
    maps = _map_files(root)
    total = _total_bytes(events) + _total_bytes(maps)
    cap = effective_cap(root, max_bytes, max_free_percent, free_bytes)
    result = {"cap": cap, "totalBefore": total, "totalAfter": total,
              "deletedDays": [], "deletedMaps": [], "over": False}
    if cap is None or total <= cap:
        return result

    protected = {path.resolve() for path in keep}
    if events:
        protected.add(events[-1].resolve())
    deleted = []
    for path in events:
        if total <= cap:
            break
        if path.resolve() in protected:
            continue
        try:
            size = path.stat().st_size
            path.unlink()
        except OSError:
            continue
        total -= size
        deleted.append(path)
    result["deletedDays"] = [str(path) for path in deleted]

    if deleted or total > cap:
        remaining = [path for path in _event_files(root) if path.is_file()]
        referenced = set()
        for path in remaining:
            try:
                referenced.update(MAP_HASH_RE.findall(path.read_text(encoding="utf-8", errors="replace")))
            except OSError:
                continue
        for path in _map_files(root):
            if path.stem in referenced:
                continue
            try:
                path.unlink()
                result["deletedMaps"].append(str(path))
            except OSError:
                pass
        total = _total_bytes(remaining) + _total_bytes(_map_files(root))
        for path in deleted:
            try:
                parent = path.parent
                while parent != root and parent.is_dir() and not any(parent.iterdir()):
                    parent.rmdir()
                    parent = parent.parent
            except OSError:
                pass

    result["totalAfter"] = total
    result["over"] = total > cap
    return result


def remove_batch(path):
    """Delete a consumed batch, tolerating a concurrent sweep."""
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="eventlog.py",
        description="Append RBR controller event batches to <root>/<YYYY>/<MM>/<YYYY-MM-DD>.jsonl",
    )
    parser.add_argument("--root", required=True, help="journal root directory")
    parser.add_argument("--batch", action="append", default=[], help="batch file (repeatable)")
    parser.add_argument("--keep-batch", action="store_true", help="do not delete consumed batch files")
    parser.add_argument("--quiet", action="store_true", help="suppress the per-batch summary")
    parser.add_argument("--max-bytes", type=parse_size, default=None,
                        help="absolute journal cap (default: journal-max-bytes file, then 1G; 0 disables)")
    parser.add_argument("--max-free-percent", type=int, default=None,
                        help="cap as a percentage of filesystem free space (default: journal-max-free-percent file, then 10; 0 disables)")
    parser.add_argument("--no-prune", action="store_true", help="skip retention pruning")
    args = parser.parse_args(argv)

    root = pathlib.Path(args.root).expanduser()
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"eventlog.py: cannot create journal root {root}: {exc}", file=sys.stderr)
        return 2

    max_bytes = args.max_bytes
    if max_bytes is None:
        max_bytes = _read_limit_file("journal-max-bytes", DEFAULT_MAX_BYTES)
    max_free_percent = args.max_free_percent
    if max_free_percent is None:
        max_free_percent = _read_limit_file("journal-max-free-percent", DEFAULT_MAX_FREE_PERCENT)

    if not args.no_prune:
        prune(root, max_bytes, max_free_percent)

    total_written = 0
    total_skipped = 0
    failed = False
    written_paths = set()
    for name in args.batch:
        path = pathlib.Path(name)
        try:
            events = read_batch(path)
        except OSError as exc:
            print(f"eventlog.py: cannot read batch {path}: {exc}", file=sys.stderr)
            failed = True
            continue
        written, skipped = append_events(root, events, written_paths)
        total_written += written
        total_skipped += skipped
        if not args.keep_batch:
            remove_batch(path)
        if not args.quiet:
            print(f"eventlog.py: {path}: {written} event(s), {skipped} skipped", file=sys.stderr)

    if not args.no_prune:
        retention = prune(root, max_bytes, max_free_percent, keep=written_paths)
        if retention["deletedDays"] or retention["deletedMaps"]:
            if not args.quiet:
                print(f"eventlog.py: pruned {len(retention['deletedDays'])} day(s) and "
                      f"{len(retention['deletedMaps'])} map(s); {retention['totalAfter']} bytes remain",
                      file=sys.stderr)
        elif retention["over"]:
            print(f"eventlog.py: journal is over its {retention['cap']}-byte limit; "
                  "only the current day remains", file=sys.stderr)

    if not args.quiet:
        print(f"eventlog.py: journal {root}: {total_written} event(s) total", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
