# RBR Desktop App

A desktop version of the Room-By-Room UI, mirroring the **new-ui web PWA** design language (top bar, profile pills, room cards, menu sheet). It is an AllSpeak graphics app (PySide6) that talks to the controller over MQTT via the local mosquitto — no internet required.

```
desktop/
├── rbr-desktop.as      AllSpeak app script (graphics + mqtt)
├── rbr_ui.py           plugin: the RBR variable types (rbrwin, topbar,
│                       profilesbar, room, sheet) and their commands
├── rbrwidgets.py       the PySide6 widgets (PWA-style presentation)
└── assets/             icons (from new-ui/resources/icon)
```

The RBR-specific widget types live in this plugin, not the AllSpeak core pack — see `../doc/PROPOSAL-allspeak-rounded-rectangle.md`.

## Running

Run from this directory (the plugin files are resolved from the working directory):

```sh
cd desktop
allspeak rbr-desktop.as
```

Connection settings come from `desktop/config.json` if present (`broker`, `port`, `mac`, `username`, `password` — copy `config.example.json` to `config.json` to make one); otherwise the app defaults to running **on the controller** (`localhost`). For another computer on the same LAN, set the broker to the controller's LAN IP — no internet needed, the router only carries LAN traffic.

Example `config.json` for a LAN computer:

```json
{ "broker": "192.168.1.128", "port": 1883,
  "mac": "c8:21:58:2c:5c:8b",
  "username": "rbr", "password": "…" }
```

Dependencies: the `allspeak-ai` pip package and PySide6 (`pip install allspeak-ai pyside6`).

### On the controller (RBR Server)

`rbr-setup.sh` step 8b installs PySide6, writes `/etc/systemd/system/rbr-desktop.service`, and starts the UI on the controller's own display. Without the service, run it manually as above.

### On another computer on the LAN

```sh
pip install allspeak-ai pyside6
git clone <rbr repo>  # or copy the desktop/ directory
cd <repo>/desktop
cp config.example.json config.json   # then edit the broker to the controller's LAN IP
allspeak rbr-desktop.as
```

The app needs the allspeak-py runtime fixes below — until they are upstream, run it with the patched runtime (this repo's `.scratch/` copy during development).

## Runtime fixes required in allspeak-py

The current allspeak-py runtime needs five small fixes for MQTT programs to run reliably — **the controller dies at connect without fix 1** (`Improper use of runtime function` from the MQTT thread) and **dies at the first device poll without fix 5** (`No reply received from module "DeviceModule"`). A ready-to-apply patch for the pip-installed runtime is **`runtime-fixes.patch`** in this directory:

```sh
SITE=$(python3 -c "import allspeak, os; print(os.path.dirname(allspeak.__file__))")
cp "$SITE"/as_mqtt.py{,.bak}; cp "$SITE"/as_program.py{,.bak}; cp "$SITE"/as_core.py{,.bak}
cd "$SITE" && patch -p1 -i <path-to>/runtime-fixes.patch
```

(Note: pip updates will overwrite the patched files — fold the fixes into `~/dev/allspeak` for the long term.)

The fixes are applied in this repo's `../.scratch/` copy for development; the patches below are what to fold into `allspeak-py`.

### 1. `on_connect` thread safety (`allspeak/as_mqtt.py`)

`on_connect` runs on the paho (MQTT) thread and called `program.getVariable()` — which calls `ensureRunning()` and fails whenever the main flow is idle (`running=False`), i.e. the steady state of a graphics app. Fix: resolve topic names/QoS eagerly in `create()` (main thread) and let `on_connect` use the captured values.

```python
# in create(): after self.topics = topics
self.topic_specs = []
for item in topics:
    record = self.program.getVariable(item)
    topic = self.program.getObject(record)
    self.topic_specs.append((topic.getName(), topic.getQoS()))

# in on_connect(): replace the getVariable loop with
for name, qos in self.topic_specs:
    self.client.subscribe(name, qos=qos)
```

### 2. `plain` clause for LAN brokers (`allspeak/as_mqtt.py`)

The runtime auto-enables TLS for any non-`localhost` broker, but the local mosquitto is plain TCP (1883). Add an opt-out keyword:

```python
# MQTT_CLAUSE_KEYWORDS: add 'plain'
# in k_mqtt's port branch:  elif token == 'plain': self.nextToken(); command['plain'] = True
# in r_mqtt: client.create(..., plain=command.get('plain', False))
# in create(): if not plain and broker not in ('localhost', '127.0.0.1'): self.client.tls_set()
```

### 3. `queueIntent` wake-up (`allspeak/as_program.py`)

`Program.flush()` only executes queued commands while `running=True`, and `queueIntent` (used by the MQTT thread) never set it — so an idle program silently dropped connect/message intents. Fix:

```python
def queueIntent(self, pc):
    global intent_queue
    self.running = True   # wake an idle program so the intent is drained
    with intent_lock:
        item = ECValue()
        item.program = self
        item.pc = pc
        intent_queue.append(item)
```

### 4. MQTT client registers as a server (`allspeak/as_mqtt.py`)

In CLI mode the main loop calls `flush()` only while `running=True` and breaks out when idle unless a "server" is registered (the HTTP-server domain does this via `program.servers.append(self)`; the MQTT client did not). An idle MQTT script therefore froze — the MQTT thread kept the process alive but nothing drained queued continuations. Fix: in `MQTTClient.create()` add `program.servers.append(self)`. Graphics apps are unaffected (the Qt timer flushes unconditionally) but CLI MQTT tools need this.

### 5. Direct-reply module messages (`allspeak/as_core.py`)

The `send … to {module} and assign reply to {var}` path runs the child's on-message handler with `module.flush(module.onMessagePC)` — but a child module's main flow has usually ended (`stop` → `running=False`), and `flush()` only executes `while running`, so the handler never ran and the parent timed out with `No reply received from module "…"`. This is what kills `controller.as` at the first `send RoomSpec to DeviceModule` on current runtimes. Fix: wake the child before flushing:

```python
module.running = True
module.flush(module.onMessagePC)
```

### Why the app keeps a tight wait loop

Even with fix 3, the app keeps its main flow alive (`MainLoop: wait 1 tick → go to MainLoop`). This is the documented CLI-MQTT pattern (the controller does the same) and guarantees MQTT handlers run promptly. `on tick` is not used: in graphics mode ticks only fire while the program is idle, which conflicts with the wait loop.

## Protocol notes (what the app sends/receives)

- Subscribes to its own topic `RBR-desktop-<random>`.
- Publishes `{sender: {name, qos}, action}` to the controller's topic (the MAC). `first` fetches the full map; `refresh` (every 10 s) re-pushes it only when something changed.
- Replies arrive chunked (`!last!1 …`); the runtime reassembles them. A plain-JSON message is silently dropped by the runtime — always send via the mqtt domain, never raw.
- The reply's `message` is the full map: profiles, per-room live state (temperature in integer hundredths, relay, mode, status…), request relay, calendar, system name. `profile` is the active profile index.

## Status

- [x] MQTT + graphics coexistence (proven in a spike, Phase 1)
- [x] Window, top bar, profile bar, room cards (Phase 2)
- [x] Live room list over MQTT (Phase 2)
- [x] Mode control, profiles, main-menu actions (Phase 3)
- [x] Schedule editor — per-room timed periods, profile picker, add/delete (mirrors the PWA's schedule editor) (Phase 3)
- [ ] systemd unit + rbr-setup.sh additions + LAN runbook (Phase 4)

## `room` type decision

**Full Python plugin (current implementation) — confirmed.** The guiding principle: the UI is a set of component parts ("what primary elements do you see when you look at the UI?"). `room` is one; other RBR-specific composite types (topbar, profilesbar, sheet, rbrwin) are siblings. Anything generally useful that spins out gets proposed as a standard AllSpeak type (see `../doc/PROPOSAL-allspeak-rounded-rectangle.md`).

Phase 3 (interactions) builds on this.
