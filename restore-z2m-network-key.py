#!/usr/bin/env python3
"""
restore-z2m-network-key.py — put a lost Zigbee2MQTT network key back.

Why this exists
---------------
`rbr-setup.sh` used to write /opt/zigbee2mqtt/data/configuration.yaml from
scratch unconditionally, with `network_key: GENERATE` and `pan_id: GENERATE`.
On a re-run that silently replaced the identity of a working Zigbee network:
Zigbee2MQTT would only notice at its next start, when it generated a new key and
network and every paired relay and thermometer dropped off.

The installer now keeps an existing configuration.yaml, so this should not
recur. This tool is for the boxes that were caught by the old behaviour.

Where the key comes from
------------------------
Zigbee2MQTT writes data/coordinator_backup.json on startup. It is a copy of the
coordinator's own state and contains the network key and PAN ID, so the original
network is recoverable from it as long as the file predates the damage. The
script searches the whole document, so it does not care which of the several
shapes Zigbee2MQTT has used for it over the years (a list of 16 integers, a hex
string, a list of hex strings, or any of those nested inside objects).

Safety
------
* Nothing is written until a usable key has been found.
* configuration.yaml is copied to configuration.yaml.bak-<timestamp> first.
* The file is rewritten in place with open(..., "w") rather than replaced, so its
  ownership and mode stay with the zigbee2mqtt user — which is what keeps
  Zigbee2MQTT able to read it.
* Re-running is harmless: it writes the same values again.

Usage
-----
    sudo python3 restore-z2m-network-key.py                  # /opt/zigbee2mqtt/data
    sudo python3 restore-z2m-network-key.py --data DIR
    sudo python3 restore-z2m-network-key.py --dry-run        # show, change nothing

Then restart Zigbee2MQTT and confirm the devices are still known to it — a
correct key means they are not re-interviewed:

    sudo systemctl restart zigbee2mqtt
    sudo journalctl -u zigbee2mqtt -n 40 --no-pager
"""

import argparse
import glob
import json
import os
import re
import shutil
import sys
import time

DEFAULT_DATA = "/opt/zigbee2mqtt/data"


def to_key(value, _depth=0):
    """Return a 16-byte key as a list of ints, or None.

    Accepts the shapes Zigbee2MQTT has used: a list of 16 ints, a list of 16 hex
    strings, a 32-character hex string (with or without 0x), or any of those
    wrapped in one or more objects with a `key`/`network_key` member.
    """
    if _depth > 4:
        return None
    if isinstance(value, dict):
        for name in ("key", "network_key", "networkKey"):
            if name in value:
                return to_key(value[name], _depth + 1)
        return None
    if isinstance(value, str):
        text = value[2:] if value.lower().startswith("0x") else value
        if re.fullmatch(r"[0-9a-fA-F]{32}", text):
            return [int(text[i:i + 2], 16) for i in range(0, 32, 2)]
        return None
    if isinstance(value, list) and len(value) == 16:
        try:
            return [int(item, 16) if isinstance(item, str) else int(item) for item in value]
        except (TypeError, ValueError):
            return None
    return None


def find(doc, wanted, depth=0):
    """Depth-first search for a mapping entry whose name matches `wanted`.

    Names are compared with underscores stripped, so network_key, networkKey and
    NETWORK-KEY are the same name. `wanted` is already in that normalised form.
    A `networkkey` hit must be a usable key; a `panid` hit is returned as-is.
    """
    if depth > 8:
        return None
    if isinstance(doc, dict):
        for name, value in doc.items():
            if str(name).lower().replace("_", "").replace("-", "") == wanted:
                found = to_key(value) if wanted == "networkkey" else value
                if found:
                    return found
            found = find(value, wanted, depth + 1)
            if found:
                return found
    elif isinstance(doc, list):
        for value in doc:
            found = find(value, wanted, depth + 1)
            if found:
                return found
    return None


def load_candidates(data_dir):
    """Every JSON file in the data directory, the coordinator backup first.

    The coordinator backup is the intended source; the others are searched so a
    version that keeps the key elsewhere is still recoverable. Files named
    coordinator_backup.json are tried before the rest.
    """
    paths = sorted(glob.glob(os.path.join(data_dir, "*.json")),
                   key=lambda p: ("coordinator_backup" not in os.path.basename(p), p))
    for path in paths:
        try:
            with open(path, encoding="utf-8") as handle:
                yield path, json.load(handle)
        except (OSError, ValueError):
            continue


def find_values(data_dir):
    """Return (key, pan_id, source_path) from the data directory, or (None, None, None)."""
    key = pan = source = None
    for path, doc in load_candidates(data_dir):
        if key is None:
            key = find(doc, "networkkey")
            if key:
                source = path
        if pan is None:
            pan = find(doc, "panid")
        if key and pan:
            break
    return key, pan, source


def as_yaml(key, pan):
    """The two YAML values, or None for one we do not have."""
    key_text = "[" + ", ".join(str(byte) for byte in key) + "]" if key else None
    if pan is None:
        pan_text = None
    elif isinstance(pan, bool):
        pan_text = None
    elif isinstance(pan, str):
        try:
            pan_text = str(int(pan, 16))
        except ValueError:
            pan_text = None
    else:
        try:
            pan_text = str(int(pan))
        except (TypeError, ValueError):
            pan_text = None
    return key_text, pan_text


def replace_field(text, field, value):
    """Replace `field: ...` in place, keeping its indentation. Returns (text, matched)."""
    pattern = re.compile(r"^(\s*)" + re.escape(field) + r"\s*:.*$", re.MULTILINE)
    new_text, count = pattern.subn(lambda m: m.group(1) + field + ": " + value, text, count=1)
    return new_text, bool(count)


def main():
    parser = argparse.ArgumentParser(description="Restore a Zigbee2MQTT network key from coordinator_backup.json.")
    parser.add_argument("--data", default=DEFAULT_DATA, help="Zigbee2MQTT data directory (default %s)" % DEFAULT_DATA)
    parser.add_argument("--dry-run", action="store_true", help="show what would change, write nothing")
    args = parser.parse_args()

    data_dir = args.data
    config_path = os.path.join(data_dir, "configuration.yaml")
    if not os.path.isdir(data_dir):
        sys.exit("no such directory: %s" % data_dir)
    if not os.path.isfile(config_path):
        sys.exit("no configuration.yaml in %s" % data_dir)

    key, pan, source = find_values(data_dir)
    print("network key : %s" % ("found in " + os.path.basename(source) if key else "NOT FOUND"))
    print("pan_id      : %s" % (pan if pan is not None else "NOT FOUND"))
    if not key:
        sys.exit("Stopping — no network key could be found. configuration.yaml untouched.\n"
                 "If a backup of data/ exists elsewhere, coordinator_backup.json is the file to take it from.")

    key_text, pan_text = as_yaml(key, pan)
    if pan_text is None:
        print("warning     : no usable pan_id found — restoring the key alone. If the network still\n"
              "              does not come back, the PAN ID has to be restored as well.")

    with open(config_path, encoding="utf-8") as handle:
        text = handle.read()

    changed = {}
    for field, value in (("network_key", key_text), ("pan_id", pan_text)):
        if value is None:
            continue
        text, matched = replace_field(text, field, value)
        changed[field] = "replaced" if matched else "NO LINE FOUND"
        print("%-11s : %s" % (field, changed[field]))

    if "NO LINE FOUND" in changed.values():
        sys.exit("Stopping — configuration.yaml has no line to put that value on. Untouched.\n"
                 "Add it by hand under the advanced: block:\n  network_key: %s\n  pan_id: %s"
                 % (key_text, pan_text))

    if args.dry_run:
        print("\n--dry-run: would write the above to %s" % config_path)
        return

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup_path = "%s.bak-%s" % (config_path, stamp)
    shutil.copy2(config_path, backup_path)
    print("\nbackup      : %s" % backup_path)

    # "w" truncates the existing file, so its owner and mode stay as they are —
    # which is what keeps Zigbee2MQTT able to read it.
    with open(config_path, "w", encoding="utf-8") as handle:
        handle.write(text)
    print("written     : %s" % config_path)
    print("\nNow restart Zigbee2MQTT and confirm the devices are still known to it:")
    print("  sudo systemctl restart zigbee2mqtt")
    print("  sudo journalctl -u zigbee2mqtt -n 40 --no-pager")


if __name__ == "__main__":
    main()
