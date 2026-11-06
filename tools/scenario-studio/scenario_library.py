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
from datetime import datetime
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


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-") or "scenario"


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}")


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


def add(path, name=None, group=UNSORTED, brief=None):
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

    remove_parser = sub.add_parser("remove", help="move a scenario and its brief to .trash")
    remove_parser.add_argument("--path", required=True)

    args = parser.parse_args()
    if args.command == "list":
        print(json.dumps(load_index(), indent=2, ensure_ascii=False))
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
    elif args.command == "remove":
        print(json.dumps(remove(args.path), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
