#!/usr/bin/env python3
"""
zigbee-bridge.py - HTTP/MQTT bridge for Zigbee2MQTT integration with RBR

Connects to the MQTT broker, subscribes to zigbee2mqtt/# topics,
and provides a local HTTP interface for deviceControl.allspeak to send
relay commands to Zigbee smartplugs.

Also collects Zigbee thermometer data and writes it to the volatile data
directory (see below) as zigbee-temperatures.json, for the controller to read.

Usage:
    python3 zigbee-bridge.py [--port 8889] [--config zigbee-config.json]

The bridge expects zigbee-config.json with MQTT broker details:
{
    "broker": "localhost",
    "port": 1883,
    "http_port": 8889
}
"""

import argparse
import json
import os
import re
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import paho.mqtt.client as mqtt

# ---------------------------------------------------------------------------
# Globals shared between MQTT thread and HTTP thread
# ---------------------------------------------------------------------------
device_states = {}       # {friendly_name: {state, temperature, humidity, battery, ...}}
device_states_lock = threading.Lock()
bridge_devices = {}      # {friendly_name: {ieee, type, model, ...}} from zigbee2mqtt/bridge/devices
mqtt_client = None
script_dir = os.path.dirname(os.path.abspath(__file__))


def volatile_dir(base):
    """Directory for regenerable data — the readings file, which this process
    rewrites in full on every temperature message.

    A one-line `volatile-root` file beside the script names it (rbr-setup.sh
    writes `/run/rbr`, a tmpfs, so the file never touches the card or the disk).
    Without that file the readings stay beside the script, which is what a dev
    machine gets. heatlog-root in the controller is the same pattern.
    """
    try:
        with open(os.path.join(base, "volatile-root")) as f:
            root = f.read().strip()
        if root:
            return root
    except OSError:
        pass
    return base


temperatures_path = os.path.join(volatile_dir(script_dir), "zigbee-temperatures.json")
trv_path = os.path.join(volatile_dir(script_dir), "zigbee-trv.json")
trv_commands = {}             # {friendly_name: {setpoint, mode, ts}} — last setpoint sent
trv_commands_lock = threading.Lock()

# A relay that hasn't been seen by zigbee2mqtt for this long (seconds) is
# treated as non-responsive. The controller polls every ~5s, so a healthy
# device refreshes last_seen constantly; 30 minutes is a very generous bound
# that only trips when a device has genuinely stopped reporting (e.g. it was
# powered down).
OFFLINE_AFTER_SECONDS = 1800

# Fallback for devices that died BEFORE this bridge process started: they have
# no cached state, no last_seen and (without availability enabled) no
# availability message, so staleness alone can never flag them. Once a device
# known to zigbee2mqtt (it appears in bridge/devices) has failed to report
# anything for this grace period since bridge start, it is presumed dead. The
# controller commands every relay every ~5s, so a healthy relay reports well
# within the grace period.
NEVER_SEEN_GRACE_SECONDS = 300
BRIDGE_START_TIME = time.time()

# zigbee2mqtt reports undelivered commands on zigbee2mqtt/bridge/logging:
#   {"level":"error","message":"z2m: Publish 'set' 'state' to 'Hall-radiator'
#    failed: 'Error: ZCL command ... timed out after 10000ms'"}
#
# These are mostly redundant re-assertions of a state the device already
# holds — the controller re-commands every relay every ~5s — so they are NOT
# counted as relay failures. Doing that would flag quiet-but-healthy relays
# and force whole rooms off: measured on a live system, of 3619 such
# failures, 3616 were `off` commands to relays already off and only 3 were
# real `on` transitions. They are kept as a DIAGNOSTIC only, surfaced on
# /health, because a device that never acknowledges is worth knowing about
# before a room actually needs heat.
set_failures = {}            # {friendly_name: {"count": int, "last": epoch}}
set_failures_lock = threading.Lock()
SET_FAILURE_PATTERN = re.compile(
    r"Publish 'set' 'state' to '([^']+)' failed")

# After publishing a relay command we wait for the device to confirm it by
# reporting the commanded state back through zigbee2mqtt. The cached state may
# be months old (long shutdowns), so echoing it would make a dead relay look
# healthy. The budget is a compromise: healthy relays confirm in well under a
# second, while a dead device costs the controller up to CONFIRM_TIMEOUT per
# failing relay per cycle (the server is threaded, so other requests still
# get served during the wait).
CONFIRM_TIMEOUT = 2.0
CONFIRM_POLL = 0.25


def _device_responding(state, device_name=None):
    """True if a device should be treated as reachable.

    Primary signal is zigbee2mqtt's per-device availability
    (zigbee2mqtt/{name}/availability = "online"/"offline"): an explicitly
    offline device is non-responsive, an explicitly online one is reachable
    even if it has been quiet — availability is refreshed by zigbee2mqtt's own
    pings, so treating a quiet-but-online device as dead would be a false
    positive (and the controller's warn/fail status forces the relay off).
    Only when availability is unknown — not enabled in zigbee2mqtt, or the
    bridge restarted before the first availability message — do we fall back
    to last_seen staleness with the generous OFFLINE_AFTER_SECONDS bound.

    Final fallback: a device that zigbee2mqtt knows about (it is in
    bridge_devices) but that has never reported since this bridge started is
    treated as non-responsive after NEVER_SEEN_GRACE_SECONDS. This is the
    "bridge restarted after the device died" case, where the bridge would
    otherwise answer "unknown" forever.
    """
    if state.get("available") is True:
        return True
    if state.get("available") is False:
        return False
    last_seen = state.get("last_seen", 0)
    if last_seen and time.time() - last_seen > OFFLINE_AFTER_SECONDS:
        return False
    if (not state and device_name in bridge_devices
            and time.time() - BRIDGE_START_TIME > NEVER_SEEN_GRACE_SECONDS):
        return False
    return True


def _read_device_state(device_name):
    """Snapshot the cached state for a device under the lock."""
    with device_states_lock:
        return device_states.get(device_name, {})


def _wait_for_confirmation(device_name, desired_state):
    """Poll the device cache until it reports the commanded state.

    The cached state before a command may be months old (the system was
    switched off for the summer), so we must not trust it: a device that
    never confirms a command is dead or unreachable. Polls for up to
    CONFIRM_TIMEOUT seconds; returns the final cached state either way.
    """
    deadline = time.time() + CONFIRM_TIMEOUT
    while time.time() < deadline:
        time.sleep(CONFIRM_POLL)
        state = _read_device_state(device_name)
        if not _device_responding(state, device_name):
            return state  # went offline mid-wait; caller reports it
        if state.get("state", "").upper() == desired_state:
            return state
    return _read_device_state(device_name)


# ---------------------------------------------------------------------------
# MQTT callbacks
# ---------------------------------------------------------------------------
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected to MQTT broker (rc={reason_code})")
    client.subscribe("zigbee2mqtt/#", qos=1)

def on_message(client, userdata, msg):
    topic = msg.topic
    try:
        payload = json.loads(msg.payload.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return

    # Bridge device list — gives us the mapping of friendly names to IEEE addresses
    if topic == "zigbee2mqtt/bridge/devices":
        _handle_bridge_devices(payload)
        return

    # Bridge events (pairing, etc.) — log them
    if topic == "zigbee2mqtt/bridge/event":
        print(f"Zigbee event: {json.dumps(payload)}")
        return

    # Failed commands — diagnostic only, see set_failures.
    if topic == "zigbee2mqtt/bridge/logging":
        _handle_bridge_logging(payload)
        return

    # Ignore other bridge topics
    if topic.startswith("zigbee2mqtt/bridge/"):
        return

    # Device availability: zigbee2mqtt/{friendly_name}/availability carries
    # "online"/"offline" (zigbee2mqtt configured with availability: true).
    # This is the reliable signal that a device — e.g. a powered-down relay —
    # has stopped responding: its state messages simply stop arriving, so the
    # cached state alone can never reveal it. deviceControl.allspeak is told the
    # device is non-responsive via the HTTP handler below.
    parts = topic.split("/")
    if len(parts) == 3 and parts[2] == "availability":
        device_name = parts[1]
        # Only the two documented payloads are meaningful; ignore anything
        # unexpected rather than guessing the device is offline.
        if payload not in ("online", "offline"):
            return
        with device_states_lock:
            state = device_states.setdefault(device_name, {})
            state["available"] = (payload == "online")
            print(f"Device {device_name} "
                  f"{'online' if state['available'] else 'OFFLINE'}")
        return

    # Device state update: zigbee2mqtt/{friendly_name}
    if len(parts) == 2:
        device_name = parts[1]
        _handle_device_update(device_name, payload)

def _handle_bridge_devices(devices_list):
    """Process the device list from zigbee2mqtt/bridge/devices."""
    global bridge_devices
    new_devices = {}
    for dev in devices_list:
        fname = dev.get("friendly_name", "")
        if fname and fname != "Coordinator":
            new_devices[fname] = {
                "ieee": dev.get("ieee_address", ""),
                "type": dev.get("type", ""),
                "model": dev.get("definition", {}).get("model", "") if dev.get("definition") else "",
                "vendor": dev.get("definition", {}).get("vendor", "") if dev.get("definition") else "",
                "supported": dev.get("supported", False),
            }
    bridge_devices = new_devices
    print(f"Zigbee2MQTT reports {len(new_devices)} device(s): {list(new_devices.keys())}")

def _handle_bridge_logging(event):
    """Record a failed zigbee2mqtt command for diagnostic visibility.

    Diagnostic only: these are not relay failures (see set_failures). Counts
    are per friendly name and never reset, so a reader should judge recency
    from the `last` timestamp alongside the count.
    """
    if not isinstance(event, dict) or event.get("level") != "error":
        return
    match = SET_FAILURE_PATTERN.search(str(event.get("message", "")))
    if not match:
        return
    device_name = match.group(1)
    with set_failures_lock:
        entry = set_failures.setdefault(device_name, {"count": 0, "last": 0.0})
        entry["count"] += 1
        entry["last"] = time.time()

def _handle_device_update(device_name, payload):
    """Process a state update from a Zigbee device."""
    is_trv = False
    with device_states_lock:
        if device_name not in device_states:
            device_states[device_name] = {}
        state = device_states[device_name]

        # Relay/plug state
        if "state" in payload:
            state["state"] = payload["state"].lower()  # "on" / "off"

        # Temperature (thermometers and some plugs with energy monitoring)
        if "temperature" in payload:
            state["temperature"] = payload["temperature"]
        # TRV: local_temperature is the valve's room reading and can serve as
        # the room sensor when no separate thermometer exists.
        if "local_temperature" in payload:
            state["local_temperature"] = payload["local_temperature"]
            state["temperature"] = payload["local_temperature"]
            is_trv = True
        if "occupied_heating_setpoint" in payload:
            state["setpoint"] = payload["occupied_heating_setpoint"]
            is_trv = True
        if "system_mode" in payload:
            state["system_mode"] = payload["system_mode"]
            is_trv = True
        if "running_state" in payload:
            state["running_state"] = payload["running_state"]
            is_trv = True
        if "humidity" in payload:
            state["humidity"] = payload["humidity"]
        if "battery" in payload:
            state["battery"] = payload["battery"]

        # Energy monitoring (smartplugs)
        if "power" in payload:
            state["power"] = payload["power"]
        if "energy" in payload:
            state["energy"] = payload["energy"]

        state["last_seen"] = time.time()

    # If this device reports temperature, update the temperatures file
    if "temperature" in payload or "local_temperature" in payload:
        _update_temperatures_file()
    if is_trv:
        _update_trv_file()

def _update_temperatures_file():
    """Write Zigbee thermometer data in the same format as thermometers.json."""
    temps = {}
    with device_states_lock:
        for name, state in device_states.items():
            if "temperature" not in state:
                continue
            # Use the friendly name as key (map.json sensor field will reference this)
            temps[name] = {
                "ts": int(state.get("last_seen", time.time()) * 1000),
                "temp": int(state["temperature"] * 100),  # centidegrees, matching RBR format
                "hum": state.get("humidity", 0),
                "batt": state.get("battery", -1),
                "rssi": 0,
            }

    # Atomic write. The temp file has to live in the TARGET's directory, not the
    # script's: os.replace() is only atomic within one filesystem and raises
    # EXDEV across two. With temperatures_path on a tmpfs (/run/rbr) and the
    # script on the root filesystem, creating the temp beside the script meant
    # every write failed and the readings file was never produced at all.
    target_dir = os.path.dirname(temperatures_path) or "."
    try:
        fd, tmp_path = tempfile.mkstemp(dir=target_dir, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump(temps, f, indent=2)
        os.replace(tmp_path, temperatures_path)
    except OSError as e:
        print(f"Error writing temperatures: {e}")


def _round_setpoint(value):
    """Clamp to the TRVZB's 4-35 C range and round to its 0.5 C step."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    value = max(4.0, min(35.0, value))
    return round(value * 2) / 2


def _update_trv_file():
    """Write TRV setpoint/mode state for the controller's dial-change sync."""
    trvs = {}
    with device_states_lock:
        for name, state in device_states.items():
            if "setpoint" not in state and "system_mode" not in state:
                continue
            with trv_commands_lock:
                command = trv_commands.get(name)
            trvs[name] = {
                "setpoint": state.get("setpoint"),
                "system_mode": state.get("system_mode"),
                "running_state": state.get("running_state"),
                "local_temperature": state.get("local_temperature"),
                "battery": state.get("battery"),
                "last_seen": state.get("last_seen", 0),
                "last_command": command,
            }

    target_dir = os.path.dirname(trv_path) or "."
    try:
        fd, tmp_path = tempfile.mkstemp(dir=target_dir, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump(trvs, f, indent=2)
        os.replace(tmp_path, trv_path)
    except OSError as e:
        print(f"Error writing TRV state: {e}")


# ---------------------------------------------------------------------------
# HTTP request handler
# ---------------------------------------------------------------------------
class ZigbeeBridgeServer(ThreadingHTTPServer):
    # Threaded so /health and /devices stay responsive (and later relay
    # commands aren't delayed) while a request is blocked in the
    # command-confirmation poll. Shared state is lock-guarded; the
    # controller itself serializes device commands.
    allow_reuse_address = True

class ZigbeeBridgeHandler(BaseHTTPRequestHandler):
    """
    Endpoints:
        GET /device/{name}?state=on|off   — send relay command, return state
        GET /device/{name}                 — return current state (no command)
        GET /trv/{name}?setpoint=N&mode=heat|off — send TRV setpoint/mode
        GET /trv/{name}                    — return cached TRV state
        GET /devices                       — list all known devices
        GET /health                        — health check (+ diagnostic setFailures)

    /device returns a body with no `state` field when the device is offline,
    hasn't been seen for a while, is unknown to zigbee2mqtt, or fails to
    confirm a commanded state — so callers can detect non-response instead of
    trusting a stale cached state (e.g. an "off" from before a long shutdown).
    """

    def do_GET(self):
        parsed = urlparse(self.path)
        path_parts = parsed.path.strip("/").split("/")
        params = parse_qs(parsed.query)

        if path_parts[0] == "health":
            now = time.time()
            with set_failures_lock:
                # `age` is derived here so a reader never has to do epoch
                # arithmetic; `last` is kept for anything wanting an absolute
                # time.
                failures = {name: dict(entry, age=int(now - entry["last"]))
                            for name, entry in set_failures.items()}
            self._respond(200, {
                "status": "ok",
                "devices": len(device_states),
                # Diagnostic only: commands zigbee2mqtt could not deliver,
                # keyed by friendly name, with the time of the most recent
                # failure so a reader can tell "failing now" from "failed
                # earlier". Never used to fail a relay — see set_failures.
                "setFailures": failures,
            })
            return

        if path_parts[0] == "devices":
            with device_states_lock:
                states_snapshot = dict(device_states)
            self._respond(200, {
                "devices": bridge_devices,
                "states": states_snapshot,
            })
            return

        if path_parts[0] == "trv" and len(path_parts) >= 2:
            device_name = "/".join(path_parts[1:])
            if device_name not in bridge_devices:
                self._respond(404, {"error": f"unknown device {device_name}"})
                return

            setpoint_raw = params.get("setpoint", [None])[0]
            if setpoint_raw is not None:
                setpoint = _round_setpoint(setpoint_raw)
                if setpoint is None:
                    self._respond(400, {"error": "setpoint must be a number"})
                    return
                mode = (params.get("mode", [None])[0] or "").lower()
                if mode not in ("heat", "off"):
                    self._respond(400, {"error": "mode must be heat or off"})
                    return
                payload = {"system_mode": mode,
                           "occupied_heating_setpoint": setpoint}
                topic = f"zigbee2mqtt/{device_name}/set"
                if mqtt_client:
                    mqtt_client.publish(topic, json.dumps(payload), qos=1)
                    print(f"Published {payload} to {topic}")
                with trv_commands_lock:
                    trv_commands[device_name] = {
                        "setpoint": setpoint,
                        "mode": mode,
                        "ts": time.time(),
                    }
                state = _read_device_state(device_name)
                meta = bridge_devices.get(device_name, {})
                queued = (meta.get("type") == "EndDevice"
                          or meta.get("power_source") == "Battery")
                # A battery valve is asleep; zigbee2mqtt queues the command
                # until it next checks in. Never wait for a confirmation here.
                self._respond(200, {
                    "accepted": True,
                    "queued": queued,
                    "device": device_name,
                    "setpoint": setpoint,
                    "mode": mode,
                    "last_seen": state.get("last_seen", 0),
                })
                return

            state = _read_device_state(device_name)
            with trv_commands_lock:
                command = trv_commands.get(device_name)
            self._respond(200, {
                "device": device_name,
                "setpoint": state.get("setpoint"),
                "system_mode": state.get("system_mode"),
                "running_state": state.get("running_state"),
                "local_temperature": state.get("local_temperature"),
                "battery": state.get("battery"),
                "last_seen": state.get("last_seen", 0),
                "last_command": command,
                "responding": _device_responding(state, device_name),
            })
            return

        if path_parts[0] == "device" and len(path_parts) >= 2:
            device_name = "/".join(path_parts[1:])  # handle names with slashes
            desired_state = params.get("state", [None])[0]

            if desired_state:
                # Publish relay command to zigbee2mqtt
                desired_state = desired_state.upper()  # Zigbee2MQTT expects ON/OFF
                topic = f"zigbee2mqtt/{device_name}/set"
                payload = json.dumps({"state": desired_state})
                if mqtt_client:
                    mqtt_client.publish(topic, payload, qos=1)
                    print(f"Published {payload} to {topic}")

            # Read the cached state. If a command was sent, wait for the
            # device to confirm it: the pre-command cache may be months old,
            # and echoing it back would make a dead relay look healthy. Note
            # this only guards commanded *transitions* — a device that died
            # while already matching the commanded state is caught by the
            # availability/staleness checks in _device_responding.
            state = _read_device_state(device_name)
            if desired_state and state.get("state", "").upper() != desired_state:
                state = _wait_for_confirmation(device_name, desired_state)
                if state.get("state", "").upper() != desired_state:
                    print(f"Device {device_name} did not confirm "
                          f"{desired_state} (state={state.get('state', 'unknown')!r})")

            # A device that zigbee2mqtt reports offline (or that hasn't been
            # seen for a long time) is non-responsive. Return a body with no
            # `state` field so deviceControl.allspeak counts the reply as a relay
            # failure and the controller can flag the room, instead of
            # trusting a stale cached state (e.g. an "off" from days ago).
            if not _device_responding(state, device_name):
                self._respond(200, {
                    "error": f"device {device_name} is not responding",
                    "last_seen": state.get("last_seen", 0),
                })
                return

            # A device with no cached state at all (unknown friendly name —
            # renamed/removed in zigbee2mqtt, or the map is out of date) must
            # not be answered with a placeholder `state`, or the controller
            # would count it as a healthy relay. Flag it as a failure instead.
            relay_state = state.get("state", "")
            if not relay_state or relay_state == "unknown":
                self._respond(200, {
                    "error": f"device {device_name} has not reported a state",
                    "last_seen": state.get("last_seen", 0),
                })
                return

            # A commanded state the device never confirmed did not take
            # effect — report it as a failure rather than a silent success.
            # Note: the body must NOT carry a `state` key, or
            # deviceControl.allspeak would count it as a healthy reply.
            if desired_state and relay_state.upper() != desired_state:
                self._respond(200, {
                    "error": f"device {device_name} did not confirm "
                             f"state {desired_state}",
                    "last_seen": state.get("last_seen", 0),
                })
                return

            # Return response in a format deviceControl.allspeak can parse
            self._respond(200, {
                "state": relay_state,
                "uptime": 0,
                "power": state.get("power", 0),
                "temperature": state.get("temperature"),
                "last_seen": state.get("last_seen", 0),
            })
            return

        self._respond(404, {"error": "not found"})

    def _respond(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def log_message(self, format, *args):
        # Suppress default request logging; we log meaningful events ourselves
        pass

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def load_config(config_path):
    """Load bridge configuration."""
    if os.path.exists(config_path):
        with open(config_path) as f:
            return json.load(f)

    # Default: local Mosquitto broker, no auth
    config = {
        "broker": "localhost",
        "port": 1883,
        "http_port": 8889,
    }
    return config

def main():
    global mqtt_client

    parser = argparse.ArgumentParser(description="Zigbee2MQTT HTTP bridge for RBR")
    parser.add_argument("--port", type=int, default=8889, help="HTTP server port")
    parser.add_argument("--config", default=os.path.join(script_dir, "zigbee-config.json"),
                        help="Path to config file")
    args = parser.parse_args()

    config = load_config(args.config)
    http_port = config.get("http_port", args.port)

    # Set up MQTT
    mqtt_client = mqtt.Client(
        client_id=f"rbr-zigbee-bridge-{os.getpid()}",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    if config.get("username"):
        mqtt_client.username_pw_set(config["username"], config.get("password", ""))
    if config.get("tls", False):
        mqtt_client.tls_set()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    print(f"Connecting to MQTT broker {config['broker']}:{config['port']}...")
    try:
        mqtt_client.connect(config["broker"], config["port"])
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")
        sys.exit(1)

    # Start MQTT loop in background thread
    mqtt_client.loop_start()

    # Start HTTP server
    server = ZigbeeBridgeServer(("127.0.0.1", http_port), ZigbeeBridgeHandler)
    print(f"Zigbee bridge HTTP server listening on http://127.0.0.1:{http_port}")
    print(f"Thermometer data will be written to {temperatures_path}")
    print(f"TRV state will be written to {trv_path}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()

if __name__ == "__main__":
    main()
