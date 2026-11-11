#!/usr/bin/env python3
"""Pick up daily journal bundles from the mail-filter folder.

The controller can email one compact bundle per day (`journal-export.py`). A
mail filter saves the attachment to a folder; this tool finds the bundles there,
extracts any it has not seen, turns each into a scenario and adds it to the
Studio's **Journal** group. It runs at Studio startup, and by hand:

    python3 journal_inbox.py --scan
    python3 journal_inbox.py --scan --inbox ~/Downloads/RBR
    python3 journal_inbox.py --reset --system 00:e0:27:5b:31:40 --day 2026-11-07

`--reset` forgets one system's imported journal for a day: it removes the Studio's
state entry, extracted bundle, generated scenario and inbox archive, leaving the
mbox alone so the attachment can be extracted again.

The folder defaults to `~/RBR-journal`, and the scan includes its per-system subfolders (the mail filter can save each system's attachments under `~/RBR-journal/<MAC>/`). A `studio-config.json` beside this script (written by `configure-studio.py`) can name another folder and can map a MAC to a useful system name; a one-line `fixtures/local/journal-inbox` file overrides the folder, so the setting lives beside the rest of the Studio's machine-local data. Imported bundles are kept in `fixtures/local/journal/<MAC-or-system>-<day>/`, and `fixtures/local/journal/inbox-seen.json` remembers every archive it has handled (by SHA-256), so scanning again is a no-op.

A bundle that cannot be read is recorded as failed rather than retried on every
start; a corrected file has a different hash and is picked up then. The one
exception is a day with no map snapshot of its own: it is retried once an
earlier bundle can supply the map, which is what new exports carry directly.
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


def config_data(path=None) -> dict:
    """Read studio-config.json, or {} when it is absent or unusable."""
    path = pathlib.Path(path) if path else CONFIG
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def config_inbox(path=None) -> str:
    """The inbox named in studio-config.json, or "" when there is none."""
    data = config_data(path)
    value = data.get("journalInbox") or data.get("inbox")
    return str(value).strip() if value else ""


def config_systems(path=None) -> dict[str, str]:
    """The MAC-to-name map from studio-config.json, keys normalised to lower case."""
    raw = config_data(path).get("systems")
    if not isinstance(raw, dict):
        return {}
    systems = {}
    for mac, name in raw.items():
        key = str(mac).strip().lower()
        label = str(name).strip()
        if key and label:
            systems[key] = label
    return systems


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
        found.extend(inbox.rglob(pattern))
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


def _system_identity(manifest: dict, systems: dict[str, str] | None = None):
    """Stable folder key and display label: MAC first, then system name, then time for partial bundles."""
    mac = str(manifest.get("mac") or "").strip().lower()
    system = str(manifest.get("system") or "").strip()
    name = str((systems or {}).get(mac) or "").strip()
    label = name or system or mac or "rbr"
    partial = bool(manifest.get("partial"))
    stamp = str(manifest.get("label") or "").strip()
    key = slug(mac) if mac else slug(system or "rbr")
    if partial:
        key = f"{key}-{slug(stamp or manifest.get('requestedAt') or 'partial')}"
        if stamp:
            label = f"{label} {stamp}"
    return mac, system, label, key, partial, stamp


def _scenario_name(manifest: dict, systems: dict[str, str] | None = None) -> str:
    day = manifest.get("day") or "unknown"
    _, _, label, _, _, _ = _system_identity(manifest, systems)
    return f"Journal {day} — {label}" if label and label != "rbr" else f"Journal {day}"


def _existing_bundle(journal_dir: pathlib.Path, day: str, system,
                     mac: str = "", partial: bool = False,
                     stamp: str = "") -> pathlib.Path | None:
    """A bundle for the same system and day (and time, for a partial bundle)."""
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
        if data.get("day") != day:
            continue
        if bool(data.get("partial")) != partial:
            continue
        if partial and str(data.get("label") or "") != stamp:
            continue
        existing_mac = str(data.get("mac") or "").strip().lower()
        if mac and existing_mac and existing_mac == mac:
            return candidate
        if not existing_mac and data.get("system") == system:
            return candidate
    return None


_DATE_SUFFIX = re.compile(r"(\d{4}-\d{2}-\d{2})$")


def _fallback_map(journal_dir: pathlib.Path, day: str):
    """The newest map from an earlier full-day bundle, or None.

    A day whose journal has no map change carries no snapshot of its own, so
    the map in force is the last one imported before it. Only full-day bundle
    directories are considered; a partial bundle's key ends in its time, not
    its day. The manifest lists maps in the order they first appeared, so its
    last row is the newest one.
    """
    if not journal_dir.is_dir():
        return None
    best = None
    for candidate in journal_dir.iterdir():
        if not candidate.is_dir():
            continue
        match = _DATE_SUFFIX.search(candidate.name)
        if not match or match.group(1) >= str(day):
            continue
        rows = []
        try:
            manifest = json.loads((candidate / "manifest.json").read_text(encoding="utf-8"))
            rows = manifest.get("maps") or []
        except (OSError, ValueError):
            rows = []
        path = None
        if rows:
            digest = rows[-1].get("hash")
            if digest:
                path = candidate / "maps" / f"{digest}.json"
        if path is None or not path.is_file():
            maps = sorted((candidate / "maps").glob("*.json"))
            path = maps[-1] if maps else None
        if path is not None and path.is_file():
            if best is None or match.group(1) > best[0]:
                best = (match.group(1), path)
    return best[1] if best else None


def reset(system, day=None, inbox=None, journal_dir=None, drafts_dir=None,
          state_path=None, config=None, quiet=False) -> list[dict]:
    """Forget one system's imported journal for a day, ready for a fresh import.

    The import state, the extracted bundle, the generated scenario and the inbox
    archive are removed. The mbox itself is left alone, so Import mbox can
    extract the attachment again. Nothing outside the Studio's own folders is
    touched.
    """
    system = str(system or "").strip().lower()
    if not system:
        raise SystemExit("journal_inbox.py: --reset needs --system MAC")
    day = str(day or _datetime.date.today().isoformat()).strip()
    inbox = resolve_inbox(inbox, config=config)
    journal_dir = pathlib.Path(journal_dir) if journal_dir else JOURNAL
    drafts_dir = pathlib.Path(drafts_dir) if drafts_dir else DRAFTS
    state_path = pathlib.Path(state_path) if state_path else STATE
    say = (lambda message: None) if quiet else (lambda message: print(message, flush=True))
    state = load_state(state_path)
    removed = []
    for digest, record in list(state.items()):
        if not isinstance(record, dict):
            continue
        record_mac = str(record.get("mac") or "").strip().lower()
        record_system = str(record.get("system") or "").strip().lower()
        if record_mac != system and record_system != system:
            continue
        if str(record.get("day") or "") != day:
            continue
        item = {"archive": record.get("archive"), "bundle": record.get("bundle"),
                "scenario": record.get("scenario")}
        bundle_path = pathlib.Path(record["bundle"]) if record.get("bundle") else None
        if bundle_path is not None:
            try:
                bundle_path.resolve().relative_to(journal_dir.resolve())
                if bundle_path.is_dir():
                    shutil.rmtree(bundle_path)
                    item["bundleRemoved"] = str(bundle_path)
            except ValueError:
                pass
            if bundle_path.name.endswith(f"-{day}"):
                key = bundle_path.name[:-len(day) - 1]
                draft = drafts_dir / f"journal-{key}-{day}.json"
                if draft.is_file():
                    draft.unlink()
                    item["draftRemoved"] = str(draft)
        scenario = str(record.get("scenario") or "").strip()
        if scenario:
            scenario_path = scenario_library.SCENARIOS / scenario
            if scenario_path.is_file():
                try:
                    scenario_library.remove(scenario_path)
                    item["scenarioRemoved"] = scenario
                except SystemExit:
                    pass
        archive_name = str(record.get("archive") or "").strip()
        if archive_name:
            candidates = [inbox / str(record.get("mac") or ""), inbox]
            for directory in candidates:
                archive = directory / archive_name
                if archive.is_file():
                    archive.unlink()
                    item["archiveRemoved"] = str(archive)
                    break
        del state[digest]
        removed.append(item)
        say(f"journal_inbox.py: reset {day} [{record.get('name') or record.get('system') or system}]")
    if removed:
        save_state(state_path, state)
    return removed


def scan(inbox=None, journal_dir=None, drafts_dir=None, state_path=None,
         group=DEFAULT_GROUP, quiet=False, pointer=None, config=None,
         systems=None) -> list[dict]:
    """Import unseen bundles and return one record per newly handled archive."""
    inbox = resolve_inbox(inbox, pointer, config)
    if systems is None:
        systems = config_systems(config)
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
        prior = state.get(digest)
        if prior is not None:
            # A bundle recorded as failed is not retried, with one exception:
            # the day had no map snapshot and a newer importer can now supply
            # the map from the previous bundle. Other failures stay recorded.
            retry = (prior.get("status") == "failed"
                     and "no map snapshot" in str(prior.get("error") or ""))
            if not retry:
                continue
            if not prior.get("day") or _fallback_map(journal_dir, prior["day"]) is None:
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
        mac, system, label, key, partial, stamp = _system_identity(manifest, systems)
        target = journal_dir / f"{key}-{day}"
        record.update(day=day, system=manifest.get("system"), mac=mac, name=label,
                      partial=partial, label=stamp, bundle=str(target))
        existing = _existing_bundle(journal_dir, day, manifest.get("system"), mac,
                                    partial, stamp)
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
            name = _scenario_name(manifest, systems)
            drafts_dir.mkdir(parents=True, exist_ok=True)
            draft = drafts_dir / f"journal-{key}-{day}.json"
            command = [sys.executable, str(HERE / "journal_to_scenario.py"),
                       "--bundle", str(target), "--out", str(draft), "--name", name]
            if not any((target / "maps").glob("*.json")):
                fallback = _fallback_map(journal_dir, day)
                if fallback is not None:
                    command.extend(["--map", str(fallback)])
            result = subprocess.run(command, cwd=HERE, capture_output=True, text=True)
            if result.returncode != 0:
                detail = (result.stderr or result.stdout or "").strip().splitlines()
                raise RuntimeError(detail[-1] if detail else f"exit {result.returncode}")
            entry = scenario_library.add(draft, name=name, group=group,
                                         system=mac or system, day=day)
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

        record.update(status="imported", scenario=entry["path"], reports=report_count,
                      mac=mac, name=label, partial=partial, label=stamp)
        state[digest] = record
        save_state(state_path, state)
        handled.append(record)
        say(f"journal_inbox.py: {day} [{label}] → {entry['path']} ({report_count} heatlog CSV(s))")
    return handled


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="journal_inbox.py",
        description="Import daily journal bundles from the mail-filter folder")
    parser.add_argument("--scan", action="store_true",
                        help="scan the folder (the default action)")
    parser.add_argument("--reset", action="store_true",
                        help="forget one system's imported journal for a day, ready to import again")
    parser.add_argument("--system", help="system MAC for --reset")
    parser.add_argument("--day", help="day for --reset (default: today)")
    parser.add_argument("--inbox", help="folder holding the emailed .tar.gz attachments "
                                       f"(default: {DEFAULT_INBOX})")
    parser.add_argument("--journal-dir", help="where extracted bundles are kept "
                                             "(default: fixtures/local/journal)")
    parser.add_argument("--config", help="studio config file "
                                        "(default: studio-config.json beside this script)")
    parser.add_argument("--group", default=DEFAULT_GROUP, help="library group (default: Journal)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    if args.reset:
        if not args.system:
            parser.error("--reset needs --system MAC")
        removed = reset(system=args.system, day=args.day, inbox=args.inbox,
                        journal_dir=args.journal_dir, config=args.config,
                        quiet=args.quiet)
        if not args.quiet:
            print(f"journal_inbox.py: {len(removed)} journal record(s) reset")
        return 0
    handled = scan(inbox=args.inbox, journal_dir=args.journal_dir, group=args.group,
                   quiet=args.quiet, config=args.config)
    if not args.quiet:
        print(f"journal_inbox.py: {len(handled)} new bundle(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
