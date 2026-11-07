#!/usr/bin/env python3
"""Pick up daily journal bundles from the mail-filter folder.

The controller can email one compact bundle per day (`journal-export.py`). A
mail filter saves the attachment to a folder; this tool finds the bundles there,
extracts any it has not seen, turns each into a scenario and adds it to the
Studio's **Journal** group. It runs at Studio startup, and by hand:

    python3 journal_inbox.py --scan
    python3 journal_inbox.py --scan --inbox ~/Downloads/RBR

The folder defaults to `~/RBR-journal`. A `studio-config.json` beside this
script (written by `configure-studio.py`) can name another folder; a one-line
`fixtures/local/journal-inbox` file overrides it, so the setting lives beside
the rest of the Studio's machine-local data. Imported bundles are kept in
`fixtures/local/journal/<system>-<day>/`, and
`fixtures/local/journal/inbox-seen.json` remembers every archive it has handled
(by SHA-256), so scanning again is a no-op.

A bundle that cannot be read is recorded as failed rather than retried on every
start; a corrected file has a different hash and is picked up then.
"""

from __future__ import annotations

import argparse
import datetime as _datetime
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import journal_bundle
import scenario_library

HERE = pathlib.Path(__file__).resolve().parent
LOCAL = HERE / "fixtures" / "local"
JOURNAL = LOCAL / "journal"
DRAFTS = LOCAL / "drafts"
STATE = JOURNAL / "inbox-seen.json"
POINTER = LOCAL / "journal-inbox"
CONFIG = HERE / "studio-config.json"
DEFAULT_INBOX = pathlib.Path.home() / "RBR-journal"
DEFAULT_GROUP = "Journal"


def slug(text) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-") or "rbr"


def config_inbox(path=None) -> str:
    """The inbox named in studio-config.json, or "" when there is none."""
    path = pathlib.Path(path) if path else CONFIG
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    if not isinstance(data, dict):
        return ""
    value = data.get("journalInbox") or data.get("inbox")
    return str(value).strip() if value else ""


def resolve_inbox(explicit=None, pointer=None, config=None) -> pathlib.Path:
    """The configured folder: --inbox, env, studio-config, pointer, then ~/RBR-journal."""
    if explicit:
        return pathlib.Path(explicit).expanduser()
    environment = os.environ.get("RBR_STUDIO_INBOX", "").strip()
    if environment:
        return pathlib.Path(environment).expanduser()
    configured = config_inbox(config)
    if configured:
        return pathlib.Path(configured).expanduser()
    pointer = pathlib.Path(pointer) if pointer else POINTER
    if pointer.is_file():
        try:
            value = pointer.read_text(encoding="utf-8").strip()
        except OSError:
            value = ""
        if value:
            return pathlib.Path(value).expanduser()
    return DEFAULT_INBOX


def load_state(path) -> dict:
    try:
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_state(path, state) -> None:
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(state, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8")
    os.replace(temporary, path)


def _archives(inbox: pathlib.Path) -> list[pathlib.Path]:
    found = []
    for pattern in ("*.tar.gz", "*.tgz"):
        found.extend(inbox.glob(pattern))
    unique = {}
    for path in found:
        if path.is_file():
            unique[str(path.resolve())] = path
    return [unique[key] for key in sorted(unique)]


def _manifest(archive: pathlib.Path) -> dict:
    bundle = journal_bundle.open_bundle(archive)
    try:
        return dict(bundle.manifest)
    finally:
        bundle.close()


def _scenario_name(manifest: dict) -> str:
    day = manifest.get("day") or "unknown"
    system = str(manifest.get("system") or "").strip()
    return f"Journal {day}" if not system else f"Journal {day} — {system}"


def _existing_bundle(journal_dir: pathlib.Path, day: str, system) -> pathlib.Path | None:
    """A bundle for the same system and day, whatever folder an importer gave it."""
    if not journal_dir.is_dir():
        return None
    for candidate in journal_dir.iterdir():
        manifest_path = candidate / "manifest.json"
        if not candidate.is_dir() or not manifest_path.is_file():
            continue
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if data.get("day") == day and data.get("system") == system:
            return candidate
    return None


def scan(inbox=None, journal_dir=None, drafts_dir=None, state_path=None,
         group=DEFAULT_GROUP, quiet=False, pointer=None, config=None) -> list[dict]:
    """Import unseen bundles and return one record per newly handled archive."""
    inbox = resolve_inbox(inbox, pointer, config)
    journal_dir = pathlib.Path(journal_dir) if journal_dir else JOURNAL
    drafts_dir = pathlib.Path(drafts_dir) if drafts_dir else DRAFTS
    state_path = pathlib.Path(state_path) if state_path else STATE
    say = (lambda message: None) if quiet else (lambda message: print(message, flush=True))

    if not inbox.is_dir():
        say(f"journal_inbox.py: no inbox at {inbox} — set the mail filter there, "
            "or name another folder with --inbox")
        return []

    state = load_state(state_path)
    handled = []
    for archive in _archives(inbox):
        digest = journal_bundle.sha256_file(archive)
        if digest in state:
            continue
        record = {
            "archive": archive.name,
            "sha256": digest,
            "seenAt": _datetime.datetime.now(_datetime.timezone.utc).isoformat(timespec="seconds"),
        }
        try:
            manifest = _manifest(archive)
        except Exception as exc:  # noqa: BLE001 - a partial or wrong file must not stop the scan
            record.update(status="failed", error=f"not a readable bundle: {exc}")
            state[digest] = record
            save_state(state_path, state)
            say(f"journal_inbox.py: skipped {archive.name} — {record['error']}")
            continue
        if manifest.get("format") != journal_bundle.BUNDLE_FORMAT or not manifest.get("day"):
            record.update(status="failed",
                          error="not an RBR journal bundle (manifest format/day missing)")
            state[digest] = record
            save_state(state_path, state)
            say(f"journal_inbox.py: skipped {archive.name} — {record['error']}")
            continue

        day = manifest["day"]
        system = manifest.get("system") or "rbr"
        target = journal_dir / f"{slug(system)}-{day}"
        record.update(day=day, system=manifest.get("system"), bundle=str(target))
        existing = _existing_bundle(journal_dir, day, manifest.get("system"))
        if existing is not None or target.exists():
            found = existing or target
            record.update(status="present", bundle=str(found),
                          note="already imported from another source")
            state[digest] = record
            save_state(state_path, state)
            continue

        try:
            journal_bundle.extract_bundle(archive, target)
            report_count = len(list((target / "reports" / "heatlog").rglob("*.csv")))
            name = _scenario_name(manifest)
            drafts_dir.mkdir(parents=True, exist_ok=True)
            draft = drafts_dir / f"journal-{slug(system)}-{day}.json"
            command = [sys.executable, str(HERE / "journal_to_scenario.py"),
                       "--bundle", str(target), "--out", str(draft), "--name", name]
            result = subprocess.run(command, cwd=HERE, capture_output=True, text=True)
            if result.returncode != 0:
                detail = (result.stderr or result.stdout or "").strip().splitlines()
                raise RuntimeError(detail[-1] if detail else f"exit {result.returncode}")
            entry = scenario_library.add(draft, name=name, group=group)
        except (Exception, SystemExit) as exc:  # noqa: BLE001 - keep the bundle, report it
            # Do not leave a half-imported folder behind: a corrected bundle
            # for the same day must be able to take the same target path.
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
            record.update(status="failed", error=str(exc) or exc.__class__.__name__)
            state[digest] = record
            save_state(state_path, state)
            say(f"journal_inbox.py: imported {day} into {target}, but no scenario was made — {record['error']}")
            continue

        record.update(status="imported", scenario=entry["path"], reports=report_count)
        state[digest] = record
        save_state(state_path, state)
        handled.append(record)
        say(f"journal_inbox.py: {day} → {entry['path']} ({report_count} heatlog CSV(s))")
    return handled


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="journal_inbox.py",
        description="Import daily journal bundles from the mail-filter folder")
    parser.add_argument("--scan", action="store_true",
                        help="scan the folder (the default action)")
    parser.add_argument("--inbox", help="folder holding the emailed .tar.gz attachments "
                                       f"(default: {DEFAULT_INBOX})")
    parser.add_argument("--journal-dir", help="where extracted bundles are kept "
                                             "(default: fixtures/local/journal)")
    parser.add_argument("--config", help="studio config file "
                                        "(default: studio-config.json beside this script)")
    parser.add_argument("--group", default=DEFAULT_GROUP, help="library group (default: Journal)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    handled = scan(inbox=args.inbox, journal_dir=args.journal_dir, group=args.group,
                   quiet=args.quiet, config=args.config)
    if not args.quiet:
        print(f"journal_inbox.py: {len(handled)} new bundle(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
