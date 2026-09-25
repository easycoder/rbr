# Project Overview (for AI)

## What this repo is

Room By Room (RBR) is an open-source smart central heating control system with:

- **Controller** — Python AllSpeak scripts running on a Linux mini-PC that manage heating per-room via Zigbee thermometers and relays, plus legacy RBR-Now ESP32 devices
- **UI** — A browser-based mobile webapp (PWA) written in JavaScript AllSpeak with Webson-rendered DOM
- **REST server** — PHP on shared hosting (rbrheating.com, not in this repo)

Communication between controller and UI is via MQTT.

## Key files

### Controller
- `controller.as` — main controller loop: loads map, processes rooms, manages MQTT, calls device control
- `deviceControl.as` — device-level operations: Zigbee relay on/off, RBR-Now relay on/off, temperature reading
- `simulator.as` — standalone simulator for testing controller logic without real hardware

### UI (legacy, served from root)
- `index.html` — entry point, loads AllSpeak runtime and fetches `resources/as/rbr.as`
- `resources/webson/*.json` — 40 Webson screen layouts
- `resources/as/rbr.as` — main UI script
- `resources/as/*.as` — supporting scripts (roomedit, profiles, statistics, etc.)

### UI (new PWA, served from `/new-ui/`)
- `new-ui/index.html` — PWA entry point with service worker and manifest
- `new-ui/resources/as/shell.as` — single ~2700-line shell script that boots the app, opens MQTT, renders the home screen, and routes all user gestures
- `new-ui/resources/as/*.as` — supporting scripts (profile-sheet, schedule-editor, map-to-rooms, device-editor)
- `new-ui/resources/webson/*.json` — new UI Webson layouts
- `new-ui/sw.js` — service worker with cache management

### Infrastructure
- `deploy.sh` — rsyncs UI + controller files to rbrheating.com (`--release` bumps version for customer controllers)
- `config.json` — RBR-Now device hardware configuration (pins, SSIDs, channels)
- `devices.json` — room-to-relay mapping
- `params.json` — controller runtime parameters
- `RBRNow/` — MicroPython firmware source for RBR-Now ESP32 devices
- `credentials.example.json` — MQTT/mail credential format for production deployment

## Main design choices
- AllSpeak scripts handle all high-level behaviour (controller logic, UI flow)
- MQTT is the sole communication path between controller and UI
- Webson JSON defines screen structure; AllSpeak attaches to stable element IDs
- The controller self-times 6×10-second processing cycles per invocation; re-launched every ~60s by cron or a process supervisor
- No software frameworks; minimal dependencies for maintainability

## External references
- AllSpeak language: https://allspeak.ai/learn/ (reference + idioms)
- AllSpeak repo: https://github.com/easycoder/allspeak.ai
- Webson: https://github.com/easycoder/webson
- AllSpeak Codex intro: https://easycoder.github.io/allspeak.ai/codex

## Practical workflow
- Edit `.as` files directly; the human reviews that generated code reads sensibly
- For JS runtime edits: update source in the allspeak repo, run `build-allspeak`, then `pin-allspeak.sh` to promote the dist file
- For UI changes: update Webson JSON *and* matching AllSpeak `attach`/`on click` references together
- Deploy with `./deploy.sh`; use `--release` to push the version stamp for customer controllers
