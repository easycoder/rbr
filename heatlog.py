#!/usr/bin/env python3
"""
heatlog.py - append one heating-data row to the RBR CSV hierarchy.

The controller logs heating data as lines in text files organised as

    <root>/<room>/<YYYY>/<MM>/<DD>.csv

Each line holds four comma-separated values:

    epochMinutes,targetTenths,actualTenths,mode

  epochMinutes  - minutes since the Unix epoch (the controller's clock,
                  divided by 60000). The date in the file path is derived
                  from this timestamp, in local time, so a 23:59 event lands
                  in the right day file.
  targetTenths  - target temperature in tenths of a degree (e.g. 207 = 20.7 C)
  actualTenths  - actual temperature in tenths of a degree
  mode          - one letter: o=off, c=on (constant target), p=timed
                  (periods/schedule), b=boost

The relay-state inference documented for analysis is: the relay is on iff
mode is one of c/p/b AND target > actual. Rows are appended on change only
(controller-side concern); this script just appends one row safely. A row
identical to the file's last line is skipped (best effort), so a controller
restart re-logging its baseline cannot duplicate the previous row.

Root resolution (in order):
  1. --root PATH
  2. a file named "heatlog-root" in the current directory (one line, the
     absolute path - normally a partition mount, or a symlink to a local
     directory on test machines)
  3. ~/heating-data

The write is a single O_APPEND write of one line, safe under concurrent
appends from multiple controller events.

Usage:
  python3 heatlog.py --room Kitchen --ts 30504123 --target 207 --actual 205 --mode p
"""

import argparse
import datetime
import os
import pathlib
import sys

MODE_LETTERS = ("o", "c", "p", "b")
MODE_DEFAULT = "o"


def resolve_root(cli_root):
    """Return the data root directory as a Path, per the resolution order above."""
    if cli_root:
        return pathlib.Path(cli_root).expanduser()
    config = pathlib.Path("heatlog-root")
    if config.is_file():
        text = config.read_text(encoding="utf-8").strip()
        if text:
            return pathlib.Path(text).expanduser()
    return pathlib.Path.home() / "heating-data"


def sanitise_room(name):
    """Make a room name safe as a single path component (no separators)."""
    cleaned = []
    for ch in str(name):
        if ch in ("/", "\\", "\x00"):
            cleaned.append("-")
        elif ord(ch) < 32:
            continue
        else:
            cleaned.append(ch)
    folder = "".join(cleaned).strip()
    if folder in ("", ".", ".."):
        return "unnamed"
    return folder


def day_csv_path(root, room, epoch_minutes):
    """Derive <root>/<room>/<YYYY>/<MM>/<DD>.csv from the row's own timestamp (local time)."""
    dt = datetime.datetime.fromtimestamp(int(epoch_minutes) * 60)
    return (
        pathlib.Path(root)
        / sanitise_room(room)
        / f"{dt.year:04d}"
        / f"{dt.month:02d}"
        / f"{dt.day:02d}.csv"
    )


def _last_row(path):
    """Return the last data line already in `path` (best effort), or None."""
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            if size == 0:
                return None
            # A row is ~30 bytes; a bounded tail read avoids loading a whole
            # day file just to compare one line.
            fh.seek(max(0, size - 4096))
            data = fh.read()
    except OSError:
        return None
    lines = data.splitlines()
    return lines[-1].decode("ascii", "replace") if lines else None


def append_row(root, room, epoch_minutes, target_tenths, actual_tenths, mode):
    """Append one CSV row, creating the directory tree as needed. Returns the file path.

    A row identical to the file's last line is skipped (best effort — a
    concurrent writer can still slip one past). That makes the log immune to
    the common sources of exact-duplicate rows: a controller restart
    re-logging the current state as its baseline before the once-a-minute
    state flush, and two controller instances briefly overlapping.
    """
    path = day_csv_path(root, room, epoch_minutes)
    row = f"{int(epoch_minutes)},{int(target_tenths)},{int(actual_tenths)},{mode}"
    if _last_row(path) == row:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    line = (row + "\n").encode("ascii")
    # Binary unbuffered append: one O_APPEND write per row, so concurrent
    # appends from separate controller events cannot interleave.
    with open(path, "ab") as fh:
        fh.write(line)
    return path


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="heatlog.py",
        description="Append one heating-data row to <root>/<room>/<YYYY>/<MM>/<DD>.csv",
    )
    parser.add_argument("--root", help="data root (default: heatlog-root file, then ~/heating-data)")
    parser.add_argument("--room", required=True, help="room name (used as the top folder)")
    parser.add_argument("--ts", required=True, help="epoch time in minutes since the Unix epoch")
    parser.add_argument("--target", required=True, help="target temperature in tenths of a degree")
    parser.add_argument("--actual", required=True, help="actual temperature in tenths of a degree")
    parser.add_argument(
        "--mode",
        default=MODE_DEFAULT,
        help="one letter: o=off, c=on, p=timed(periods), b=boost (default o)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        epoch_minutes = int(args.ts)
        target_tenths = int(args.target)
        actual_tenths = int(args.actual)
    except ValueError:
        print(f"heatlog.py: numeric arguments required (ts={args.ts!r}, target={args.target!r}, actual={args.actual!r})", file=sys.stderr)
        return 2
    if epoch_minutes <= 0 or target_tenths < -1000 or actual_tenths < -1000 or actual_tenths > 5000 or target_tenths > 5000:
        print(f"heatlog.py: implausible values (ts={epoch_minutes}, target={target_tenths}, actual={actual_tenths})", file=sys.stderr)
        return 2
    mode = args.mode.lower()
    if mode not in MODE_LETTERS:
        print(f"heatlog.py: unknown mode {args.mode!r} (expected one of {', '.join(MODE_LETTERS)})", file=sys.stderr)
        return 2
    root = resolve_root(args.root)
    append_row(root, args.room, epoch_minutes, target_tenths, actual_tenths, mode)
    return 0


if __name__ == "__main__":
    sys.exit(main())
