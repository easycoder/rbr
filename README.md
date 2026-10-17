# Room By Room

Room By Room is an open-source control system for central heating that works room by room. Each room has its own thermometer and its own radiator control, and the system decides when each room should be heated — so the house is warm where it is being used, and the rest of it is not.

The interface is a web app, so a phone is the only device anyone has to install. The system can be seen and adjusted from anywhere, and the controller in the house carries on working regardless.

## What runs where

Three parts, plus the hardware between them:

1. **The controller** — a small Linux mini-PC in the house, running `controller.allspeak` under the AllSpeak runtime. It holds the plan (rooms, schedules, profiles), reads the thermometers, and switches each room's heating. Everything a controller needs is a plain file; see `doc/CONTROLLER-FILES.md`.
2. **The site** — `rbrheating.com`, which serves the web app at `/heat/`, the PHP endpoints it calls (`credentials.php`, `auth.php`), the controller update bundle, and the documentation reader at `/docs`. `deploy.sh` is what publishes it.
3. **The web app** — `new-ui/`, a browser PWA written in AllSpeak's JavaScript dialect. It is the only user interface: it renders the map it is given, and hands every gesture back to the controller over MQTT.

Between the controller and the radiators sit Zigbee thermometers and relays, with Zigbee2MQTT and a small HTTP bridge (`zigbee-bridge.py`) in between. A relay at the boiler asks it to fire only when some room actually wants heat.

## The plan

The map — `map.json` on the controller — is the whole configuration: **one shared room list**, carrying each room's identity (which relays it has, which thermometer serves it, whether it is frost-protected, its readings), and then, per profile, only that room's schedule state, keyed by room name. A name is the join, so a room's wiring and its schedule cannot drift into another room. `AI/MAP_FORMAT.md` is the format of record.

## Working on it

```bash
# controller, by hand (it normally runs as a service)
allspeak controller.allspeak --no-dashboard

# the web app, served statically
python3 -m http.server 9000      # then open http://localhost:9000/new-ui/index.html

# the checks that need no broker, browser or controller
tests/unit/run-unit-tests.sh
node tests/pwa-compile-check.js
node tests/pwa-device-editor-check.js
```

`AGENT.md` is the working guide — how the code is laid out, the conventions the documentation blocks follow, and the traps this language and this runtime have already cost time on. `DIFF.md` records why the system looks the way it does, change by change. Most of `doc/` and all of `docs/` are written for people rather than for agents; `docs/README.md` is the index.

## Credits

The system is built on [AllSpeak](https://allspeak.ai) — a scripting language with Python and JavaScript runtimes — and otherwise on ordinary parts: a mini-PC, Zigbee thermometers and radiator valves, and a phone. Third-party dependencies are kept to a minimum and there are no build tools: every file here is read as it stands.
