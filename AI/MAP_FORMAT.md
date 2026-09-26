# Map File Format

The RBR system is described by two JSON configuration files.

## `map.json` — Room and profile configuration

This is the primary configuration file that drives the controller's behaviour.

```
map.json
├── profiles[]          — named profiles (e.g. "Monday-Friday", "Weekend")
│   └── rooms[]         — one entry per room
│       ├── name        — room label
│       ├── sensor      — BLE/Zigbee thermometer MAC address
│       ├── relays[]    — relay identifiers
│       ├── mode        — timed | boost | advance | on | off
│       ├── target      — fallback target temperature (°C)
│       ├── events[]    — timed schedule: [{until: "HH:MM", temp: "N.N"}, ...]
│       ├── periods[]   — current timed schedule: [{on: "HH:MM", off: "HH:MM", temp: "N.N", enabled: true|false}, ...]
│       ├── relayType   — "Shelly One" | "RBR-Now" etc.
│       └── linked      — "yes" | "no"
├── overrides (optional) — one-off schedule tweaks, keyed by room name
└── calendar (optional)  — maps day names to profile names
```

### `overrides` — one-off schedule tweaks

A room's `overrides` entry is a single one-day change to its schedule, written by the controller when a UI sends a `Room Override` request (the PWA's Special actions). It sits **outside `profiles`** deliberately, on two counts: it must apply whichever profile the calendar picks for the target day, and it must survive `Update Profiles`/`Update Rooms`, which replace the whole `profiles` array.

```json
"overrides": {
    "Kitchen": { "kind": "start", "date": "2026-09-23", "on": "08:30", "was": "06:30", "at": 1787353201098 }
}
```

- `kind` is `start` (heating begins at `on` instead of the scheduled time) or `skip` (that morning's period is dropped entirely).
- `date` is the calendar day the change applies to, resolved when the request was made: today if the room's first period had not yet begun, otherwise tomorrow.
- `on` is the requested start time (absent for a `skip`).
- `was` records the period's scheduled start at the time of the request, for display.
- `at` is the arm timestamp.

The controller applies the override when it reads the schedule: a `start` at or after that period's own `off` is treated as a `skip`. The stored `periods` are never modified, so the schedule reverts by itself once the date passes; the entry is pruned at the midnight roll-over.

### `periods[].enabled` — switching a period off

Each period carries an optional boolean `enabled`. A period whose flag is `false` is ignored everywhere the schedule is read: it never becomes the current period, contributes no heat, is skipped by the advance projection and cannot be the morning target of a one-off override.

An **absent flag means enabled**, so existing maps (and any period written by hand) keep working unchanged and there is no need to rewrite the whole file. The UI adds the flag to every period when a schedule is saved, so once a room's schedule has been edited its periods carry an explicit `true`/`false`.

### Edit rules
- Keep MAC addresses and relay identifiers exactly as found
- `events` must be ordered by `until` time, earliest first
- `mode` values are strictly: `timed`, `boost`, `advance`, `on`, `off`
- Temperature values in `events[].temp` are strings (e.g. `"21.0"`), `target` is a number
- `periods[].enabled` is a boolean; omit it to mean enabled, or set `false` to switch a period off
- Do not remove runtime fields (`relay`, `advance`, `boost`, `status`, `timestamp`, etc.) — the controller writes these
- `map.json` and `resources/as/map.json` may both need updating if both UI trees are active

### After editing
Validate JSON:
```bash
python3 -m json.tool map.json > /dev/null && echo OK
```
The controller picks up changes on its next 60-second cron cycle.

## `devices.json` — Room-to-relay mapping

Maps room names to their relay hardware identifiers.

## `config.json` — RBR-Now hardware configuration

Describes each RBR-Now device: role (master/slave), SSID, channel, and pin mappings for LED and relay (including invert flags).
