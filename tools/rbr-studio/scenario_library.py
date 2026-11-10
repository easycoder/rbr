#!/usr/bin/env python3
"""The studio's local scenario library.

Scenarios live under `fixtures/local/scenarios/<group>/`; each may have a
sibling `<stem>.brief.md` holding the brief it was generated from. The shell
reads `index.json` and shows the groups as a filter. The whole directory is
ignored: scenario and brief files contain real room names. Deleting moves both
files to `fixtures/local/.trash/` rather than unlinking them.

    python3 scenario_library.py list
    python3 scenario_library.py seed-examples
    python3 scenario_library.py add --path fixtures/local/drafts/office.json \
        --group "Office" --brief-file fixtures/local/drafts/office.brief.md
    python3 scenario_library.py group --name "Schedules"
    python3 scenario_library.py duplicate --path fixtures/local/scenarios/journal/day.json \
        --name "Office only" --room Office
    python3 scenario_library.py remove --path fixtures/local/scenarios/office/office.json

`add` copies a file from outside the library into the group folder, rewrites a
relative `home.map` for the new depth, and records the brief. Existing flat
entries remain readable; their group is `Unsorted`.
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOCAL = HERE / "fixtures" / "local"
SCENARIOS = LOCAL / "scenarios"
TRASH = LOCAL / ".trash"
INDEX = SCENARIOS / "index.json"
UNSORTED = "Unsorted"
EXAMPLES = HERE / "docs" / "examples"
EXAMPLES_GROUP = "Examples"
SEED_FLAG = LOCAL / ".examples-seeded"
JOURNAL_SEEN = LOCAL / "journal" / "inbox-seen.json"


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-") or "scenario"


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}")


def _seen_by_scenario():
    """Scenario path -> the inbox record that imported it (MAC and day)."""
    data = read_json(JOURNAL_SEEN, {})
    seen = {}
    if isinstance(data, dict):
        for record in data.values():
            if isinstance(record, dict) and record.get("scenario"):
                seen[str(record["scenario"])] = record
    return seen


def _file_date(path):
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
    except OSError:
        return None


def _backfill_metadata(data):
    """Fill system and date on entries written before those fields existed.

    Journal entries can recover both from the inbox's own record; anything else
    gets the scenario file's modification date, which is what the year browser
    and the week filter have to work with. This runs on load and is a no-op once
    every entry carries a date.
    """
    changed = False
    cutoff = datetime.now().date() - timedelta(days=6)
    seen = _seen_by_scenario()
    for item in data["scenarios"]:
        if not isinstance(item, dict):
            continue
        rel = item.get("path")
        record = seen.get(str(rel)) if rel else None
        if record:
            if not item.get("system"):
                system = record.get("mac") or record.get("system")
                if system:
                    item["system"] = str(system)
                    changed = True
            if not item.get("day") and record.get("day"):
                item["day"] = str(record["day"])
                changed = True
        if not item.get("day") and not item.get("created"):
            created = _file_date(SCENARIOS / rel) if rel else None
            if created:
                item["created"] = created
                changed = True
        entry_date = item.get("day") or item.get("created")
        recent = False
        if entry_date:
            try:
                recent = date.fromisoformat(str(entry_date)) >= cutoff
            except ValueError:
                recent = False
        # A working copy is new even when it carries an older journal day; the
        # week list should show the copy its author just made.
        if item.get("duplicate") and item.get("created"):
            try:
                recent = date.fromisoformat(str(item["created"])) >= cutoff
            except ValueError:
                pass
        if item.get("recent") != recent:
            item["recent"] = recent
            changed = True
    return changed


def load_index():
    data = read_json(INDEX, {})
    if not isinstance(data, dict):
        raise SystemExit(f"{INDEX}: expected a JSON object")
    data.setdefault("groups", [])
    data.setdefault("scenarios", [])
    changed = False
    for item in data["scenarios"]:
        if not isinstance(item, dict):
            continue
        if not item.get("group"):
            item["group"] = UNSORTED
            changed = True
    if UNSORTED not in data["groups"]:
        data["groups"].append(UNSORTED)
        changed = True
    if _backfill_metadata(data):
        changed = True
    data["groups"] = sorted(set(data["groups"]), key=str.lower)
    if changed:
        save_index(data)
    return data


def save_index(data):
    SCENARIOS.mkdir(parents=True, exist_ok=True)
    data["groups"] = sorted(set(data.get("groups", [])), key=str.lower)
    INDEX.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def group_dir(group):
    directory = SCENARIOS / slug(group)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def unique_stem(directory, stem):
    candidate = stem
    n = 2
    while (directory / f"{candidate}.json").exists():
        candidate = f"{stem}-{n}"
        n += 1
    return candidate


def _relocated_map(data, source, target):
    """Keep a relative home.map pointing at the same file after the copy."""
    home = data.get("home")
    if not isinstance(home, dict):
        return data
    value = home.get("map")
    if not isinstance(value, str) or not value or os.path.isabs(value):
        return data
    source_map = (source.parent / value).resolve()
    if source_map.exists():
        home["map"] = os.path.relpath(source_map, target.parent)
    return data


def add(path, name=None, group=UNSORTED, brief=None, system=None, day=None,
        duplicate=False):
    """Make `path` a library scenario and return its manifest entry."""
    source = Path(path).resolve()
    data = read_json(source)
    if not isinstance(data, dict):
        raise SystemExit(f"{source}: the scenario must be a JSON object")
    group = (group or UNSORTED).strip() or UNSORTED
    name = name or data.get("name") or source.stem
    directory = group_dir(group)

    if source.parent == directory:
        target = source
    else:
        target = directory / f"{unique_stem(directory, slug(name))}.json"
        data = _relocated_map(data, source, target)
        target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if brief is None:
        sibling = source.with_name(source.stem + ".brief.md")
        if sibling.exists():
            brief = sibling.read_text(encoding="utf-8")
        elif isinstance(data.get("description"), str):
            brief = data["description"]
    brief_rel = None
    if brief:
        brief_path = target.with_name(target.stem + ".brief.md")
        brief_path.write_text(str(brief).rstrip() + "\n", encoding="utf-8")
        brief_rel = brief_path.relative_to(SCENARIOS).as_posix()

    entry = {
        "id": target.stem,
        "name": name,
        "group": group,
        "path": target.relative_to(SCENARIOS).as_posix(),
    }
    if brief_rel:
        entry["brief"] = brief_rel
    if system:
        entry["system"] = str(system)
    if day:
        entry["day"] = str(day)
    if duplicate:
        entry["duplicate"] = True
        entry["created"] = datetime.now().date().isoformat()
    elif not day:
        entry["created"] = datetime.now().date().isoformat()

    index = load_index()
    if group not in index["groups"]:
        index["groups"].append(group)
    index["scenarios"] = [item for item in index["scenarios"]
                          if item.get("path") != entry["path"]]
    index["scenarios"].append(entry)
    index["scenarios"].sort(key=lambda item: (str(item.get("group", "")).lower(),
                                              str(item.get("name", "")).lower()))
    save_index(index)
    return entry


def seed_examples(force=False):
    """Copy the public example scenarios into the local library once.

    They become ordinary deletable scenarios in the Examples group. The
    public files stay in docs/examples for the README and the test suite; the
    Studio list uses the copies, so deleting one cannot break those.
    """
    if SEED_FLAG.exists() and not force:
        return []
    sources = (
        ("advance.json", "Advance at 15:00"),
        ("temperature.json", "Kitchen temperature"),
        ("delay.json", "Delay demo"),
    )
    index = load_index()
    existing = {(item.get("group"), item.get("name")) for item in index["scenarios"]}
    created = []
    LOCAL.mkdir(parents=True, exist_ok=True)
    DRAFTS = LOCAL / "drafts"
    DRAFTS.mkdir(parents=True, exist_ok=True)
    for filename, label in sources:
        if (EXAMPLES_GROUP, label) in existing:
            continue
        source = EXAMPLES / filename
        if not source.exists():
            continue
        data = read_json(source, {})
        home = data.get("home") if isinstance(data, dict) else None
        if isinstance(home, dict) and isinstance(home.get("map"), str):
            candidate = (EXAMPLES / home["map"]).resolve()
            if candidate.exists():
                # Inline the shared fixture so the library copy is self-contained.
                home["map"] = read_json(candidate, {})
        data["name"] = label
        draft = DRAFTS / f"_seed-{slug(label)}.json"
        draft.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        try:
            created.append(add(draft, name=label, group=EXAMPLES_GROUP,
                               brief=data.get("description")))
        finally:
            draft.unlink(missing_ok=True)
    SEED_FLAG.write_text("seeded\n", encoding="utf-8")
    return created


OUTDOOR_ROOMS = ("Outside",)


def _scenario_aliases(data):
    aliases = data.get("rooms")
    if not isinstance(aliases, dict):
        return {}
    return {str(alias): str(name) for alias, name in aliases.items()
            if isinstance(name, str)}


def _scenario_map(data, source=None):
    """Return the base map when it is inline or a readable sibling file."""
    home = data.get("home")
    if not isinstance(home, dict):
        return None
    value = home.get("map")
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute() and source is not None:
        path = Path(source).resolve().parent / path
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _room_names(data, source=None):
    aliases = _scenario_aliases(data)
    names = set(aliases) | set(aliases.values())
    base = _scenario_map(data, source)
    if isinstance(base, dict):
        for room in base.get("rooms", []) or []:
            if isinstance(room, dict) and isinstance(room.get("name"), str):
                names.add(room["name"])
    return names


def _canonical_room(name, aliases):
    return aliases.get(name, name)


def _target_rooms(target, aliases):
    """Room names named by a semantic target, or an empty set for a global one."""
    if not isinstance(target, str):
        return set()
    parts = target.split(".")
    if len(parts) >= 3 and parts[0] == "room":
        return {_canonical_room(parts[1], aliases)}
    if len(parts) >= 4 and parts[0] == "devices" and parts[1] == "room":
        return {_canonical_room(".".join(parts[2:-1]), aliases)}
    return set()


def step_room_refs(step, aliases):
    """Canonical room names a step names; an empty set means a global step."""
    if not isinstance(step, dict):
        return set()
    refs = set()
    controller = step.get("controller")
    if isinstance(controller, dict):
        room = controller.get("room")
        if isinstance(room, str) and room:
            refs.add(_canonical_room(room, aliases))
    ui = step.get("ui")
    if isinstance(ui, dict):
        if "tap" in ui:
            refs |= _target_rooms(ui.get("tap"), aliases)
        for key in ("select", "fill", "scroll"):
            entry = ui.get(key)
            if isinstance(entry, dict):
                refs |= _target_rooms(entry.get("target"), aliases)
    user = step.get("user")
    if isinstance(user, dict):
        room = user.get("room")
        if isinstance(room, str) and room:
            refs.add(_canonical_room(room, aliases))
    for key in ("expect", "waitFor"):
        entry = step.get(key)
        if isinstance(entry, dict):
            refs |= _target_rooms(entry.get("target"), aliases)
    wire = step.get("expectWire")
    if isinstance(wire, dict):
        for key in ("match", "notMatch"):
            entry = wire.get(key)
            if isinstance(entry, dict):
                for field in ("Room", "room"):
                    if isinstance(entry.get(field), str):
                        refs.add(_canonical_room(entry[field], aliases))
    return refs


def renumber_steps(data):
    """Give a scenario's steps sequential ids, so a filtered copy has no gaps."""
    steps = data.get("steps")
    if not isinstance(steps, list):
        return data
    for index, step in enumerate(steps, start=1):
        if isinstance(step, dict):
            step["id"] = f"s{index}"
    return data


def _is_temperature_step(step):
    """True when the step's room-specific effect is a temperature reading."""
    controller = step.get("controller")
    if isinstance(controller, dict):
        fields = set()
        if isinstance(controller.get("set"), dict):
            fields |= set(controller["set"])
        state = controller.get("state")
        if isinstance(state, dict) and isinstance(state.get("set"), dict):
            fields |= set(state["set"])
        if "temperature" in fields:
            return True
    for key in ("expect", "waitFor"):
        entry = step.get(key)
        if isinstance(entry, dict):
            target = entry.get("target")
            if isinstance(target, str) and target.split(".")[-1] in ("temp", "temperature"):
                return True
    wire = step.get("expectWire")
    if isinstance(wire, dict):
        for key in ("match", "notMatch"):
            entry = wire.get(key)
            if isinstance(entry, dict) and "temperature" in entry:
                return True
    return False


def filter_to_room(data, room, source=None):
    """Keep global steps and steps naming `room`; return (data, kept, total).

    A global step is one that names no room at all: summary and sheet actions,
    profile or wire-level checks, `raw` pushes, connections and delays. The
    outdoor pseudo-room is kept only for temperature readings; its relay,
    status and mode events are dropped. A step carrying the marker is always
    kept, because it is the breakpoint and dropping it would lose the place to
    stop. Kept steps are renumbered because the dropped steps would otherwise
    leave gaps in the id sequence.
    """
    if not isinstance(data, dict):
        raise SystemExit("scenario_library.py: the scenario must be a JSON object")
    aliases = _scenario_aliases(data)
    name = (room or "").strip()
    if not name:
        raise SystemExit("scenario_library.py: a room name is required")
    canonical = _canonical_room(name, aliases)
    known = _room_names(data, source)
    if known and canonical not in known:
        raise SystemExit(
            f"scenario_library.py: no room named {name!r} in the scenario "
            f"(known: {', '.join(sorted(known, key=str.lower))})")
    steps = data.get("steps")
    if not isinstance(steps, list):
        raise SystemExit("scenario_library.py: the scenario has no steps[]")
    outdoor_rooms = set(OUTDOOR_ROOMS)
    kept = []
    for step in steps:
        refs = step_room_refs(step, aliases)
        if step.get("marker"):
            kept.append(step)  # the breakpoint is a control, not room data
        elif not refs or canonical in refs:
            kept.append(step)
        elif refs & outdoor_rooms and _is_temperature_step(step):
            kept.append(step)
    if not kept:
        raise SystemExit(
            f"scenario_library.py: no steps name {canonical!r} and the scenario has no global steps")
    data["steps"] = kept
    renumber_steps(data)
    return data, len(kept), len(steps)


def duplicate(path, name=None, group=None, room=None):
    """Copy a scenario (and its brief) into the library as a new entry.

    With `room`, the copy keeps only global steps and those naming that room,
    plus outdoor temperature changes. Other outdoor status/relay/mode events are
    dropped, except the marked step, which is the breakpoint. This makes a
    day-long journal scenario readable when one room is under investigation.
    """
    source = Path(path).resolve()
    data = read_json(source)
    if not isinstance(data, dict):
        raise SystemExit(f"{source}: the scenario must be a JSON object")
    name = (name or f"{data.get('name') or source.stem} copy").strip()
    if not name:
        raise SystemExit("a duplicate name is required")
    if group is None:
        if SCENARIOS in source.parents:
            group = source.parent.relative_to(SCENARIOS).as_posix()
        else:
            group = UNSORTED
    data["name"] = name
    note = None
    if room:
        data, kept, total = filter_to_room(data, room, source)
        note = (f"Filtered copy: global steps, outdoor temperature changes, "
                f"and steps for {room.strip()} only ({kept} of {total} steps; "
                f"the marked step is kept).")
        description = data.get("description")
        if isinstance(description, str) and description.strip():
            data["description"] = description.rstrip() + " " + note
        else:
            data["description"] = note
    draft_dir = LOCAL / "drafts"
    draft_dir.mkdir(parents=True, exist_ok=True)
    draft = draft_dir / f"_duplicate-{slug(name)}.json"
    draft.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    brief = source.with_name(source.stem + ".brief.md")
    source_entry = None
    if SCENARIOS in source.parents:
        rel = source.relative_to(SCENARIOS).as_posix()
        source_entry = next(
            (item for item in load_index()["scenarios"] if item.get("path") == rel),
            None)
    try:
        if brief.exists():
            brief_text = brief.read_text(encoding="utf-8")
            if note:
                brief_text = brief_text.rstrip() + "\n\n" + note
        else:
            brief_text = data.get("description")
        entry = add(draft, name=name, group=group, brief=brief_text,
                    system=(source_entry or {}).get("system"),
                    day=(source_entry or {}).get("day"),
                    duplicate=True)
    finally:
        draft.unlink(missing_ok=True)
    return entry


def rename(path, name):
    """Rename a library scenario's display name without moving its file."""
    source = Path(path).resolve()
    name = (name or "").strip()
    if not name:
        raise SystemExit("a new scenario name is required")
    if SCENARIOS not in source.parents:
        raise SystemExit(f"{source}: only library scenarios can be renamed here")
    if not source.exists():
        raise SystemExit(f"{source}: no such scenario")
    data = read_json(source)
    if not isinstance(data, dict):
        raise SystemExit(f"{source}: the scenario must be a JSON object")
    data["name"] = name
    source.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rel = source.relative_to(SCENARIOS).as_posix()
    index = load_index()
    entry = next((item for item in index["scenarios"] if item.get("path") == rel), None)
    if entry is None:
        raise SystemExit(f"{source}: not in the library index")
    entry["name"] = name
    index["scenarios"].sort(key=lambda item: (str(item.get("group", "")).lower(),
                                              str(item.get("name", "")).lower()))
    save_index(index)
    return entry


def add_group(name):
    """Create an empty group and return its display name."""
    group = (name or "").strip()
    if not group:
        raise SystemExit("a group name is required")
    group_dir(group)
    index = load_index()
    if group not in index["groups"]:
        index["groups"].append(group)
        save_index(index)
    return group


def remove(path):
    """Move a scenario and its brief to .trash and return the moved paths."""
    source = Path(path).resolve()
    if SCENARIOS not in source.parents:
        raise SystemExit(f"{source}: only scenarios under {SCENARIOS} can be removed here")
    if not source.exists():
        raise SystemExit(f"{source}: no such scenario")
    rel = source.relative_to(SCENARIOS).as_posix()
    index = load_index()
    entry = next((item for item in index["scenarios"] if item.get("path") == rel), None)
    brief_rel = entry.get("brief") if entry else None
    brief = (SCENARIOS / brief_rel).resolve() if brief_rel else None

    TRASH.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    moved = []
    target = TRASH / f"{stamp}-{source.name}"
    shutil.move(str(source), str(target))
    moved.append(str(target))
    if brief is not None and brief.exists():
        brief_target = TRASH / f"{stamp}-{brief.name}"
        shutil.move(str(brief), str(brief_target))
        moved.append(str(brief_target))

    index["scenarios"] = [item for item in index["scenarios"] if item.get("path") != rel]
    save_index(index)
    return {"scenario": moved[0], "brief": moved[1] if len(moved) > 1 else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="print the library manifest")
    sub.add_parser("refresh", help="recompute dates and the recent flag, then save")
    seed_parser = sub.add_parser("seed-examples", help="copy the public examples into the library")
    seed_parser.add_argument("--force", action="store_true", help="run even if the seed marker exists")
    seed_parser.add_argument("--quiet", action="store_true", help="suppress the summary")

    add_parser = sub.add_parser("add", help="add or update a scenario")
    add_parser.add_argument("--path", required=True)
    add_parser.add_argument("--name")
    add_parser.add_argument("--group", default=UNSORTED)
    add_parser.add_argument("--brief", help="brief text")
    add_parser.add_argument("--brief-file", help="file holding the brief")

    group_parser = sub.add_parser("group", help="create an empty group")
    group_parser.add_argument("--name", required=True)

    duplicate_parser = sub.add_parser("duplicate", help="copy a scenario and its brief")
    duplicate_parser.add_argument("--path", required=True)
    duplicate_parser.add_argument("--name")
    duplicate_parser.add_argument("--group")
    duplicate_parser.add_argument(
        "--room",
        help="keep global steps, outdoor temperature changes, the marked step, and those naming this room (or alias)")

    rename_parser = sub.add_parser("rename", help="rename a library scenario")
    rename_parser.add_argument("--path", required=True)
    rename_parser.add_argument("--name", required=True)

    remove_parser = sub.add_parser("remove", help="move a scenario and its brief to .trash")
    remove_parser.add_argument("--path", required=True)

    args = parser.parse_args()
    if args.command == "list":
        print(json.dumps(load_index(), indent=2, ensure_ascii=False))
    elif args.command == "refresh":
        load_index()
    elif args.command == "seed-examples":
        created = seed_examples(args.force)
        if not args.quiet:
            print(json.dumps(created, indent=2, ensure_ascii=False))
    elif args.command == "add":
        brief = args.brief
        if args.brief_file:
            brief = Path(args.brief_file).read_text(encoding="utf-8")
        print(json.dumps(add(args.path, args.name, args.group, brief),
                         indent=2, ensure_ascii=False))
    elif args.command == "group":
        print(json.dumps({"group": add_group(args.name)}, indent=2, ensure_ascii=False))
    elif args.command == "duplicate":
        entry = duplicate(args.path, args.name, args.group, args.room)
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        print(f"SCENARIO_PATH=fixtures/local/scenarios/{entry['path']}")
    elif args.command == "rename":
        entry = rename(args.path, args.name)
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        print(f"SCENARIO_PATH=fixtures/local/scenarios/{entry['path']}")
    elif args.command == "remove":
        print(json.dumps(remove(args.path), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
