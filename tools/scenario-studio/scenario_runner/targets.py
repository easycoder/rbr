"""Semantic target catalogue for the RBR page.

A scenario names `room.Office.advance`, never `#room-2-advance-btn`. Names are
resolved against the map the run is using, so reordering rooms cannot silently
point a scenario at another room. `css:` is the explicit escape hatch.
"""

from .errors import ScenarioError

ROOM_ELEMENTS = {
    "card": "card",
    "name": "name",
    "temp": "temp",
    "subline": "subline",
    "rest": "rest",
    "info": "info-btn",
    "expansion": "expansion",
    "heating-tag": "heating-tag",
    "warn": "warn-text",
    "warn-row": "warn-row",
    "advance": "advance-btn",
    "schedule": "edit-schedule",
    "special": "special-btn",
    "override": "override-row",
    "setpoint": "setpoint",
    "mode.timed": "mode-timed",
    "mode.boost": "mode-boost",
    "mode.on": "mode-on",
    "mode.off": "mode-off",
    "target": "target-value",
    "target.plus": "target-plus",
    "target.minus": "target-minus",
    "boost.30": "boost-30",
    "boost.1h": "boost-1h",
    "boost.2h": "boost-2h",
    "boost.off": "boost-off",
}

SUMMARY = {
    "title": "summary-title",
    "subtitle": "summary-subtitle",
    "outside": "summary-outside",
    "profile": "summary-profile-name",
    "pill": "summary-profile-pill",
    "chip": "summary-chip",
    "today": "summary-today",
}

SCHEETS = {
    "root": "sheet-root",
    "title": "sheet-title",
    "close": "sheet-close-btn",
}

MENU = {
    "system": "menu-row-system",
    "devices": "menu-row-devices",
    "outside": "menu-row-outside",
    "backups": "menu-row-backups",
}


def visible_rooms(base_map):
    """The room rows the page renders: the outdoor sensor entry is not a card."""
    out = []
    for room in base_map.get("rooms", []):
        if room.get("name") == "Outside" and not room.get("relays"):
            continue
        out.append(room)
    return out


def room_index(base_map, name):
    for i, room in enumerate(visible_rooms(base_map)):
        if room.get("name") == name:
            return i
    known = ", ".join(room.get("name", "?") for room in visible_rooms(base_map))
    raise ScenarioError(f"no room named {name!r} in the base map (rooms: {known})")


def identity_index(base_map, name):
    for i, room in enumerate(base_map.get("rooms", [])):
        if room.get("name") == name:
            return i
    known = ", ".join(room.get("name", "?") for room in base_map.get("rooms", []))
    raise ScenarioError(f"no room named {name!r} in the map's identity list (rooms: {known})")


def profile_index(base_map, name):
    for i, profile in enumerate(base_map.get("profiles", [])):
        if profile.get("name") == name:
            return i
    known = ", ".join(profile.get("name", "?") for profile in base_map.get("profiles", []))
    raise ScenarioError(f"no profile named {name!r} in the base map (profiles: {known})")


def resolve(target, base_map, aliases):
    """Return a CSS selector for a semantic target."""
    if target.startswith("css:"):
        return target[4:]

    parts = target.split(".")
    if not parts or not parts[0]:
        raise ScenarioError(f"empty target {target!r}")

    head = parts[0]

    if head == "css":
        raise ScenarioError("use 'css:<selector>' for a raw selector")

    if head == "summary":
        if len(parts) != 2 or parts[1] not in SUMMARY:
            raise ScenarioError(f"unknown summary target {target!r} (known: {', '.join(SUMMARY)})")
        return "#" + SUMMARY[parts[1]]

    if head == "sheet":
        if len(parts) != 2 or parts[1] not in SCHEETS:
            raise ScenarioError(f"unknown sheet target {target!r} (known: {', '.join(SCHEETS)})")
        return "#" + SCHEETS[parts[1]]

    if head == "menu":
        if len(parts) != 2 or parts[1] not in MENU:
            raise ScenarioError(f"unknown menu target {target!r} (known: {', '.join(MENU)})")
        return "#" + MENU[parts[1]]

    if head == "boot":
        if len(parts) == 2 and parts[1] == "warning":
            return "#app"
        raise ScenarioError("unknown boot target; use boot.warning")

    if head == "room":
        if len(parts) < 3:
            raise ScenarioError(f"room target {target!r} needs room.<name>.<element>")
        name = parts[1]
        name = aliases.get(name, name)
        element = ".".join(parts[2:])
        if element not in ROOM_ELEMENTS:
            raise ScenarioError(
                f"unknown room element {element!r} in {target!r} "
                f"(known: {', '.join(sorted(ROOM_ELEMENTS))})")
        return f"#room-{room_index(base_map, name)}-{ROOM_ELEMENTS[element]}"

    if head == "schedule":
        if len(parts) == 2:
            fixed = {
                "save": "schedule-save-btn",
                "cancel": "schedule-cancel-btn",
                "add": "schedule-add-btn",
                "profile": "schedule-profile-pill",
                "sheet": "schedule-editor-sheet",
            }
            if parts[1] not in fixed:
                raise ScenarioError(f"unknown schedule target {target!r}")
            return "#" + fixed[parts[1]]
        if len(parts) == 4 and parts[1] == "period":
            fields = {
                "start": "start-select",
                "stop": "off-select",
                "temp": "temp-value",
                "enabled": "enable",
                "delete": "delete",
            }
            if parts[3] not in fields:
                raise ScenarioError(f"unknown schedule period field {parts[3]!r}")
            return f"#schedule-period-{parts[2]}-{fields[parts[3]]}"
        raise ScenarioError(f"unknown schedule target {target!r}")

    if head == "profiles":
        if len(parts) == 2:
            fixed = {
                "save": "profile-save-btn",
                "cancel": "profile-cancel-btn",
                "add": "profile-add-btn",
                "sheet": "profile-sheet",
            }
            if parts[1] not in fixed:
                raise ScenarioError(f"unknown profiles target {target!r}")
            return "#" + fixed[parts[1]]
        if len(parts) >= 4 and parts[1] == "row":
            name = ".".join(parts[2:-1])
            field = parts[-1]
            fields = {"label": "label", "rename": "rename", "delete": "delete", "body": "body"}
            if field not in fields:
                raise ScenarioError(f"unknown profile row field {field!r}")
            return f"#profile-row-{profile_index(base_map, name)}-{fields[field]}"
        raise ScenarioError(f"unknown profiles target {target!r}")

    if head == "devices":
        if len(parts) == 2:
            fixed = {
                "save": "device-editor-save-btn",
                "cancel": "device-editor-cancel-btn",
                "add": "device-editor-add-room",
                "sheet": "device-editor-sheet",
                "room-pill": "device-editor-room-pill",
            }
            if parts[1] not in fixed:
                raise ScenarioError(f"unknown devices target {target!r}")
            return "#" + fixed[parts[1]]
        if len(parts) >= 4 and parts[1] == "room":
            name = ".".join(parts[2:-1])
            field = parts[-1]
            fields = {
                "name": "name",
                "edit": "edit",
                "delete": "delete",
                "up": "up",
                "down": "down",
            }
            if field not in fields:
                raise ScenarioError(f"unknown device room field {field!r}")
            return f"#device-room-edit-{identity_index(base_map, name)}-{fields[field]}"
        raise ScenarioError(f"unknown devices target {target!r}")

    raise ScenarioError(
        f"unknown target {target!r}; expected summary.*, room.<name>.*, sheet.*, "
        f"schedule.*, profiles.*, devices.*, menu.*, boot.warning or css:<selector>")
