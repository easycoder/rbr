#!/usr/bin/env python3
"""
zigbee-mesh.py - show the Zigbee mesh as the coordinator sees it

Asks zigbee2mqtt for a network map (the neighbour and routing tables read back
from every device) and renders it as a parent tree plus a per-device table:
each device's parent, the link quality on that edge, its best and worst links,
every weak link in the mesh, and any device whose tables could not be read.

Read-only by design: it publishes one request to the broker and subscribes. It
sends no device commands and changes nothing, so it is safe to run on a live
controller at any time.

Usage:
    python3 zigbee-mesh.py                  # mesh map, default broker
    python3 zigbee-mesh.py --failures 60    # also count unanswered commands for a minute
    python3 zigbee-mesh.py --json           # machine-readable output
    python3 zigbee-mesh.py --from scan.json # render a previously saved response

The broker comes from zigbee-config.json (the same file zigbee-bridge.py reads)
and falls back to localhost:1883. Any of --broker/--port/--username/--password/
--tls override it.

A network map is slow: zigbee2mqtt interrogates each device in turn, so expect
one to three minutes on a house-sized mesh. That is also why the tool prints
progress while it waits, and why --timeout exists.
"""

import argparse
import json
import os
import re
import sys
import time

import paho.mqtt.client as mqtt

REQUEST_TOPIC = "zigbee2mqtt/bridge/request/networkmap"
RESPONSE_TOPIC = "zigbee2mqtt/bridge/response/networkmap"
LOGGING_TOPIC = "zigbee2mqtt/bridge/logging"

# zigbee2mqtt reports a command it could not deliver on bridge/logging. The
# device name is the friendly name and may contain any character but a quote.
SET_FAILURE_PATTERN = re.compile(r"Publish 'set' '[^']*' to '([^']+)' failed")

# Neighbour-table relationship values, as they appear in the raw network map.
# They are written from the point of view of the entry's owner (the link's
# source):
#   0  the source is the PARENT of the target
#   1  the source is a CHILD of the target (so the target is its parent)
#   2  siblings - heard each other, no parent/child relationship
# Routers record every neighbour as a sibling, including their own parent, so
# for a router the authoritative side is whoever claims it as a child.
REL_PARENT = 0
REL_CHILD = 1
REL_SIBLING = 2

WEAK_LQI = 40  # below this an edge is worth reporting as marginal


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------
def load_config(path):
    """Read zigbee-config.json if it is there; absence is not an error.

    The bridge treats the file as optional (falling back to localhost:1883), so
    this tool does the same - a controller without it still works.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            config = json.load(handle)
    except (OSError, ValueError):
        return {}
    return config if isinstance(config, dict) else {}


def make_client(args, config, client_id_suffix):
    """Build a configured MQTT client from the CLI arguments and config file.

    Shared by the map request and the failure watch so the broker, credentials
    and TLS setting cannot drift apart between the two.
    """
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id=f"rbr-mesh-{client_id_suffix}-{os.getpid()}")
    username = args.username if args.username is not None else config.get("username")
    password = args.password if args.password is not None else config.get("password")
    if username:
        client.username_pw_set(username, password)
    tls = args.tls if args.tls is not None else bool(config.get("tls"))
    if tls:
        import ssl
        client.tls_set(cert_reqs=ssl.CERT_NONE)
        client.tls_insecure_set(True)
    return client


def request_network_map(args, config):
    """Fetch a raw network map from zigbee2mqtt and return its `value` dict.

    Runs the MQTT client only for as long as the request takes: the response
    trickles back after the scan finishes, sometimes minutes later, which is why
    the wait prints progress.
    """
    payloads = []
    availability = {}
    started = time.time()

    def on_connect(client, userdata, flags, reason_code, properties=None):
        if reason_code != 0:
            print(f"Broker refused the connection (rc={reason_code})", file=sys.stderr)
            return
        # Availability topics are retained, so this also snapshots the current
        # online/offline state without a second request.
        client.subscribe("zigbee2mqtt/+/availability", qos=0)
        client.subscribe(RESPONSE_TOPIC, qos=1)
        client.publish(REQUEST_TOPIC, json.dumps({"type": "raw", "routes": True}), qos=1)

    def on_message(client, userdata, message):
        if message.topic == RESPONSE_TOPIC:
            payloads.append(message.payload.decode("utf-8", errors="replace"))
        elif message.topic.endswith("/availability"):
            name = message.topic.split("/")[1]
            availability[name] = message.payload.decode("utf-8", errors="replace")

    client = make_client(args, config, "map")
    print(f"Asking {args.broker}:{args.port} for a network map (this takes a minute or two)...")
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(args.broker, args.port, 60)
    except OSError as error:
        sys.exit(f"Cannot reach the MQTT broker at {args.broker}:{args.port}: {error}")
    client.loop_start()

    next_progress = started + 15
    while time.time() - started < args.timeout and not payloads:
        time.sleep(0.5)
        if time.time() >= next_progress:
            print(f"  ... still scanning ({int(time.time() - started)}s)")
            next_progress = time.time() + 15

    client.loop_stop()
    client.disconnect()

    if not payloads:
        sys.exit(f"No network map after {args.timeout}s. "
                 f"Check zigbee2mqtt is running: systemctl status zigbee2mqtt")
    response = json.loads(payloads[-1])
    if response.get("status") != "ok":
        sys.exit(f"zigbee2mqtt refused the request: {json.dumps(response.get('error'))}")
    return response.get("data", {}).get("value", {}), availability


def load_saved_map(path):
    """Read a saved response so a scan can be rendered and inspected offline."""
    with open(path, "r", encoding="utf-8") as handle:
        saved = json.load(handle)
    # Accept the full response, its `data`, or just the `value` payload.
    if "data" in saved and isinstance(saved["data"], dict):
        saved = saved["data"]
    if "value" in saved and isinstance(saved["value"], dict):
        saved = saved["value"]
    return saved, {}


# ---------------------------------------------------------------------------
# Reading the map
# ---------------------------------------------------------------------------
def parse_map(value, availability=None):
    """Turn a raw map into devices, parent edges, a parent tree and weak links.

    Kept free of printing so it can be exercised from a saved scan.

    Parent edges are taken from the relationship field: a rel=0 link means its
    source is the parent, which is the parent's own table and the trustworthy
    side for a router. A rel=1 link means its source is a child and names its
    parent in turn - that is how sleepy end devices report, and it corroborates
    the rel=0 view where both exist. Where they disagree the rel=0 edge wins,
    because a sleepy device can be slow to notice it has moved.
    """
    availability = availability or {}
    devices = {}
    for node in value.get("nodes", []) or []:
        name = node.get("friendlyName") or node.get("ieeeAddr", "?")
        definition = node.get("definition") or {}
        devices[name] = {
            "ieee": node.get("ieeeAddr", ""),
            "nwk": node.get("networkAddress"),
            "type": node.get("type", ""),
            "model": definition.get("model", ""),
            "vendor": definition.get("vendor") or node.get("manufacturerName", ""),
            "last_seen": node.get("lastSeen"),
            "failed": list(node.get("failed") or []),
            "links": {},
            "available": availability.get(name),
        }

    name_of = {info["ieee"]: name for name, info in devices.items()}
    # A device's own view of each neighbour: name -> lqi.
    for link in value.get("links", []) or []:
        source = name_of.get(link.get("source", {}).get("ieeeAddr"))
        target = name_of.get(link.get("target", {}).get("ieeeAddr"))
        if source is None or target is None:
            continue
        lqi = link.get("lqi") or 0
        devices[source]["links"][target] = {
            "lqi": lqi,
            "relationship": link.get("relationship"),
            "routes": list(link.get("routes") or []),
        }

    # A device's parent, from the neighbour tables. rel=0 is written by the
    # parent's own table ("I am the parent of that device"), so it names the
    # child in the link's target. rel=1 is written by the child's table ("that
    # device is my parent"), which is how sleepy end devices report. The rel=0
    # view wins where they disagree, because a sleepy device can be slow to
    # notice it has moved. Only the coordinator has no parent.
    parents = {}          # child -> {"parent": name, "lqi": int, "source": str}
    for name, info in devices.items():
        for neighbour, link in info["links"].items():
            if link["relationship"] == REL_CHILD and name not in parents:
                parents[name] = {"parent": neighbour, "lqi": link["lqi"],
                                 "source": "own table"}
    for name, info in devices.items():
        for neighbour, link in info["links"].items():
            if link["relationship"] == REL_PARENT and neighbour not in parents:
                if devices[neighbour]["type"] == "Coordinator":
                    continue  # the coordinator has no parent to claim
                parents[neighbour] = {"parent": name, "lqi": link["lqi"],
                                      "source": "parent's table"}

    children = {}
    for child, edge in parents.items():
        children.setdefault(edge["parent"], []).append(child)
    for group in children.values():
        group.sort()

    # One entry per pair, reported as the weaker direction: an asymmetric link
    # fails in one direction only, and the weak side is the one that matters.
    # lqi 0 is not a weak link but a neighbour recorded at some point and not
    # heard since, which is normal and would otherwise flood this list, so it is
    # ignored when choosing the reported direction and counted separately.
    directed = {}
    for source, info in devices.items():
        for neighbour, link in info["links"].items():
            directed[(source, neighbour)] = link["lqi"] or 0
    weak = []
    paired = set()
    quiet = 0
    for (source, neighbour), lqi in directed.items():
        pair = tuple(sorted((source, neighbour)))
        if pair in paired:
            continue
        paired.add(pair)
        reverse = directed.get((neighbour, source))
        candidates = [(lqi, source, neighbour)]
        if reverse is not None:
            candidates.append((reverse, neighbour, source))
        heard = [edge for edge in candidates if edge[0] > 0]
        if not heard:
            quiet += 1
            continue
        lowest, from_name, to_name = min(heard)
        other = [edge[0] for edge in candidates if (edge[1], edge[2]) != (from_name, to_name)]
        if lowest < WEAK_LQI:
            weak.append({"lqi": lowest, "from": from_name, "to": to_name,
                         "reverse": other[0] if other else None})
    weak.sort(key=lambda edge: edge["lqi"])

    return {"devices": devices, "parents": parents, "children": children,
            "weak": weak, "quiet_pairs": quiet}


def age(last_seen_ms):
    """Seconds since zigbee2mqtt last heard from a device, or None."""
    if not last_seen_ms:
        return None
    return max(0, time.time() - last_seen_ms / 1000.0)


def human_age(seconds):
    if seconds is None:
        return "-"
    if seconds < 90:
        return f"{seconds:.0f}s"
    if seconds < 5400:
        return f"{seconds / 60:.0f}m"
    return f"{seconds / 3600:.1f}h"


# ---------------------------------------------------------------------------
# Optional: which relays are failing right now
# ---------------------------------------------------------------------------
def watch_failures(args, config, seconds):
    """Count unanswered commands per device for a few seconds.

    zigbee2mqtt logs a delivery failure on bridge/logging when a device does not
    acknowledge within its timeout. Comparing those against the commands sent
    gives the miss rate that matters: 0-7% is normal on this mesh, a device at
    20%+ is not answering reliably, and 100% means it is gone.
    """
    commands = {}
    failures = {}
    ended = time.time() + seconds

    def on_connect(client, userdata, flags, reason_code, properties=None):
        client.subscribe("zigbee2mqtt/+/set", qos=1)
        client.subscribe(LOGGING_TOPIC, qos=1)

    def on_message(client, userdata, message):
        if message.topic.endswith("/set"):
            name = message.topic.split("/")[1]
            commands[name] = commands.get(name, 0) + 1
            return
        text = message.payload.decode("utf-8", errors="replace")
        if "failed" not in text:
            return
        try:
            line = json.loads(text)
        except ValueError:
            return
        match = SET_FAILURE_PATTERN.search(str(line.get("message", "")))
        if match:
            failures[match.group(1)] = failures.get(match.group(1), 0) + 1

    client = make_client(args, config, "fail")
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(args.broker, args.port, 60)
    except OSError as error:
        sys.exit(f"Cannot reach the MQTT broker at {args.broker}:{args.port}: {error}")
    client.loop_start()
    print(f"Watching relay commands for {seconds}s to count unanswered ones...")
    while time.time() < ended:
        time.sleep(0.5)
    client.loop_stop()
    client.disconnect()
    return commands, failures


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def print_tree(mesh):
    """The parent tree, one line per device, indented by depth."""
    devices = mesh["devices"]
    children = mesh["children"]
    parents = mesh["parents"]
    roots = [name for name in devices if name not in parents]
    # The coordinator is the root of the tree; anything else with no parent is
    # an orphan whose table did not name one.
    order = sorted(roots, key=lambda name: (devices[name]["type"] != "Coordinator", name))
    print("Parent tree (lqi is the link quality on the edge to the parent):")
    seen = set()

    def walk(name, depth):
        if name in seen:
            return
        seen.add(name)
        edge = parents.get(name)
        if edge is None:
            label = "(no parent in the tables)"
            flag = ""
        else:
            label = f"lqi {edge['lqi']}"
            flag = "  <- weak" if edge["lqi"] and edge["lqi"] < WEAK_LQI else ""
        kind = {"Coordinator": "coordinator", "Router": "router",
                "EndDevice": "end device"}.get(devices[name]["type"], devices[name]["type"])
        seen_age = age(devices[name]["last_seen"])
        # The coordinator has no last_seen of its own - it is the receiver.
        age_text = "" if seen_age is None else f", heard {human_age(seen_age)} ago"
        print(f"  {'    ' * depth}{name}  [{kind}, {label}{age_text}]{flag}")
        for child in children.get(name, []):
            walk(child, depth + 1)

    for root in order:
        walk(root, 0)

    orphans = [name for name in devices if name not in seen]
    for name in sorted(orphans):
        print(f"  {name}  [unreached by the tree]")
    print()


def print_device_detail(mesh, wanted):
    """One device's edges in both directions - which is what a placement change
    needs: can this device hear the candidate router, and can the router hear it?
    A neighbour table only records what its owner hears, so both sides are read.
    """
    devices = mesh["devices"]
    parents = mesh["parents"]
    relationships = {REL_PARENT: "their parent", REL_CHILD: "their child",
                     REL_SIBLING: "sibling"}
    for name in wanted:
        if name not in devices:
            print(f"No device called {name} in the map.")
            print()
            continue
        info = devices[name]
        edge = parents.get(name)
        parent_text = f"{edge['parent']} at lqi {edge['lqi']}" if edge else "unknown"
        print(f"{name} ({info['type']}, {info['model']}): parent {parent_text}")
        print(f"  hears ({len(info['links'])} neighbours):")
        for neighbour, link in sorted(info["links"].items(), key=lambda kv: -kv[1]["lqi"]):
            relation = relationships.get(link["relationship"], str(link["relationship"]))
            print(f"    {link['lqi']:4}  {neighbour}  ({relation})")
        listeners = [(other, other_info["links"][name])
                     for other, other_info in devices.items()
                     if name in other_info["links"]]
        print(f"  heard by ({len(listeners)}):")
        for other, link in sorted(listeners, key=lambda kv: -kv[1]["lqi"]):
            relation = relationships.get(link["relationship"], str(link["relationship"]))
            print(f"    {link['lqi']:4}  {other}  ({relation})")
        print()


def print_devices(mesh):
    devices = mesh["devices"]
    parents = mesh["parents"]
    no_route_table = 0
    print(f"{'device':22} {'type':10} {'parent':22} {'lqi':>4} {'best':>5} {'worst':>6} {'links':>5} "
          f"{'seen':>6} {'model':16}")
    for name in sorted(devices):
        info = devices[name]
        edge = parents.get(name)
        links = {n: l["lqi"] for n, l in info["links"].items()}
        best = max(links.values()) if links else 0
        worst = min(links.values()) if links else 0
        # `failed` lists the fields zigbee2mqtt could not read from the device.
        # routingTable is normal to lose on an Ember coordinator, so it is not
        # flagged per device - only counted for the summary line below.
        failed = [field for field in info["failed"] if field != "routingTable"]
        if "routingTable" in info["failed"]:
            no_route_table += 1
        flags = []
        if info.get("available") == "offline":
            flags.append("OFFLINE - not answering zigbee2mqtt")
        if failed:
            flags.append("no reading of: " + ", ".join(failed))
        label = name + (" *" if flags else "")
        edge_lqi = edge["lqi"] if edge and edge["lqi"] else 0
        print(f"{label:22} {info['type']:10} {(edge['parent'] if edge else '-'):22} "
              f"{(edge_lqi if edge_lqi else '-'):>4} {best:5} {worst:6} {len(info['links']):5} "
              f"{human_age(age(info['last_seen'])):>6} {info['model']:16}")
        for note in flags:
            print(f"{'':22}   ! {note}")
    if no_route_table:
        print(f"  {no_route_table} routers returned no routing table, which is normal on an Ember coordinator.")
    # `seen` is zigbee2mqtt's last-seen record. With the last_seen feature
    # disabled it reflects the last time zigbee2mqtt heard from or questioned
    # the device, so it is a rough liveness hint, not a report interval.
    print("  seen = zigbee2mqtt's last-seen record (rough; verify liveness with OFFLINE flags)")
    print()


def print_weak(mesh):
    weak = mesh["weak"]
    print(f"Weak links (below lqi {WEAK_LQI}; the arrow is the weaker direction, "
          f"'reverse' is the other one): {len(weak)}")
    for edge in weak[:40]:
        # A reverse of 0 means the other direction has no recent reading, which
        # is the quiet case rather than a value worth printing.
        reverse = f"   (reverse {edge['reverse']})" if edge.get("reverse") else ""
        print(f"  {edge['lqi']:4}  {edge['from']} -> {edge['to']}{reverse}")
    if not weak:
        print("  none")
    if mesh.get("quiet_pairs"):
        print(f"  ({mesh['quiet_pairs']} further pairs are recorded by a table but not heard at all, "
              f"lqi 0 - normal for devices that have moved or gone)")
    print()


def print_failures(commands, failures, seconds):
    print(f"Commands in the last {seconds}s (unanswered = not acknowledged in time):")
    print(f"{'device':22} {'commands':>8} {'unanswered':>11} {'miss rate':>10}")
    for name in sorted(commands, key=lambda n: -failures.get(n, 0)):
        sent = commands[name]
        missed = failures.get(name, 0)
        print(f"{name:22} {sent:8} {missed:11} {100 * missed / max(sent, 1):9.0f}%")
    print("  Normal on this mesh is 0-7%. 20%+ means the device is not answering reliably;")
    print("  100% means it is gone (a mains module that has stopped needs a power cycle).")
    print()


def render(mesh, args):
    """Print the whole report: header, parent tree, device table, weak links."""
    value_devices = mesh["devices"]
    routers = sum(1 for info in value_devices.values() if info["type"] == "Router")
    ends = sum(1 for info in value_devices.values() if info["type"] == "EndDevice")
    print(f"Zigbee mesh at {time.strftime('%Y-%m-%d %H:%M:%S')}: "
          f"{len(value_devices)} devices ({routers} routers, {ends} end devices), "
          f"broker {args.broker}:{args.port}")
    print()
    print_tree(mesh)
    print_devices(mesh)
    print_weak(mesh)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Show the Zigbee mesh as the coordinator sees it (read-only).")
    parser.add_argument("--broker", default=None, help="MQTT broker (default: from zigbee-config.json, else localhost)")
    parser.add_argument("--port", type=int, default=None, help="MQTT port (default 1883)")
    parser.add_argument("--username", default=None, help="MQTT username (default: from zigbee-config.json)")
    parser.add_argument("--password", default=None, help="MQTT password (default: from zigbee-config.json)")
    parser.add_argument("--tls", action="store_true", default=None, help="Connect with TLS")
    parser.add_argument("--config", default=None, help="Config file (default zigbee-config.json beside this script)")
    parser.add_argument("--timeout", type=int, default=240, help="Seconds to wait for the map (default 240)")
    parser.add_argument("--failures", nargs="?", const=60, type=int, default=None,
                        metavar="SECONDS", help="Also count unanswered relay commands (default 60s)")
    parser.add_argument("--json", action="store_true", help="Print the parsed mesh as JSON")
    parser.add_argument("--device", action="append", default=[], metavar="NAME",
                        help="Also show one device's links in both directions (repeatable)")
    parser.add_argument("--from", dest="from_file", default=None, metavar="FILE",
                        help="Render a previously saved response instead of asking the broker")
    args = parser.parse_args(argv)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = args.config or os.path.join(script_dir, "zigbee-config.json")
    config = load_config(config_path)
    if args.broker is None:
        args.broker = config.get("broker", "localhost")
    if args.port is None:
        args.port = int(config.get("port", 1883))

    if args.from_file:
        value, availability = load_saved_map(args.from_file)
    else:
        value, availability = request_network_map(args, config)
    mesh = parse_map(value, availability)

    if args.json:
        print(json.dumps(mesh, indent=2, default=str))
        return 0

    # Render the map first, then the detail, then watch: the live failure watch
    # reads better after the mesh it belongs to, and it is the slow part anyway.
    render(mesh, args)
    if args.device:
        print_device_detail(mesh, args.device)
    if args.failures:
        commands, failures = watch_failures(args, config, args.failures)
        print_failures(commands, failures, args.failures)
    return 0


if __name__ == "__main__":
    sys.exit(main())
