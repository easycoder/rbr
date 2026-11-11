"""Load and validate a scenario before any browser is started."""

import json
from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import targets
from .errors import ScenarioError

ALLOWED_STEP_ACTIONS = ("controller", "user", "ui", "expect", "expectWire", "waitFor", "connection", "delay")
DEFAULT_STEP_TIMEOUT_MS = 5000


@dataclass
class Prepared:
    path: Path
    scenario: dict
    base_dir: Path
    base_map: dict
    start: datetime
    zone: ZoneInfo
    aliases: dict
    profile_idx: int
    step_times: list
    defaults: dict = field(default_factory=dict)
    continue_on_failure: bool = False

    def step_timeout_ms(self, step):
        return int(step.get("timeoutMs") or self.defaults.get("stepTimeoutMs") or DEFAULT_STEP_TIMEOUT_MS)

    def when(self, at):
        """Resolve a step's `at` against the scenario's date and timezone."""
        if isinstance(at, datetime):
            return at
        if isinstance(at, str) and ":" in at and "-" not in at and "T" not in at:
            clock = time.fromisoformat(at)
            return datetime.combine(self.start.date(), clock, tzinfo=self.zone)
        value = datetime.fromisoformat(at.replace("Z", "+00:00"))
        if value.tzinfo is None:
            value = value.replace(tzinfo=self.zone)
        return value.astimezone(self.zone)


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        raise ScenarioError(f"file not found: {path}")
    except json.JSONDecodeError as exc:
        raise ScenarioError(f"{path}: invalid JSON: {exc}")


def _zone(name):
    if not name:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        raise ScenarioError(f"unknown time zone {name!r}")


def _load_map(home, base_dir):
    source = home.get("map")
    if isinstance(source, dict):
        return json.loads(json.dumps(source))
    if not isinstance(source, str) or not source:
        raise ScenarioError("home.map must be a path or an inline map")
    path = (base_dir / source).resolve()
    if not path.exists():
        raise ScenarioError(f"home.map does not exist: {path}")
    return _load_json(path)


def _validate_map(base_map):
    issues = []
    if not isinstance(base_map.get("rooms"), list) or not base_map["rooms"]:
        issues.append("the base map has no rooms[]")
    if not isinstance(base_map.get("profiles"), list) or not base_map["profiles"]:
        issues.append("the base map has no profiles[]")
    for i, room in enumerate(base_map.get("rooms", []) or []):
        if not isinstance(room, dict) or not room.get("name"):
            issues.append(f"rooms[{i}] has no name")
    for i, profile in enumerate(base_map.get("profiles", []) or []):
        if not isinstance(profile, dict) or not profile.get("name"):
            issues.append(f"profiles[{i}] has no name")
    return issues


def _validate_step(step, index, prepared, ids, issues):
    where = f"steps[{index}]"
    if not isinstance(step, dict):
        issues.append(f"{where}: not an object")
        return
    step_id = step.get("id")
    if not isinstance(step_id, str) or not step_id:
        issues.append(f"{where}: id is required")
    elif step_id in ids:
        issues.append(f"{where}: duplicate id {step_id!r}")
    else:
        ids.add(step_id)

    if not step.get("at"):
        issues.append(f"{where}: at is required")
    else:
        try:
            prepared.when(step["at"])
        except Exception as exc:
            issues.append(f"{where}: bad at {step['at']!r}: {exc}")

    actions = [key for key in ALLOWED_STEP_ACTIONS if key in step]
    if len(actions) != 1:
        issues.append(f"{where}: exactly one of {', '.join(ALLOWED_STEP_ACTIONS)} is required (got {actions or 'none'})")
        return
    if "marker" in step and not isinstance(step["marker"], bool):
        issues.append(f"{where}.marker: true or false is required")
    action = actions[0]

    def check_target(value, label):
        if not isinstance(value, str) or not value:
            issues.append(f"{where}.{label}: target is required")
            return
        try:
            targets.resolve(value, prepared.base_map, prepared.aliases)
        except ScenarioError as exc:
            issues.append(f"{where}.{label}: {exc}")

    if action == "controller":
        controller = step["controller"]
        if not isinstance(controller, dict):
            issues.append(f"{where}.controller: not an object")
            return
        unknown = set(controller) - {"room", "set", "state", "raw", "push", "adopt"}
        if unknown:
            issues.append(f"{where}.controller: unknown fields {sorted(unknown)}")
        has = [key for key in ("set", "state", "raw") if key in controller]
        if not has:
            issues.append(f"{where}.controller: needs set, state or raw")
        room = controller.get("room")
        if ("set" in controller or "state" in controller) and not room:
            issues.append(f"{where}.controller: room is required with set/state")
        if "set" in controller:
            if not isinstance(controller["set"], dict):
                issues.append(f"{where}.controller.set: not an object")
            elif room:
                try:
                    targets.identity_index(prepared.base_map, prepared.aliases.get(room, room))
                except ScenarioError as exc:
                    issues.append(f"{where}.controller.set: {exc}")
        if "state" in controller:
            state = controller["state"]
            if not isinstance(state, dict):
                issues.append(f"{where}.controller.state: not an object")
            else:
                if not isinstance(state.get("set"), dict):
                    issues.append(f"{where}.controller.state.set: an object is required")
                if state.get("profile") is not None:
                    if isinstance(state["profile"], int):
                        if not 0 <= state["profile"] < len(prepared.base_map.get("profiles", [])):
                            issues.append(f"{where}.controller.state.profile: index {state['profile']} is out of range")
                    else:
                        try:
                            targets.profile_index(prepared.base_map, state["profile"])
                        except ScenarioError as exc:
                            issues.append(f"{where}.controller.state.profile: {exc}")
                if room:
                    try:
                        targets.identity_index(prepared.base_map, prepared.aliases.get(room, room))
                    except ScenarioError:
                        pass
        if "raw" in controller:
            if not isinstance(controller["raw"], str):
                issues.append(f"{where}.controller.raw: a string is required")
            if "set" in controller or "state" in controller:
                issues.append(f"{where}.controller: raw cannot be combined with set or state")
        if "adopt" in controller and not isinstance(controller["adopt"], bool):
            issues.append(f"{where}.controller.adopt: true or false")
        if controller.get("adopt") and "raw" not in controller:
            issues.append(f"{where}.controller.adopt: raw is required")
        if "push" in controller and not isinstance(controller["push"], bool):
            issues.append(f"{where}.controller.push: true or false")

    elif action == "user":
        user = step["user"]
        if not isinstance(user, dict):
            issues.append(f"{where}.user: not an object")
            return
        if not isinstance(user.get("action"), str) or not user["action"]:
            issues.append(f"{where}.user.action: a string is required")
        if user.get("room") is not None and not isinstance(user["room"], str):
            issues.append(f"{where}.user.room: a string is required")

    elif action == "ui":
        ui = step["ui"]
        if not isinstance(ui, dict):
            issues.append(f"{where}.ui: not an object")
            return
        keys = [key for key in ("tap", "select", "fill", "scroll") if key in ui]
        if len(keys) != 1:
            issues.append(f"{where}.ui: exactly one of tap, select, fill, scroll is required")
            return
        if keys[0] == "tap":
            check_target(ui["tap"], "ui.tap")
        elif keys[0] == "scroll":
            check_target(ui["scroll"].get("target"), "ui.scroll.target")
        else:
            check_target(ui[keys[0]].get("target"), f"ui.{keys[0]}.target")
            if not isinstance(ui[keys[0]].get("value"), str):
                issues.append(f"{where}.ui.{keys[0]}.value: a string is required")

    elif action == "expect":
        expect = step["expect"]
        if not isinstance(expect, dict):
            issues.append(f"{where}.expect: not an object")
            return
        check_target(expect.get("target"), "expect.target")
        predicates = [key for key in ("text", "contains", "notContains", "visible", "hidden", "value", "count", "geometry") if key in expect]
        if not predicates:
            issues.append(f"{where}.expect: needs one of text, contains, notContains, visible, hidden, value, count")
        if "geometry" in expect:
            issues.append(f"{where}.expect.geometry: not supported by this runner version")

    elif action == "expectWire":
        wire = step["expectWire"]
        if not isinstance(wire, dict):
            issues.append(f"{where}.expectWire: not an object")
            return
        if not isinstance(wire.get("request"), str) or not wire["request"]:
            issues.append(f"{where}.expectWire.request: a string is required")
        if "match" in wire and not isinstance(wire["match"], dict):
            issues.append(f"{where}.expectWire.match: an object is required")

    elif action == "waitFor":
        wait = step["waitFor"]
        if not isinstance(wait, dict):
            issues.append(f"{where}.waitFor: not an object")
            return
        check_target(wait.get("target"), "waitFor.target")
        if wait.get("state") not in ("attached", "visible", "hidden", "detached"):
            issues.append(f"{where}.waitFor.state: attached, visible, hidden or detached")

    elif action == "connection":
        connection = step["connection"]
        if not isinstance(connection, dict):
            issues.append(f"{where}.connection: not an object")
            return
        if connection.get("action") not in ("drop", "reconnect", "error"):
            issues.append(f"{where}.connection.action: drop, reconnect or error")

    elif action == "delay":
        value = step["delay"]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            issues.append(f"{where}.delay: a number of real seconds is required")
        elif value < 0:
            issues.append(f"{where}.delay: must be zero or more")


def prepare(path, repo=None):
    """Load, validate and prepare a scenario; raises ScenarioError with all issues."""
    path = Path(path).resolve()
    scenario = _load_json(path)
    if not isinstance(scenario, dict):
        raise ScenarioError("the scenario must be a JSON object")

    issues = []
    if scenario.get("schemaVersion") != 1:
        issues.append("schemaVersion must be 1")
    if not scenario.get("name"):
        issues.append("name is required")
    clock = scenario.get("clock") or {}
    if not isinstance(clock, dict) or not clock.get("start"):
        issues.append("clock.start is required")
        raise ScenarioError("\n".join(issues))
    zone = _zone(clock.get("timeZone"))
    try:
        start = datetime.fromisoformat(str(clock["start"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ScenarioError(f"clock.start is not a date-time: {exc}")
    if start.tzinfo is None:
        start = start.replace(tzinfo=zone)
    start = start.astimezone(zone)

    home = scenario.get("home") or {}
    if not isinstance(home, dict):
        raise ScenarioError("home must be an object")
    base_map = _load_map(home, path.parent)
    issues.extend(_validate_map(base_map))

    aliases = scenario.get("rooms") or {}
    if not isinstance(aliases, dict):
        issues.append("rooms must be an object of aliases")
        aliases = {}
    for alias, name in aliases.items():
        try:
            targets.identity_index(base_map, name)
        except ScenarioError as exc:
            issues.append(f"rooms.{alias}: {exc}")

    profile_idx = 0
    profile_name = home.get("profile")
    if isinstance(profile_name, int):
        profile_idx = profile_name
    elif isinstance(profile_name, str) and profile_name:
        try:
            profile_idx = targets.profile_index(base_map, profile_name)
        except ScenarioError as exc:
            issues.append(f"home.profile: {exc}")
    elif profile_name is not None:
        issues.append("home.profile must be a name or an index")
    if 0 <= profile_idx < len(base_map.get("profiles", [])):
        base_map["profile"] = profile_idx
    else:
        issues.append(f"home.profile index {profile_idx} is out of range")
    if home.get("calendar") in ("on", "off"):
        base_map["calendar"] = home["calendar"]

    defaults = scenario.get("defaults") or {}
    if not isinstance(defaults, dict):
        issues.append("defaults must be an object")
        defaults = {}

    prepared = Prepared(
        path=path,
        scenario=scenario,
        base_dir=path.parent,
        base_map=base_map,
        start=start,
        zone=zone,
        aliases=aliases,
        profile_idx=profile_idx,
        step_times=[],
        defaults=defaults,
        continue_on_failure=bool(defaults.get("continueOnFailure")),
    )

    steps = scenario.get("steps")
    if not isinstance(steps, list) or not steps:
        issues.append("steps must be a non-empty array")
        steps = []

    ids = set()
    previous = None
    markers = []
    allow_out_of_order = bool(scenario.get("allowOutOfOrder"))
    for index, step in enumerate(steps):
        _validate_step(step, index, prepared, ids, issues)
        if isinstance(step, dict) and step.get("marker"):
            markers.append(index)
        if isinstance(step, dict) and step.get("at"):
            try:
                when = prepared.when(step["at"])
            except Exception:
                prepared.step_times.append(None)
                continue
            prepared.step_times.append(when)
            if previous is not None and when < previous and not allow_out_of_order:
                issues.append(
                    f"steps[{index}] ({step.get('id', '?')}): at {step['at']} goes backwards "
                    f"(set allowOutOfOrder if that is intended)")
            previous = when
        else:
            prepared.step_times.append(None)

    if issues:
        raise ScenarioError("\n".join(issues))
    if len(markers) > 1:
        raise ScenarioError("only one step may carry the marker")
    return prepared
