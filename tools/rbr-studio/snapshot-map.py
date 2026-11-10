#!/usr/bin/env python3
"""Copy the current system map into a local fixture and generate a starter scenario.

The live map is expected at `map.json` beside this script, so the studio folder
can be copied to another machine and given that machine's map.

The controller's `map.json` on disk is not quite the map the page receives: the
controller strips the derived fields (relaysTotal, relaysFailed, status and the
readings) before writing it, and adds them back in its reply. This script copies
a map into `fixtures/local/`, fills those fields from what the disk map does
have, and writes a small scenario that reports one room's temperature.

    cd tools/rbr-studio
    python3 snapshot-map.py                 # uses map.json beside this script
    python3 snapshot-map.py --source /path/to/map.json
    python3 snapshot-map.py --source ... --out fixtures/local/us.json --no-scenario

`fixtures/local/` is gitignored: it contains real room names and device ids.
The generated scenario is picked up by studio.allspeak as "Local system" on its
next start.
"""

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_SOURCE = HERE / "map.json"
DEFAULT_OUT = HERE / "fixtures" / "local" / "home.json"


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-") or "system"


def read_map(path):
    with open(path, "r", encoding="utf-8") as handle:
        base = json.load(handle)
    if not isinstance(base.get("rooms"), list) or not isinstance(base.get("profiles"), list):
        raise SystemExit(f"{path}: not a system map (rooms[] and profiles[] are required)")
    return base


def profile_index(base):
    value = base.get("profile", 0)
    if isinstance(value, int) and 0 <= value < len(base.get("profiles", [])):
        return value
    if isinstance(value, str):
        for i, profile in enumerate(base.get("profiles", [])):
            if profile.get("name") == value:
                return i
    return 0


def normalise(base):
    """Fill the fields the page derives, which the disk map does not carry."""
    out = json.loads(json.dumps(base))
    profiles = out.get("profiles", [])
    idx = profile_index(out)
    out["profile"] = idx
    active = profiles[idx].get("name") if profiles else ""

    for room in out.get("rooms", []):
        relays = room.get("relays") or []
        relayfails = room.get("relayfails") or []
        if "relaysTotal" not in room:
            room["relaysTotal"] = len(relays)
        if "relaysFailed" not in room:
            room["relaysFailed"] = sum(1 for count in relayfails if count)
        room.setdefault("linked", "yes")
        room.setdefault("relay", "off")
        room.setdefault("status", "good")
        room.setdefault("statusMessage", "")

    if not isinstance(out.get("calendar-data"), list) or len(out["calendar-data"]) != 7:
        out["calendar-data"] = [
            {f"day{i}-profile": active} for i in range(7)
        ]
    return out, idx, active


def first_room(base):
    rooms = [room for room in base.get("rooms", [])
             if room.get("name") and not (room.get("name") == "Outside" and not room.get("relays"))]
    if not rooms:
        raise SystemExit("the map has no room to build a scenario from")
    return rooms[0]


def starter_scenario(base, idx, active, room):
    current = room.get("temperature")
    try:
        current = int(current)
    except (TypeError, ValueError):
        current = 2000
    if current <= 0:
        current = 2000
    new_temp = current + 10
    expected = f"{new_temp / 100:.1f}"
    name = base.get("name") or "Current system"
    return {
        "schemaVersion": 1,
        "name": f"Local system — {name}",
        "description": "Generated from the current system map: report one room's temperature.",
        "clock": {"start": "2026-11-05T08:00:00Z", "timeZone": "Europe/London"},
        "home": {
            "map": "home.json",
            "profile": active,
            "calendar": base.get("calendar", "off"),
        },
        "rooms": {"main": room["name"]},
        "defaults": {"stepTimeoutMs": 5000, "screenshots": "failure"},
        "steps": [
            {
                "id": "s1",
                "at": "08:00",
                "controller": {"room": "main", "set": {"temperature": new_temp}},
            },
            {
                "id": "s2",
                "at": "08:00",
                "expect": {"target": "room.main.name", "contains": room["name"]},
            },
            {
                "id": "s3",
                "at": "08:00",
                "expect": {"target": "room.main.temp", "contains": expected},
            },
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remove", action="store_true",
                        help="remove the generated Local system scenario")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE),
                        help="map.json to copy (default: map.json beside snapshot-map.py)")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="destination fixture")
    parser.add_argument("--no-scenario", action="store_true", help="copy the map only; do not generate smoke.json")
    args = parser.parse_args()
    if args.remove:
        scenario_path = DEFAULT_OUT.parent / "smoke.json"
        try:
            scenario_path.unlink()
            print(f"removed {scenario_path}")
        except FileNotFoundError:
            print(f"no {scenario_path}")
        return 0

    source = Path(args.source).resolve()
    if not source.exists():
        raise SystemExit(f"no map at {source}; run this on the controller or pass --source")
    base = read_map(source)
    normalised, idx, active = normalise(base)
    room = first_room(normalised)

    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(normalised, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"map      {out}")
    print(f"system   {normalised.get('name', '(unnamed)')}")
    print(f"profile  {active} (index {idx})")
    print("rooms    " + ", ".join(room.get("name", "?") for room in normalised.get("rooms", [])))
    print(f"starter  {room['name']}")

    if not args.no_scenario:
        scenario = starter_scenario(normalised, idx, active, room)
        scenario_path = out.parent / "smoke.json"
        scenario_path.write_text(json.dumps(scenario, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"scenario {scenario_path}")
        print()
        print("Run it with:")
        try:
            shown = scenario_path.relative_to(HERE)
        except ValueError:
            shown = scenario_path
        print(f"  .venv/bin/python -m scenario_runner --scenario {shown}")
        print("Or restart studio.allspeak: the scenario list will include 'Local system'.")

    print()
    print("fixtures/local/ is gitignored; it holds real room and device names.")


if __name__ == "__main__":
    main()
