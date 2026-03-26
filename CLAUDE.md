# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Summary

Room By Room (RBR) is an open-source smart central heating control system. It has three components:

1. **Controller** — Python/EasyCoder scripts running on an Orange Pi Zero 2 that manage heating per-room via BLE thermometers and WiFi-connected relay devices (RBR-Now ESP32 modules)
2. **UI** — A browser-based mobile webapp written in JavaScript EasyCoder with Webson-rendered DOM, served from `index.html`
3. **REST server** — PHP on shared hosting (not in this repo)

Communication between controller and UI is via MQTT (broker: `rbrheating.duckdns.org`).

## Key Technologies

- **EasyCoder**: A high-level scripting language with both Python and JavaScript dialects. Scripts use the `.ecs` extension. The Python runtime lives in a separate repo at `~/dev/easycoder/easycoder-py` (set via `EASYCODER_SRC` env var). The JS runtime modules are in `easycoder/`.
- **Webson**: JSON-based DOM rendering. Layout definitions are in `resources/webson/*.json`. Element IDs in Webson must stay in sync with `.ecs` scripts that attach to them.
- **MQTT**: Used for all controller-UI communication. Broker is `rbrheating.duckdns.org` (port 8883 for Python/controller, port 443 for JS/UI websocket). Auth: username `rbr`, password from `~/.mqtt_password`. Controller ID from `~/.mqtt_userid` (must match target device MAC, currently `38:54:39:34:62:d7/request`).
- **ESP-Now**: Used for controller-to-device communication within the RBR-Now network

## Running

```bash
# Run the controller (checks for existing instance, sets EASYCODER_SRC)
./run-controller.sh

# The controller is normally triggered every 60 seconds by cron
# It runs 6 cycles of 10 seconds each per invocation
```

The UI is a static webapp — must be served via HTTP (not `file://`) because it uses XHR to load scripts. Run `python3 -m http.server 8080` and open `http://localhost:8080/index.html`. The UI prompts for the MQTT password on first use and stores it in localStorage.

## Repository Structure

- `controller.ecs` — Main controller script (EasyCoder Python dialect)
- `controller.py` — Python launcher that loads the EasyCoder runtime and starts `newController.ecs`
- `deviceControl.ecs` — Device control logic for RBR-Now relay/thermometer devices
- `simulator.ecs` — Controller simulator for testing without hardware
- `scanner.ecs`, `flash-device.ecs` — Device management utilities
- `index.html` — UI entry point; embeds an EasyCoder loader script inline
- `resources/easycoder/` — JavaScript EasyCoder runtime modules (Core.js, Browser.js, Webson.js, etc.)
- `resources/ecs/` — UI EasyCoder scripts (rbr.ecs is main, plus mode/calendar/statistics/etc.)
- `resources/webson/` — Webson JSON UI layout definitions
- `resources/css/`, `resources/icon/`, `resources/img/` — Static assets
- `RBRNow/` — MicroPython firmware for ESP32 devices (master/slave networking via ESP-Now)
- `plugins/ec_p100.py` — EasyCoder plugin for TP-Link P100 smart plug control
- `rbr_ui/`, `rbrconf/` — Python GUI tools for configuration
- `config.json` — RBR-Now device network configuration (SSIDs, MACs, pin mappings)
- `map.json` — System map: rooms, thermometer MACs, device types, modes, timing schedules
- `params.json`, `devices.json`, `thermometers.json` — Runtime configuration files
- `AI/` — Architecture and working rules documentation for AI contributors

## Working Rules

- **EasyCoder scripts are the source of truth for behavior** — make surgical changes, preserve command vocabulary and flow, prefer existing labels/subroutines
- **Webson JSON defines UI structure** — renaming element IDs requires matching changes in `.ecs` scripts
- **No build tools required** — the system runs directly from source files
- If editing EasyCoder JS runtime modules, rebuild with `build-easycoder` in the easycoder repo
- Symlinks to EasyCoder sources can be refreshed with `relink-easycoder.sh`
- Prefer explicit state handling over hidden side effects
- Avoid modern JS syntax (`??`, optional chaining) for compatibility with older runtimes

## Configuration Data

- `map.json` — Physical system layout: room names, thermometer MACs, device types, operating modes (timed/boost/advance/on/off), temperature schedules per profile
- `config.json` — RBR-Now network: device roles (master/slave), SSIDs, pin assignments, relay/LED config
- Multiple profiles (e.g., Weekday, Weekend) with an optional calendar mapping days to profiles

## EasyCoder Language Reference

Use `/ecs-js` for JS dialect context and `/ecs-python` for Python dialect context. Use `/ecs-review` to check `.ecs` files for syntax correctness.

