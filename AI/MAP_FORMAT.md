# Map File Format

The RBR system is described by two JSON configuration files.

## `map.json` — Room and profile configuration

This is the primary configuration file that drives the controller's behaviour.

```
map.json
├── name                — system name
├── request             — demand-relay name
├── profile             — index of the selected profile
├── calendar, calendar-data
├── rooms[]             — the shared room list: identity, once for the system
│   ├── name            — room label, and the key that joins it to every profile
│   ├── relays[]        — relay identifiers (empty for a TRV room)
│   ├── sensor          — BLE/Zigbee thermometer MAC address
│   ├── trv             — optional self-contained valve friendly name; the room has no relays
│   ├── linked          — "yes" | "no": relay driven by target/temperature, or directly by mode
│   ├── relayfails[]    — per-relay failure counts, parallel to relays
│   ├── protect, ptemp  — frost protection, and its trigger temperature
│   └── temperature, humidity, battery, sensorAge, timestamp, status, statusMessage,
│       relayMessage, relaysFailed, relaysTotal, relay   — the readings and what is derived from them
├── profiles[]          — named plans (e.g. "Monday-Friday", "Weekend")
│   └── rooms{}         — per-room schedule state, keyed by room name
│       ├── mode        — timed | boost | advance | on | off
│       ├── target      — fallback target temperature (°C)
│       ├── events[]    — timed schedule: [{until: "HH:MM", temp: "N.N"}, ...]
│       ├── periods[]   — current timed schedule: [{on: "HH:MM", off: "HH:MM", temp: "N.N", enabled: true|false}, ...]
│       ├── advance, period, prevmode, until, boostperiod — scheduling state the controller maintains
│       └── (no identity fields: those live in `rooms`)
├── overrides (optional) — one-off schedule tweaks, keyed by room name
└── calendar (optional)  — maps day names to profile names
```

### Rooms above profiles, joined by name

There is **one room list for the system**. A room's identity — which relays it has, which thermometer serves it, whether the relay is driven by target or by mode, whether it is frost-protected, and its readings — is a property of the installation, so it is stored once in `rooms[]`. A profile holds only what it is asked to do: `profiles[].rooms["Kitchen"]` is that room's schedule state under that plan.

The join is the room **name**. It used to be an array index, which meant that two profiles with differently ordered room lists silently wrote into each other's rooms; by name that cannot happen. Two consequences worth knowing:

- **Room names must be unique**, because a name is now a key in every profile. The Devices sheet refuses a duplicate name and gives a new room a numbered default ("Unnamed", "Unnamed 2").
- **A room with no state in a profile** is still part of the system's room set: the UI lists it as Off with no schedule, and the controller does not control it under that profile. The UI writes state for every room when it saves, so this is a transient state rather than a permanent one.

The controller merges the two halves into one flat record per room for its processing cycle, and splits them again before writing the map or sending it to a UI. Every routine in between sees exactly what it saw before the split.

### What a UI sends

An `Update Profiles` request carries both halves — `rooms[]` (identity) and `profiles[]` (schedule state) — plus the selected `profile` and the calendar fields. The controller takes only the seven identity fields a UI owns (`relays`, `sensor`, `trv`, `linked`, `relayfails`, `protect`, `ptemp`) from `rooms`, keeping its own readings and derived status for every room it already knew: a page is reporting state from a few seconds ago, and its temperatures must not win. Names absent from the incoming list are deleted; names not seen before are added.

A room with a `trv` has no relays. The controller commands the valve's `system_mode` (`heat`/`off`) and `occupied_heating_setpoint` instead of switching a relay; a setpoint changed on the valve's own dial is written back into the current period's `temp` so the schedule and the interface show it.

`Update Rooms` replaces the identity list on its own, for a client that edits wiring without touching schedules.

`profiles[].rooms` must be an object keyed by room name. A list means the sender is a UI that predates the split, and the controller **rejects the request and leaves the running map alone** rather than emptying the room set and stopping the heating. The log says so.

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
- A room appears once in `rooms[]`, and every profile carries a state entry under that exact name
- Readings and derived status belong in `rooms[]`, never inside a profile — and a file written by the controller will not have them at all: `PrepareMapForDisk` strips them and they are re-derived within a cycle of a restart, so a hand-written map may leave them out
- An existing map in the older shape (rooms inside each profile) is converted by the controller when it loads, and the converted shape is what gets written back on the next save — no migration tool is needed

### After editing
Validate JSON:
```bash
python3 -m json.tool map.json > /dev/null && echo OK
```
The controller picks up changes on its next 60-second cron cycle.
