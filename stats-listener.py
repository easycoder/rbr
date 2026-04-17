#!/usr/bin/env python3
"""
stats-listener.py - MQTT listener that records room statistics to CSV files

Subscribes to {MAC}/stats topics on the local MQTT broker and writes
statistics to: /var/lib/rbr-stats/{MAC}/{room}/{YYYY}/{MM}/{DD}.csv

Each CSV line: timestamp,target,temperature,humidity
(timestamp in ms, target/temperature in centidegrees, humidity as reported)

Usage:
    python3 stats-listener.py [--broker localhost] [--port 1883] [--data-dir /var/lib/rbr-stats]
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime

import paho.mqtt.client as mqtt

data_dir = "/var/lib/rbr-stats"


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected to MQTT broker (rc={reason_code})")
    client.subscribe("+/stats", qos=0)
    print("Subscribed to +/stats")


def on_message(client, userdata, msg):
    topic = msg.topic
    try:
        raw = msg.payload.decode("utf-8", errors="replace")
        # Strip AllSpeak chunk prefix (e.g. "!last!1 ")
        if raw.startswith("!last!"):
            space = raw.index(" ")
            raw = raw[space + 1:]
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        print(f"Bad payload on {topic}: {msg.payload[:100]}")
        return

    if payload.get("action") != "stats":
        return

    message = payload.get("message", "")
    if not message:
        return

    # Extract MAC from topic: {MAC}/stats
    parts = topic.split("/")
    if len(parts) != 2:
        return
    mac = parts[0]

    # Parse message: room,timestamp,target,temperature,humidity
    fields = message.split(",")
    if len(fields) < 5:
        print(f"Bad stats format from {mac}: {message}")
        return

    room = fields[0]
    try:
        timestamp = int(fields[1])
        target = int(fields[2])
        temperature = int(fields[3])
        humidity = int(fields[4])
    except ValueError:
        print(f"Bad numeric values from {mac}/{room}: {message}")
        return

    # Build path: {data_dir}/{mac}/{room}/{YYYY}/{MM}/{DD}.csv
    dt = datetime.fromtimestamp(timestamp / 1000)
    dir_path = os.path.join(data_dir, mac, room, dt.strftime("%Y"), dt.strftime("%m"))
    os.makedirs(dir_path, exist_ok=True)

    file_path = os.path.join(dir_path, f"{dt.strftime('%d')}.csv")
    line = f"{timestamp},{target},{temperature},{humidity}\n"

    try:
        with open(file_path, "a") as f:
            f.write(line)
    except OSError as e:
        print(f"Error writing {file_path}: {e}")


def main():
    global data_dir

    parser = argparse.ArgumentParser(description="RBR statistics MQTT listener")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--username", default=None, help="MQTT username")
    parser.add_argument("--password", default=None, help="MQTT password")
    parser.add_argument("--data-dir", default="/var/lib/rbr-stats", help="Data directory")
    args = parser.parse_args()

    data_dir = args.data_dir
    os.makedirs(data_dir, exist_ok=True)

    client = mqtt.Client(
        client_id=f"rbr-stats-listener-{os.getpid()}",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    if args.username:
        client.username_pw_set(args.username, args.password)
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"Connecting to {args.broker}:{args.port}...")
    try:
        client.connect(args.broker, args.port)
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)

    print(f"Writing stats to {data_dir}")
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        client.disconnect()


if __name__ == "__main__":
    main()
