#!/usr/bin/env python3
"""One-shot journal ingest for the RBR Studio shell.

Takes a bundle, a raw day, or a local journal root, imports it if necessary,
generates a scenario window, and adds the result to the local RBR Studio
library. Prints progress lines and a final `SCENARIO_PATH=` line for the shell
to select.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

import journal_bundle
import scenario_library

HERE = pathlib.Path(__file__).resolve().parent
DRAFTS = HERE / "fixtures" / "local" / "drafts"
JOURNALS = HERE / "fixtures" / "local" / "journal"


def _run(command):
    result = subprocess.run(command, cwd=HERE, capture_output=True, text=True)
    for line in (result.stdout or "").splitlines():
        print(line)
    for line in (result.stderr or "").splitlines():
        print(line, file=sys.stderr)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    return result.stdout


def _source_kind(source: str):
    path = pathlib.Path(source).expanduser()
    if source.endswith((".tar.gz", ".tgz")):
        return "bundle", path, None
    if path.is_dir() and (path / "manifest.json").is_file():
        return "bundle", path, None
    if source.endswith(".jsonl"):
        return "journal", path, None
    return "root", path, None


def _manifest_day(bundle_path: pathlib.Path | None) -> str | None:
    if bundle_path is None:
        return None
    try:
        bundle = journal_bundle.open_bundle(bundle_path)
    except Exception:  # noqa: BLE001 - a missing manifest just means no default day
        return None
    try:
        return bundle.manifest.get("day")
    finally:
        bundle.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True,
                        help="bundle, .jsonl, or local journal root")
    parser.add_argument("--day", help="journal day (YYYY-MM-DD); required for a local root")
    parser.add_argument("--from", dest="start", help="window start (HH:MM or ISO)")
    parser.add_argument("--to", dest="end", help="window end (HH:MM or ISO)")
    parser.add_argument("--name", help="scenario name")
    parser.add_argument("--group", default="Journal", help="library group (default: Journal)")
    parser.add_argument("--system", help="controller MAC the journal belongs to")
    parser.add_argument("--timezone", default="Europe/London")
    parser.add_argument("--map", help="base map for a raw journal without snapshots")
    parser.add_argument("--no-add", action="store_true", help="generate the draft but do not add it to the library")
    args = parser.parse_args(argv)

    kind, one, _ = _source_kind(args.source)
    bundle = None
    if kind == "bundle":
        bundle = one
        day = args.day or _manifest_day(bundle)
    elif kind == "journal":
        day = args.day or pathlib.Path(one).stem
    else:
        if not args.day:
            raise SystemExit("journal_ingest.py: --day is required for a local journal root")
        day = args.day

    name = args.name or f"Journal {day or ''}".strip()
    if args.start or args.end:
        name += f" {args.start or 'start'}-{args.end or 'end'}"

    if kind == "root":
        # A day bundle is a cache, not a source of truth: always refresh it.
        # Reusing an existing directory made a second Import journal return the
        # events downloaded before the window had happened.
        bundle = JOURNALS / f"{day}"
        _run([sys.executable, str(HERE / "journal_import.py"),
              "--source", str(pathlib.Path(one).expanduser()), "--day", day,
              "--dest", str(bundle), "--force"])

    DRAFTS.mkdir(parents=True, exist_ok=True)
    draft = DRAFTS / f"journal-{day or 'unknown'}-{(args.start or 'start').replace(':','')}-{(args.end or 'end').replace(':','')}.json"
    command = [sys.executable, str(HERE / "journal_to_scenario.py"),
               "--out", str(draft), "--timezone", args.timezone]
    if bundle is not None:
        command += ["--bundle", str(bundle)]
    else:
        command += ["--journal", str(one)]
        if args.map:
            command += ["--map", str(pathlib.Path(args.map).expanduser())]
    if args.start:
        command += ["--from", args.start]
    if args.end:
        command += ["--to", args.end]
    if args.name:
        command += ["--name", args.name]
    _run(command)
    print(f"DRAFT={draft}")

    if args.no_add:
        return 0
    entry = scenario_library.add(draft, name=name, group=args.group,
                                 system=args.system, day=day)
    path = pathlib.Path("fixtures") / "local" / "scenarios" / entry["path"]
    print(f"SCENARIO_PATH={path.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
