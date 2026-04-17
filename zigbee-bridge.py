#!/usr/bin/env python3
"""
zigbee-bridge.py - HTTP/MQTT bridge for Zigbee2MQTT integration with RBR

Connects to the MQTT broker, subscribes to zigbee2mqtt/# topics,
and provides a local HTTP interface for deviceControl.ecs to send
relay commands to Zigbee smartplugs.

Also collects Zigbee thermometer data and writes it to
zigbee-temperatures.json for the controller to read.

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
import sys
import tempfile
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
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
temperatures_path = os.path.join(script_dir, "zigbee-temperatures.json")

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

    # Ignore other bridge topics
    if topic.startswith("zigbee2mqtt/bridge/"):
        return

    # Device state update: zigbee2mqtt/{friendly_name}
    parts = topic.split("/")
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

def _handle_device_update(device_name, payload):
    """Process a state update from a Zigbee device."""
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
    if "temperature" in payload:
        _update_temperatures_file()

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

    # Atomic write
    try:
        fd, tmp_path = tempfile.mkstemp(dir=script_dir, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump(temps, f, indent=2)
        os.replace(tmp_path, temperatures_path)
    except OSError as e:
        print(f"Error writing temperatures: {e}")

# ---------------------------------------------------------------------------
# HTTP request handler
# ---------------------------------------------------------------------------
class ZigbeeBridgeServer(HTTPServer):
    allow_reuse_address = True

class ZigbeeBridgeHandler(BaseHTTPRequestHandler):
    """
    Endpoints:
        GET /device/{name}?state=on|off   — send relay command, return state
        GET /device/{name}                 — return current state (no command)
        GET /devices                       — list all known devices
        GET /health                        — health check
    """

    def do_GET(self):
        parsed = urlparse(self.path)
        path_parts = parsed.path.strip("/").split("/")
        params = parse_qs(parsed.query)

        if path_parts[0] == "health":
            self._respond(200, {"status": "ok", "devices": len(device_states)})
            return

        if path_parts[0] == "devices":
            self._respond(200, {
                "devices": bridge_devices,
                "states": {k: v for k, v in device_states.items()},
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

                # Wait briefly for state confirmation
                time.sleep(0.3)

            with device_states_lock:
                state = device_states.get(device_name, {})

            # Return response in a format deviceControl.ecs can parse
            relay_state = state.get("state", "unknown")
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

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()

if __name__ == "__main__":
    main()
