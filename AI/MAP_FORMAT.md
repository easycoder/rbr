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
│       ├── relayType   — "Shelly One" | "RBR-Now" etc.
│       └── linked      — "yes" | "no"
└── calendar (optional) — maps day names to profile names
```

### Edit rules
- Keep MAC addresses and relay identifiers exactly as found
- `events` must be ordered by `until` time, earliest first
- `mode` values are strictly: `timed`, `boost`, `advance`, `on`, `off`
- Temperature values in `events[].temp` are strings (e.g. `"21.0"`), `target` is a number
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
