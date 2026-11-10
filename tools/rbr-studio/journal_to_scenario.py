#!/usr/bin/env python3
"""Turn a controller journal day into an RBR Studio scenario.

This is the deterministic half of the recorder. It reads a bundle produced by
`journal_import.py`, or a raw daily JSONL plus its maps, and writes an ordinary
scenario JSON that `scenario_runner` can execute.

The generator follows the controller's recorded behaviour: sensor readings and
room-state transitions become controller steps, and the visible changes become
expectations. It deliberately does not replay UI requests as taps; the journal
records the request, but the page's gesture and its timing are not recoverable
from the controller alone. The controller effects of those requests are in the
`room.state` and `plan.snapshot` events and are converted.

Examples:
    python3 journal_to_scenario.py --bundle fixtures/local/journal/qed6-2026-11-06 \
        --from 07:00 --to 09:30 --out fixtures/local/scenarios/kitchen-morning.json

    python3 journal_to_scenario.py --journal /data/rbr-heating/events/2026/11/2026-11-06.jsonl \
        --maps /data/rbr-heating/events/maps --from 2026-11-06T07:00:00Z --to 09:30 \
        --timezone Europe/London --out /tmp/morning.json
"""

from __future__ import annotations

import argparse
import copy
import datetime as _datetime
import json
import pathlib
import re
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import journal_bundle

IDENTITY_FIELDS = (
    "relay", "status", "statusMessage", "relayMessage", "relaysFailed",
    "relaysTotal", "relayfails", "trvrunning", "trvsetpoint", "trvfails",
)
STATE_FIELDS = (
    "mode", "target", "period", "advance", "advanceuntil", "until",
    "prevmode", "boostperiod",
)


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        raise SystemExit(f"journal_to_scenario.py: unknown timezone {name!r}")


def _event_time(event: dict) -> _datetime.datetime | None:
    value = event.get("ts")
    if isinstance(value, str):
        try:
            stamp = _datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=_datetime.timezone.utc)
            return stamp
        except ValueError:
            pass
    ts_ms = event.get("tsMs")
    if isinstance(ts_ms, (int, float)):
        return _datetime.datetime.fromtimestamp(ts_ms / 1000.0, tz=_datetime.timezone.utc)
    return None


def _when(value: str, day: _datetime.date, zone: ZoneInfo) -> _datetime.datetime:
    if ":" in value and "-" not in value and "T" not in value:
        clock = _datetime.time.fromisoformat(value)
        return _datetime.datetime.combine(day, clock, tzinfo=zone)
    stamp = _datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=zone)
    return stamp.astimezone(zone)


def _format_temp(value) -> str | None:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    # Sensor readings are hundredths; the page truncates to one decimal
    # (FormatHundredths divides by 100 and then by 10, both as integers).
    return f"{number // 100}.{(number % 100) // 10}"


def _alias(name: str, used: set[str]) -> str:
    base = re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_") or "room"
    if base[0].isdigit():
        base = "r_" + base
    alias = base
    index = 2
    while alias in used:
        alias = f"{base}_{index}"
        index += 1
    used.add(alias)
    return alias


def _map_profile_index(base_map: dict, profile) -> int | None:
    if isinstance(profile, int):
        return profile if 0 <= profile < len(base_map.get("profiles", [])) else None
    for index, record in enumerate(base_map.get("profiles", [])):
        if record.get("name") == profile:
            return index
    return None


def _user_label(action: str, source: dict, payload: dict) -> str:
    """A short human label for a UI request, from its action and source."""
    control = source.get("control") or ""
    screen = source.get("screen") or ""
    if action == "Operating Mode":
        if control == "advance":
            value = payload.get("advance")
            if value == "A":
                return "Advance on"
            if value == "-":
                return "Advance cancelled"
            return "Advance"
        if control == "boost" or str(payload.get("Mode") or payload.get("mode") or "").lower() == "boost":
            return "Boost"
        if control == "target" or payload.get("target") is not None:
            return "Target"
        mode = payload.get("Mode") or payload.get("mode")
        if mode:
            return f"Mode {mode}"
        return "Operating mode"
    if action == "Update Profiles":
        if screen == "schedule":
            return "Schedule saved"
        if screen in ("profiles", "profile", "calendar"):
            return "Calendar saved"
        return "Profiles updated"
    labels = {
        "Add Room": "Room added",
        "Update Rooms": "Rooms updated",
        "Select Profile": "Profile selected",
        "Room Override": "One-off override",
        "System Name": "System renamed",
        "Request Relay": "Request relay set",
        "Backup": "Backup setting",
        "Backup Now": "Backup started",
        "Journal Now": "Journal exported",
        "Test": "Test request",
    }
    return labels.get(action, action or "UI request")


def _user_event(action: str, source: dict, payload: dict) -> str:
    """The request type a UI action carries, for the Event column."""
    control = (source.get("control") or "").lower()
    screen = (source.get("screen") or "").lower()
    mode = payload.get("Mode") or payload.get("mode") or ""
    if action == "Operating Mode":
        if control == "advance":
            return "Cancel Advance" if payload.get("advance") == "-" else "Advance"
        if control == "boost" or str(mode).lower() == "boost":
            return "Boost"
        if control == "target" or payload.get("target") is not None:
            return "Target"
        return "Mode"
    if action == "Update Profiles":
        if screen == "schedule":
            return "Schedule"
        if screen in ("profiles", "profile", "calendar"):
            return "Calendar"
        return "Update Profiles"
    if action == "Select Profile":
        return "Calendar"
    return action or "UI request"


def _schedule_change(profiles, previous, room):
    """Summarise the room's schedule changes between two profile lists."""
    if not profiles or not previous or not room:
        return ""
    before = {profile.get("name"): profile for profile in previous if isinstance(profile, dict)}
    changes = []
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        name = profile.get("name") or "profile"
        old_profile = before.get(name)
        if not old_profile:
            continue
        old_room = (old_profile.get("rooms") or {}).get(room) or {}
        new_room = (profile.get("rooms") or {}).get(room) or {}
        old_periods = old_room.get("periods") or []
        new_periods = new_room.get("periods") or []
        old_by = {(period.get("on"), period.get("off")): period
                  for period in old_periods if isinstance(period, dict)}
        new_by = {(period.get("on"), period.get("off")): period
                  for period in new_periods if isinstance(period, dict)}
        for key, new in new_by.items():
            old = old_by.get(key)
            label = f"{name} {key[0]}–{key[1]}"
            if old is None:
                changes.append(f"{label}: added at {new.get('temp')} °C")
                continue
            if old.get("temp") != new.get("temp"):
                changes.append(f"{label}: {old.get('temp')} → {new.get('temp')} °C")
            if old.get("enabled", True) != new.get("enabled", True):
                changes.append(f"{label}: {'enabled' if new.get('enabled', True) else 'disabled'}")
        for key in old_by:
            if key not in new_by:
                changes.append(f"{name} {key[0]}–{key[1]}: removed")
    return "; ".join(changes) if changes else "no change"


def _base_map(args, events: list[dict], start: _datetime.datetime, bundle) -> tuple[dict, dict]:
    """Return (map, session event) using the latest map snapshot at or before start."""
    session = next((event for event in events if event.get("type") == "session.start"), {})
    if args.map:
        base = json.loads(pathlib.Path(args.map).expanduser().read_text(encoding="utf-8"))
        return base, session
    start_ms = int(start.timestamp() * 1000)
    candidates = []
    for event in events:
        data = event.get("data") or {}
        if event.get("type") in ("session.start", "plan.snapshot") and data.get("mapHash"):
            if int(event.get("tsMs") or 0) <= start_ms:
                candidates.append(event)
    if not candidates:
        candidates = [event for event in events
                      if (event.get("data") or {}).get("mapHash")]
    if not candidates:
        raise SystemExit("journal_to_scenario.py: no map snapshot in the journal; pass --map")
    chosen = max(candidates, key=lambda event: (event.get("tsMs") or 0, event.get("seq") or 0))
    digest = (chosen.get("data") or {})["mapHash"]
    try:
        base = bundle.load_map(digest)
    except FileNotFoundError:
        raise SystemExit(
            f"journal_to_scenario.py: bundle is missing map {digest}; pass --map")
    return base, session


def _state_fields(data: dict) -> tuple[dict, dict]:
    identity = {key: data[key] for key in IDENTITY_FIELDS if key in data}
    state = {key: data[key] for key in STATE_FIELDS if key in data}
    return identity, state


def _visible(base_map: dict, name: str) -> bool:
    for room in base_map.get("rooms", []):
        if room.get("name") == name:
            return not (name == "Outside" and not room.get("relays"))
    return False


def _step_id(index: int) -> str:
    return f"s{index}"


def _iso(stamp: _datetime.datetime) -> str:
    return stamp.isoformat(timespec="seconds")


def build_scenario(args, bundle, events: list[dict]) -> dict:
    zone = _zone(args.timezone)
    dated = [(event, _event_time(event)) for event in events]
    dated = [(event, stamp) for event, stamp in dated if stamp is not None]
    if not dated:
        raise SystemExit("journal_to_scenario.py: no events with timestamps")
    dated.sort(key=lambda item: (item[1], item[0].get("seq") or 0))
    day = _datetime.date.fromisoformat(bundle.manifest.get("day") or dated[0][1].astimezone(zone).date().isoformat())
    first = dated[0][1].astimezone(zone)
    last = dated[-1][1].astimezone(zone)
    start = _when(args.start, day, zone) if args.start else first
    end = _when(args.end, day, zone) if args.end else last
    if end < start:
        raise SystemExit("journal_to_scenario.py: --to is before --from")

    base, session = _base_map(args, events, start, bundle)
    base = copy.deepcopy(base)
    schedule_profiles = copy.deepcopy(base.get("profiles", []))
    profile = args.profile or (session.get("data") or {}).get("profile")
    profile_index = _map_profile_index(base, profile)
    if profile is None and isinstance(base.get("profile"), int):
        profile = base["profile"]
        profile_index = profile
    if profile_index is not None:
        base["profile"] = profile_index

    aliases = {}
    used = set()
    for room in base.get("rooms", []):
        name = room.get("name")
        if name:
            aliases[_alias(name, used)] = name
    reverse_alias = {name: alias for alias, name in aliases.items()}

    steps = []

    def add_controller(room, at, identity=None, state=None, note=None):
        action = {"room": room}
        if identity:
            action["set"] = identity
        if state:
            entry = {"set": state}
            if profile is not None:
                entry["profile"] = profile
            action["state"] = entry
        step = {"id": _step_id(len(steps) + 1), "at": _iso(at), "controller": action}
        if note:
            step["note"] = note
        steps.append(step)

    def add_expect(at, target, note=None, **expect):
        step = {"id": _step_id(len(steps) + 1), "at": _iso(at),
                "expect": {"target": target, **expect}}
        if note:
            step["note"] = note
        steps.append(step)

    def add_user(room, at, action, source, payload, seq, label=None):
        source = source or {}
        payload = payload or {}
        if not label:
            label = _user_label(action, source, payload)
        event = _user_event(action, source, payload)
        user = {"action": action, "event": event, "label": label}
        if room:
            user["room"] = room
        for key in ("screen", "control", "gesture"):
            value = source.get(key)
            if value:
                user[key] = value
        for key, field in (("advance", "advance"), ("mode", "Mode"),
                           ("target", "Target"), ("profile", "Profile"),
                           ("kind", "kind"), ("time", "time")):
            value = payload.get(field)
            if value is not None:
                user[key] = value
        if seq is not None:
            user["seq"] = seq
        note = f"seq {seq or '?'}: UI request — {event}"
        if label and label != event:
            note += f" ({label})"
        origin = "/".join(str(source.get(key)) for key in ("screen", "control", "gesture")
                          if source.get(key))
        if origin:
            note += f" ({origin})"
        steps.append({"id": _step_id(len(steps) + 1), "at": _iso(at),
                      "user": user, "note": note})

    # Seed the state that existed before the window. The base map may be a
    # session or plan snapshot from before the first event; these rows make the
    # UI start from the same room state the journal had at --from.
    prior_states = {}
    prior_sensors = {}
    start_ms = int(start.timestamp() * 1000)
    for event, stamp in dated:
        if int(event.get("tsMs") or stamp.timestamp() * 1000) >= start_ms:
            continue
        data = event.get("data") or {}
        if event.get("type") == "room.state" and data.get("room"):
            prior_states[data["room"]] = (data, event.get("seq"))
        elif event.get("type") == "sensor.reading" and data.get("room") and data.get("temp") is not None:
            prior_sensors[data["room"]] = (data, event.get("seq"))
    for room, (data, seq) in prior_states.items():
        identity, state = _state_fields(data)
        add_controller(room, start, identity=identity, state=state,
                       note=f"baseline from seq {seq or '?'}")
    for room, (data, seq) in prior_sensors.items():
        identity = {"temperature": data.get("temp")}
        if data.get("humidity") is not None:
            identity["humidity"] = data["humidity"]
        if data.get("battery") is not None:
            identity["battery"] = data["battery"]
        if data.get("sourceTsMs") or data.get("tsMs"):
            identity["timestamp"] = data.get("sourceTsMs") or data.get("tsMs")
        add_controller(room, start, identity=identity,
                       note=f"baseline reading from seq {seq or '?'}")

    baseline_steps = len(steps)
    last_state = {room: dict(data) for room, (data, _seq) in prior_states.items()}
    last_sensor = {room: dict(data) for room, (data, _seq) in prior_sensors.items()}
    warnings = []
    window_events = 0
    request_count = 0
    snapshot_after_start = False
    profile_changed = False

    for event, stamp in dated:
        if stamp < start or stamp > end:
            continue
        window_events += 1
        data = event.get("data") or {}
        kind = event.get("type")
        room = data.get("room")
        if kind == "sensor.reading" and room:
            previous = last_sensor.get(room, {})
            changed = any(data.get(key) != previous.get(key)
                          for key in ("temp", "humidity", "battery"))
            if not changed and not args.all_sensors:
                last_sensor[room] = data
                continue
            identity = {"temperature": data.get("temp")}
            if data.get("humidity") is not None:
                identity["humidity"] = data["humidity"]
            if data.get("battery") is not None:
                identity["battery"] = data["battery"]
            identity["timestamp"] = data.get("sourceTsMs") or data.get("tsMs")
            add_controller(room, stamp, identity=identity,
                           note=f"seq {event.get('seq')}: {data.get('sensor') or 'sensor'} reading")
            value = _format_temp(data.get("temp"))
            if value is not None and _visible(base, room):
                add_expect(stamp, f"room.{reverse_alias[room]}.temp", contains=value)
            elif room == "Outside" and value is not None:
                add_expect(stamp, "summary.outside", contains=value)
            last_sensor[room] = data
        elif kind == "room.state" and room:
            previous = last_state.get(room, {})
            identity, state = _state_fields(data)
            changed_identity = {key: value for key, value in identity.items()
                                if previous.get(key) != value}
            changed_state = {key: value for key, value in state.items()
                             if previous.get(key) != value}
            if not args.include_status_text:
                changed_identity.pop("statusMessage", None)
                changed_identity.pop("relayMessage", None)
            if not changed_identity and not changed_state:
                last_state[room] = data
                continue
            add_controller(room, stamp,
                           identity=changed_identity or None,
                           state=changed_state or None,
                           note=f"seq {event.get('seq')}: room state")
            if _visible(base, room):
                if "advance" in changed_state and data.get("status") not in ("warn", "fail"):
                    if changed_state.get("advance") == "A":
                        add_expect(stamp, f"room.{reverse_alias[room]}.subline",
                                   contains="(A)")
                    else:
                        add_expect(stamp, f"room.{reverse_alias[room]}.subline",
                                   notContains="(A)")
            last_state[room] = data
        elif kind == "ui.request":
            request_count += 1
            payload = data.get("payload") or {}
            source = data.get("source") or payload.get("Source") or {}
            action = payload.get("Action") or data.get("action") or "UI request"
            request_room = data.get("room") or source.get("room") or payload.get("Room")
            request_label = None
            if action == "Update Profiles":
                change = _schedule_change(payload.get("profiles"), schedule_profiles, request_room)
                if change:
                    prefix = "Schedule saved" if (source.get("screen") or "") == "schedule" else "Calendar saved"
                    request_label = f"{prefix} — {change}"
                if payload.get("profiles"):
                    schedule_profiles = copy.deepcopy(payload["profiles"])
            add_user(request_room, stamp, action, source, payload, event.get("seq"),
                     label=request_label)
        elif kind == "plan.snapshot" and stamp > start:
            snapshot_after_start = True
        elif kind == "profile.change":
            profile = data.get("toName") or data.get("to") or profile
            profile_changed = True

    if snapshot_after_start:
        warnings.append("a plan snapshot after the window start was not replayed; structural edits need a base map at that point")
    if request_count:
        warnings.append(f"{request_count} UI request(s) are shown as user steps but not replayed as taps; their controller effects are included")
    if profile_changed:
        warnings.append("a profile change was not replayed as an active-profile change; narrow the window or add a profile step")
    if window_events == 0:
        raise SystemExit(
            f"journal_to_scenario.py: no journal events between {start:%H:%M:%S} and {end:%H:%M:%S} "
            f"on {day}; the journal covers {first:%H:%M:%S} to {last:%H:%M:%S}. "
            "Check that the controller is still writing its journal, then retry.")
    if len(steps) == baseline_steps:
        raise SystemExit(
            f"journal_to_scenario.py: {window_events} journal event(s) in the window produced no convertible changes; "
            "the scenario would contain only the pre-window baseline. Widen the window or use --all-sensors.")
    if not steps:
        raise SystemExit("journal_to_scenario.py: no convertible events in the window")
    if len(steps) > args.max_steps:
        raise SystemExit(
            f"journal_to_scenario.py: {len(steps)} steps exceed --max-steps {args.max_steps}; "
            "narrow --from/--to or raise the limit")

    name = args.name or f"Journal {day.isoformat()} {start:%H:%M}-{end:%H:%M}"
    description = (
        f"Generated from {bundle.manifest.get('source') or 'the controller event journal'} "
        f"for {day.isoformat()} {start:%H:%M}-{end:%H:%M}. "
        f"{len(steps)} steps from {len(events)} journal events."
    )
    if warnings:
        description += " " + " ".join(warnings)
    return {
        "schemaVersion": 1,
        "id": f"journal-{day.isoformat()}-{start:%H%M}-{end:%H%M}",
        "name": name,
        "description": description,
        "tags": ["journal", "generated"],
        "clock": {"start": _iso(start), "timeZone": args.timezone},
        "home": {"map": base, "profile": profile if profile is not None else base.get("profile", 0)},
        "rooms": aliases,
        "defaults": {"stepTimeoutMs": 5000, "screenshots": "failure", "refreshReply": "empty"},
        "steps": steps,
    }


def load_input(args):
    if bool(args.bundle) == bool(args.journal):
        raise SystemExit("journal_to_scenario.py: give exactly one of --bundle or --journal")
    if args.bundle:
        return journal_bundle.open_bundle(pathlib.Path(args.bundle).expanduser())
    path = pathlib.Path(args.journal).expanduser()
    maps = pathlib.Path(args.maps).expanduser() if args.maps else path.parent.parent.parent / "maps"
    manifest = {}
    if path.parent.parent.parent.name:
        manifest = {"day": path.stem, "source": f"file:{path}"}
    return journal_bundle.Bundle(root=path.parent, events_path=path, maps_dir=maps, manifest=manifest)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="journal_to_scenario.py",
        description="Turn a controller journal day into an RBR Studio scenario")
    parser.add_argument("--bundle", help="bundle directory or .tar.gz from journal_import.py")
    parser.add_argument("--journal", help="raw daily JSONL file")
    parser.add_argument("--maps", help="maps directory for --journal (default: <root>/maps)")
    parser.add_argument("--map", help="explicit base map JSON, overriding the journal snapshot")
    parser.add_argument("--from", dest="start", help="window start: HH:MM, HH:MM:SS or ISO")
    parser.add_argument("--to", dest="end", help="window end: HH:MM, HH:MM:SS or ISO")
    parser.add_argument("--timezone", default="Europe/London", help="scenario timezone (default: Europe/London)")
    parser.add_argument("--profile", help="override the active profile")
    parser.add_argument("--name", help="scenario name")
    parser.add_argument("--out", required=True, help="scenario JSON to write")
    parser.add_argument("--max-steps", type=int, default=5000, help="refuse a scenario larger than this (default: 5000)")
    parser.add_argument("--all-sensors", action="store_true", help="keep repeated sensor readings with unchanged values")
    parser.add_argument("--include-status-text", action="store_true", help="emit statusMessage/relayMessage-only changes")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    bundle = load_input(args)
    try:
        if not bundle.events_path or not bundle.events_path.is_file():
            raise SystemExit("journal_to_scenario.py: no events file in the bundle")
        events = journal_bundle.read_events(bundle.events_path)
        scenario = build_scenario(args, bundle, events)
        out = pathlib.Path(args.out).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(scenario, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {out}: {len(scenario['steps'])} steps, {scenario['clock']['start']} to {scenario['clock'].get('timeZone')}")
        return 0
    finally:
        bundle.close()


if __name__ == "__main__":
    sys.exit(main())
