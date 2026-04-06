#!/usr/bin/env python3
"""
zigbee-pair.py - Command-line tool for pairing Zigbee devices with RBR

Connects to the MQTT broker, enables Zigbee2MQTT permit_join,
monitors for new devices, and updates local config files.

Usage:
    python3 zigbee-pair.py                  # Interactive pairing mode
    python3 zigbee-pair.py --list           # List paired devices
    python3 zigbee-pair.py --rename OLD NEW # Rename a device
    python3 zigbee-pair.py --remove NAME    # Remove a device
"""

import argparse
import json
import os
import sys
import threading
import time

import paho.mqtt.client as mqtt

script_dir = os.path.dirname(os.path.abspath(__file__))

# State
devices = {}          # Current device list from bridge
new_devices = []      # Newly joined devices during this session
permit_join_active = False
client = None
connected_event = threading.Event()
devices_received = threading.Event()

def load_config():
    """Load MQTT config, same as zigbee-bridge.py."""
    config_path = os.path.join(script_dir, "zigbee-config.json")
    if os.path.exists(config_path):
        with open(config_path) as f:
            return json.load(f)

    config = {
        "broker": "rbrheating.duckdns.org",
        "port": 8883,
        "username": "rbr",
        "password": "",
    }
    pw_path = os.path.expanduser("~/.mqtt_password")
    if os.path.exists(pw_path):
        with open(pw_path) as f:
            config["password"] = f.read().strip()
    return config

def on_connect(c, userdata, flags, reason_code, properties):
    global client
    print(f"Connected to MQTT broker")
    c.subscribe("zigbee2mqtt/bridge/#", qos=1)
    connected_event.set()

def on_message(c, userdata, msg):
    topic = msg.topic
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return

    if topic == "zigbee2mqtt/bridge/devices":
        _handle_devices(payload)

    elif topic == "zigbee2mqtt/bridge/event":
        _handle_event(payload)

    elif topic == "zigbee2mqtt/bridge/response/permit_join":
        status = payload.get("data", {}).get("value", False)
        print(f"Permit join: {'enabled' if status else 'disabled'}")

    elif topic == "zigbee2mqtt/bridge/state":
        state = payload.get("state", "unknown") if isinstance(payload, dict) else payload
        print(f"Zigbee2MQTT state: {state}")

def _handle_devices(devices_list):
    global devices
    devices = {}
    for dev in devices_list:
        fname = dev.get("friendly_name", "")
        if fname and fname != "Coordinator":
            devices[fname] = {
                "ieee": dev.get("ieee_address", ""),
                "type": dev.get("type", ""),
                "model": (dev.get("definition") or {}).get("model", "unknown"),
                "vendor": (dev.get("definition") or {}).get("vendor", "unknown"),
                "supported": dev.get("supported", False),
            }
    devices_received.set()

def _handle_event(payload):
    event_type = payload.get("type", "")
    data = payload.get("data", {})

    if event_type == "device_joined":
        ieee = data.get("ieee_address", "unknown")
        fname = data.get("friendly_name", ieee)
        print(f"\n*** New device joined: {fname} (IEEE: {ieee}) ***")
        new_devices.append({"ieee": ieee, "friendly_name": fname})

    elif event_type == "device_interview":
        status = data.get("status", "")
        fname = data.get("friendly_name", "unknown")
        if status == "started":
            print(f"    Interviewing {fname}...")
        elif status == "successful":
            definition = data.get("definition", {})
            model = definition.get("model", "unknown") if definition else "unknown"
            vendor = definition.get("vendor", "unknown") if definition else "unknown"
            print(f"    Interview complete: {fname} - {vendor} {model}")
            # Update the new_devices entry
            for nd in new_devices:
                if nd["friendly_name"] == fname or nd["ieee"] == data.get("ieee_address"):
                    nd["model"] = model
                    nd["vendor"] = vendor
        elif status == "failed":
            print(f"    Interview FAILED for {fname}")

    elif event_type == "device_announce":
        fname = data.get("friendly_name", "unknown")
        print(f"    Device announced: {fname}")

def connect_mqtt():
    global client
    config = load_config()
    if not config["password"]:
        print("Error: No MQTT password configured.")
        print("Create zigbee-config.json or ~/.mqtt_password")
        sys.exit(1)

    client = mqtt.Client(
        client_id=f"rbr-zigbee-pair-{os.getpid()}",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    client.username_pw_set(config["username"], config["password"])
    client.tls_set()
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"Connecting to {config['broker']}:{config['port']}...")
    client.connect(config["broker"], config["port"])
    client.loop_start()

    if not connected_event.wait(timeout=10):
        print("Error: Could not connect to MQTT broker")
        sys.exit(1)

def list_devices():
    """List all paired Zigbee devices."""
    connect_mqtt()

    # Wait for device list
    print("Waiting for device list from Zigbee2MQTT...")
    if not devices_received.wait(timeout=10):
        print("No response from Zigbee2MQTT. Is it running?")
        sys.exit(1)

    if not devices:
        print("No Zigbee devices paired.")
    else:
        print(f"\n{'Name':<25} {'IEEE Address':<25} {'Model':<20} {'Vendor':<20}")
        print("-" * 90)
        for name, info in sorted(devices.items()):
            print(f"{name:<25} {info['ieee']:<25} {info['model']:<20} {info['vendor']:<20}")
    print()

    client.loop_stop()
    client.disconnect()

def rename_device(old_name, new_name):
    """Rename a Zigbee device in Zigbee2MQTT."""
    connect_mqtt()
    time.sleep(1)

    payload = json.dumps({"from": old_name, "to": new_name})
    client.publish("zigbee2mqtt/bridge/request/device/rename", payload, qos=1)
    print(f"Rename request sent: '{old_name}' -> '{new_name}'")
    time.sleep(2)

    client.loop_stop()
    client.disconnect()

def remove_device(name):
    """Remove a Zigbee device from Zigbee2MQTT."""
    confirm = input(f"Remove device '{name}'? This cannot be undone. (y/N): ")
    if confirm.lower() != "y":
        print("Cancelled.")
        return

    connect_mqtt()
    time.sleep(1)

    payload = json.dumps({"id": name, "force": False})
    client.publish("zigbee2mqtt/bridge/request/device/remove", payload, qos=1)
    print(f"Remove request sent for '{name}'")
    time.sleep(2)

    client.loop_stop()
    client.disconnect()

def pair_mode():
    """Interactive pairing mode."""
    connect_mqtt()

    # Wait for initial device list
    print("Waiting for Zigbee2MQTT...")
    if not devices_received.wait(timeout=10):
        print("No response from Zigbee2MQTT. Is it running?")
        sys.exit(1)

    print(f"\nCurrently {len(devices)} device(s) paired.")
    print("Enabling pairing mode for 120 seconds...")
    print("Put your Zigbee device into pairing mode now.")
    print("(Press Ctrl+C to stop)\n")

    # Enable permit_join
    payload = json.dumps({"value": True, "time": 120})
    client.publish("zigbee2mqtt/bridge/request/permit_join", payload, qos=1)

    try:
        countdown = 120
        while countdown > 0:
            time.sleep(1)
            countdown -= 1
            if countdown % 30 == 0 and countdown > 0:
                print(f"  {countdown} seconds remaining...")
    except KeyboardInterrupt:
        print("\nStopping...")

    # Disable permit_join
    payload = json.dumps({"value": False})
    client.publish("zigbee2mqtt/bridge/request/permit_join", payload, qos=1)

    if new_devices:
        print(f"\n{len(new_devices)} new device(s) joined this session:")
        for nd in new_devices:
            model = nd.get("model", "unknown")
            print(f"  - {nd['friendly_name']} (IEEE: {nd['ieee']}, Model: {model})")

        # Offer to rename
        for nd in new_devices:
            current = nd["friendly_name"]
            new_name = input(f"\nRename '{current}'? Enter new name (or press Enter to keep): ").strip()
            if new_name and new_name != current:
                rename_device(current, new_name)
                nd["friendly_name"] = new_name

        print("\nTo use these devices in RBR, add them to map.json:")
        print('  For a smartplug relay:  "relays": ["<device_name>"], "relayType": "Zigbee"')
        print('  For a thermometer sensor:  "sensor": "<device_name>", "sensorType": "Zigbee"')
    else:
        print("\nNo new devices joined.")

    time.sleep(1)
    client.loop_stop()
    client.disconnect()

def main():
    parser = argparse.ArgumentParser(description="Zigbee device pairing tool for RBR")
    parser.add_argument("--list", action="store_true", help="List paired devices")
    parser.add_argument("--rename", nargs=2, metavar=("OLD", "NEW"), help="Rename a device")
    parser.add_argument("--remove", metavar="NAME", help="Remove a device")
    args = parser.parse_args()

    if args.list:
        list_devices()
    elif args.rename:
        rename_device(args.rename[0], args.rename[1])
    elif args.remove:
        remove_device(args.remove)
    else:
        pair_mode()

if __name__ == "__main__":
    main()
