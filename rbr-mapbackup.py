#!/usr/bin/env python3
"""rbr-mapbackup.py — rolling history for map.json, and repair if it breaks.

The controller saves map.json with AllSpeak's `save`, which is a plain
open/write (as_core.py), so a power cut part-way through leaves a truncated
file. AllSpeak cannot catch that: its `load ... or ...` clause fires for a
missing file but raises a Runtime Error for one that will not parse — so a
truncated map.json makes controller.service crash-loop rather than fall back.

This keeper is the safety net, and it runs as a user service so a repair
happens automatically after a power cut:

  * validates map.json (parses, and carries a `profiles` list) before
    trusting it. An invalid file is re-read once first, so a save that
    happens to be in flight is never mistaken for corruption;
  * stores each DISTINCT valid revision in map-history/ (newest --keep,
    default 10) and maintains map-last-good.json as a stable pointer to the
    newest valid revision. Because every stored copy was validated on the
    way in, every copy in the history is loadable;
  * if map.json is damaged, keeps it for forensics as map-corrupt-<ts>.json
    and restores map-last-good.json over map.json — or, with nothing valid
    to restore, simply moves the damaged file aside, which is the controller's
    documented path for a missing map (it builds its default map).

Every write here is atomic (temp file + os.replace), matching the bridge's
temperature file and rbr-updater.py.

Usage:
    rbr-mapbackup.py [--dir DIR] [--keep N] [--quiet]

--dir defaults to this script's directory, i.e. the controller directory
holding map.json. Installed as rbr-mapbackup.service + rbr-mapbackup.timer
by rbr-setup.sh.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time

MAP = "map.json"
LAST_GOOD = "map-last-good.json"
HISTORY_DIR = "map-history"
PREFIX = "map-"
CORRUPT_PREFIX = "map-corrupt-"
# How long to wait before re-reading a file that failed to parse, so a save in
# progress (the controller rewrites the whole file) is not read as corruption.
RECHECK_DELAY = 0.75
# Damaged files are kept for forensics; only the most recent few.
CORRUPT_KEEP = 3


def log(message):
    print(f"mapbackup: {message}", flush=True)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data):
    """Write bytes to path via a temp file in the same directory, then rename."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".mapbackup-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(tmp, path)
    except OSError:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def validate(raw):
    """Return (True, "") if raw looks like a usable RBR map, else (False, why)."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return False, f"not valid JSON ({exc})"
    if not isinstance(data, dict):
        return False, "top level is not an object"
    if not isinstance(data.get("profiles"), list):
        return False, "no 'profiles' list"
    return True, ""


def read_map(path):
    """Read path, re-reading once if it does not parse. Returns (raw, ok, why)."""
    raw = open(path, "rb").read()
    ok, why = validate(raw)
    if ok:
        return raw, True, ""
    time.sleep(RECHECK_DELAY)
    raw = open(path, "rb").read()
    ok, why = validate(raw)
    return raw, ok, why


def prune(directory, prefix, keep):
    """Delete all but the newest `keep` files matching prefix in directory."""
    if keep <= 0:
        entries = []
    else:
        entries = sorted(name for name in os.listdir(directory)
                         if name.startswith(prefix) and name.endswith(".json"))
    for name in entries[:max(0, len(entries) - keep)]:
        os.remove(os.path.join(directory, name))
        log(f"pruned {name}")


def repair(base, map_path, last_good, raw, why):
    """Deal with an unreadable map.json. Returns 0 (nothing here is fatal)."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    damaged = os.path.join(base, f"{CORRUPT_PREFIX}{stamp}.json")

    good = None
    if os.path.exists(last_good):
        candidate = open(last_good, "rb").read()
        ok, candidate_why = validate(candidate)
        if ok:
            good = candidate
        else:
            log(f"{LAST_GOOD} is also unusable ({candidate_why})")

    if good is None:
        # Nothing to restore from: move the damaged file aside so the
        # controller's own LoadMap takes its "no map" path and builds the
        # default map, which is better than crash-looping on a broken file.
        os.replace(map_path, damaged)
        log(f"{MAP} is unreadable ({why}) and there is no good revision to "
            f"restore — moved it to {os.path.basename(damaged)} so the "
            f"controller rebuilds a default map")
        return 0

    shutil.copyfile(map_path, damaged)
    atomic_write(map_path, good)
    rooms = 0
    try:
        data = json.loads(good)
        for profile in data.get("profiles") or []:
            rooms += len(profile.get("rooms") or [])
            break
    except Exception:
        pass
    log(f"{MAP} was unreadable ({why}) — restored {len(good)} bytes from "
        f"{LAST_GOOD} ({rooms} room(s) in the first profile); the damaged copy "
        f"is kept as {os.path.basename(damaged)}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Keep a rolling history of map.json.")
    parser.add_argument("--dir", default=os.path.dirname(os.path.abspath(__file__)),
                        help="controller directory holding map.json")
    parser.add_argument("--keep", type=int, default=10,
                        help="number of revisions to keep (default 10)")
    parser.add_argument("--quiet", action="store_true",
                        help="only report changes, repairs and problems")
    args = parser.parse_args()

    base = os.path.abspath(args.dir)
    map_path = os.path.join(base, MAP)
    last_good = os.path.join(base, LAST_GOOD)
    history = os.path.join(base, HISTORY_DIR)

    if not os.path.exists(map_path):
        if not args.quiet:
            log(f"no {MAP} in {base} — nothing to do")
        return 0

    try:
        raw, ok, why = read_map(map_path)
    except OSError as exc:
        log(f"cannot read {MAP}: {exc}")
        return 0

    if not ok:
        return repair(base, map_path, last_good, raw, why)

    os.makedirs(history, exist_ok=True)
    current = digest(raw)

    if os.path.exists(last_good) and digest(open(last_good, "rb").read()) == current:
        if not args.quiet:
            log(f"{MAP} unchanged since the newest revision — nothing stored")
    else:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        dest = os.path.join(history, f"{PREFIX}{stamp}.json")
        suffix = 1
        while os.path.exists(dest):
            dest = os.path.join(history, f"{PREFIX}{stamp}-{suffix}.json")
            suffix += 1
        atomic_write(dest, raw)
        atomic_write(last_good, raw)
        profiles = 0
        try:
            profiles = len(json.loads(raw).get("profiles") or [])
        except Exception:
            pass
        log(f"stored {os.path.basename(dest)} "
            f"({len(raw)} bytes, {profiles} profile(s)) as the newest revision")

    prune(history, PREFIX, args.keep)
    prune(base, CORRUPT_PREFIX, CORRUPT_KEEP)
    return 0


if __name__ == "__main__":
    sys.exit(main())
