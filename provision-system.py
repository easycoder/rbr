#!/usr/bin/env python3
"""
provision-system.py — create or repair a system's entry in rbr-users.json.

Runs on the web host, as the account that owns rbr-users.json. Nothing else on
the box writes that file.

Why this exists
---------------
`auth.php` has two ends: `/register` creates a pending record with a six-digit
password, and `/verify` marks it verified and mints the token that
credentials.php accepts. Between them they look like the whole story, and they
are not: credentials.php also requires a `credentials` block on the entry (the
broker account the UI connects with), and *no endpoint creates it*. A system
registered and verified through the UI alone therefore pairs successfully and
then sits in demo mode, because its broker credentials request comes back 401.
There is nothing in the browser or the controller to say why.

This tool makes one command the whole job: it leaves the entry complete —
password, verified, token, credentials — or reports that it already is.
Defaults for the broker come from the host settings file, which is what
credentials.php itself falls back to, so the two cannot drift apart.

    ./provision-system.py --list
    ./provision-system.py --mac 00:e0:27:5b:31:40 --email someone@example.com
    ./provision-system.py --mac ... --email ... --write

Without --write it is a dry run: it says exactly what it would change and
touches nothing. Secrets are never printed: the one exception is a newly
generated system password, which exists nowhere else until it is written down.
"""

import argparse
import json
import os
import re
import secrets
import shutil
import socket
import ssl
import struct
import sys
import time

MAC_PATTERN = re.compile(r"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def say(message=""):
    print(message, flush=True)


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else default
    except (OSError, ValueError):
        return default


def write_json_owner_preserved(path, data):
    """Write JSON atomically, keeping the file's mode and owner.

    Atomic because this file gates every system's pairing: a half-written one
    locks every customer out, and the failure would look like wrong passwords.
    """
    stat = os.stat(path)
    directory = os.path.dirname(os.path.abspath(path))
    temp = os.path.join(directory, ".%s.tmp-%d" % (os.path.basename(path), os.getpid()))
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temp, stat.st_mode & 0o777)
    try:
        os.chown(temp, stat.st_uid, stat.st_gid)
    except OSError:
        pass  # not root, and the file is already ours
    os.replace(temp, path)


def mqtt_auth_check(host, port, username, password, timeout=10):
    """True if the broker accepts these credentials, False if it refuses.

    A minimal MQTT 3.1.1 CONNECT/CONNACK over TLS, so the check needs no
    client library — the host may not have one, and installing packages to
    verify a password is a poor trade. Returns None if the broker cannot be
    reached at all, which is a different problem from a refused login.
    """
    def field(text):
        raw = text.encode("utf-8")
        return struct.pack("!H", len(raw)) + raw

    # Payload order is fixed: client identifier first (empty is legal for 3.1.1
    # with a clean session), then username, then password. Omitting the client
    # identifier makes the broker drop the connection without a CONNACK, which
    # is indistinguishable from a wrong password unless it is built correctly.
    payload = field("MQTT") + bytes([4]) + bytes([0xC2])
    payload += struct.pack("!H", 60) + field("") + field(username) + field(password)
    remaining = len(payload)
    encoded = b""
    while True:
        byte, remaining = remaining % 128, remaining // 128
        encoded += bytes([byte | (0x80 if remaining else 0)])
        if not remaining:
            break
    packet = bytes([0x10]) + encoded + payload

    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=timeout) as raw:
            with context.wrap_socket(raw, server_hostname=host) as secure:
                secure.sendall(packet)
                reply = secure.recv(4)
    except OSError:
        return None
    if len(reply) < 4 or reply[0] != 0x20:
        return None
    return reply[3] == 0x00


def describe(system):
    return "verified" if system.get("verified") else "pending"


def main():
    parser = argparse.ArgumentParser(
        description="Create or repair a system's entry in rbr-users.json.")
    parser.add_argument("--users-file", default="/home/rbrheating/rbr-users.json")
    parser.add_argument("--host-file", default=None,
                        help="host settings (default: <users dir>/<host>.txt)")
    parser.add_argument("--host", default="rbrheating.com",
                        help="host whose settings file supplies broker defaults")
    parser.add_argument("--mac", help="system MAC, xx:xx:xx:xx:xx:xx")
    parser.add_argument("--email", help="owner's email address")
    parser.add_argument("--broker", help="override: MQTT host")
    parser.add_argument("--port", type=int, help="override: websocket port served to the UI")
    parser.add_argument("--mqtt-port", type=int, default=8883,
                        help="broker port used for the login test (not the websocket "
                             "port the UI is served: %(default)s)")
    parser.add_argument("--mqtt-username", help="override: broker username")
    parser.add_argument("--mqtt-password-file",
                        help="file holding the broker password (keeps it off the command line)")
    parser.add_argument("--rotate-token", action="store_true",
                        help="issue a new token (unpairs devices already holding the old one)")
    parser.add_argument("--force", action="store_true",
                        help="allow changing the email or password of a verified system")
    parser.add_argument("--no-broker-check", action="store_true",
                        help="skip the login test against the broker")
    parser.add_argument("--list", action="store_true", help="show provisioned systems")
    parser.add_argument("--write", action="store_true",
                        help="apply the changes (without this it is a dry run)")
    args = parser.parse_args()

    users_file = os.path.abspath(args.users_file)
    if not os.path.isfile(users_file):
        say("No %s — is this the web host?" % users_file)
        return 2
    host_file = args.host_file or os.path.join(
        os.path.dirname(users_file), "%s.txt" % args.host)
    users = load_json(users_file, {})
    host_settings = load_json(host_file, {})

    if args.list:
        if not users:
            say("No systems provisioned.")
            return 0
        say("%-20s %-28s %-10s %-12s %s" % ("MAC", "EMAIL", "STATE", "CREDENTIALS", "TOKEN"))
        for mac, system in sorted(users.items()):
            say("%-20s %-28s %-10s %-12s %s" % (
                mac, system.get("email", ""), describe(system),
                "yes" if (system.get("credentials") or {}).get("username") else "MISSING",
                "yes" if system.get("token") else "MISSING"))
        return 0

    if not args.mac or not args.email:
        say("Need --mac and --email (or --list).")
        return 2

    mac = args.mac.strip().lower()
    email = args.email.strip().lower()
    if not MAC_PATTERN.match(mac):
        say("Bad MAC %r — expected xx:xx:xx:xx:xx:xx, colons included, any case." % args.mac)
        return 2
    if not EMAIL_PATTERN.match(email):
        say("Bad email %r." % args.email)
        return 2

    # Broker defaults: the per-system block, then the host settings, then the
    # command line — the same precedence credentials.php applies when serving.
    existing = users.get(mac)
    credentials = dict(existing.get("credentials", {})) if existing else {}
    for key, value in (("broker", args.broker or host_settings.get("broker")),
                       ("port", args.port or host_settings.get("port")),
                       ("username", args.mqtt_username or host_settings.get("username"))):
        if value not in (None, ""):
            credentials.setdefault(key, value)
    if args.mqtt_password_file:
        with open(args.mqtt_password_file, encoding="utf-8") as handle:
            credentials["password"] = handle.read().strip()
    elif not credentials.get("password") and host_settings.get("password"):
        credentials["password"] = host_settings["password"]

    changes, problems = [], []
    system = dict(existing) if existing else {}

    if existing and existing.get("verified") and existing.get("email") != email:
        if not args.force:
            problems.append("already verified with email %r; --force to change it"
                            % existing.get("email"))
    elif system.get("email") != email:
        system["email"] = email
        changes.append("email -> %s" % email)

    if not system.get("created"):
        system["created"] = int(time.time())
        changes.append("created timestamp")

    new_password = None
    if not system.get("password"):
        new_password = "%06d" % secrets.randbelow(1000000)
        if args.write:
            system["password"] = new_password
            changes.append("system password: generated")
        else:
            changes.append("system password: generated")

    if not system.get("verified"):
        system["verified"] = True
        changes.append("verified")

    if args.rotate_token or not system.get("token"):
        if args.write:
            system["token"] = secrets.token_hex(24)
        changes.append("token: %s" % ("rotated" if args.rotate_token else "issued"))

    if not credentials.get("username") or not credentials.get("password"):
        problems.append("no broker username/password available — pass "
                        "--mqtt-password-file or check %s" % host_file)
    elif system.get("credentials") != credentials:
        system["credentials"] = credentials
        changes.append("broker credentials -> %s@%s:%s (password %d chars)" % (
            credentials.get("username"), credentials.get("broker"),
            credentials.get("port"), len(credentials.get("password", ""))))

    say("System %s" % mac)
    say("  state: %s" % (describe(existing) if existing else "not provisioned"))
    prefix = "" if args.write else "would "
    for change in changes:
        say("  %schange: %s" % (prefix, change))
    if not changes and not problems:
        say("  already complete — nothing to change")
    for problem in problems:
        say("  PROBLEM: %s" % problem)

    if problems:
        say("Not writing anything.")
        return 1
    if not changes:
        return 0

    if not args.no_broker_check:
        result = mqtt_auth_check(credentials.get("broker") or host_settings.get("broker"),
                                 args.mqtt_port,
                                 credentials["username"], credentials["password"])
        if result is True:
            say("  broker: accepts these credentials")
        elif result is False:
            say("  broker: REFUSED them — the UI would pair and then sit in demo mode")
            say("Not writing anything.")
            return 1
        else:
            say("  broker: unreachable, so the login could not be tested")

    if not args.write:
        say()
        say("Dry run — nothing written. Add --write to apply.")
        return 0

    backup = "%s.bak-%s" % (users_file, time.strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(users_file, backup)
    users[mac] = system
    write_json_owner_preserved(users_file, users)

    # Re-read rather than assume: this file is the only thing standing between
    # a customer and a working system, so prove it is still valid JSON.
    check = load_json(users_file, None)
    if not isinstance(check, dict) or mac not in check:
        say("  WROTE BUT COULD NOT READ IT BACK — restore %s" % backup)
        return 1
    say()
    say("Written. Previous file kept as %s" % os.path.basename(backup))
    if new_password:
        say()
        say("  System password: %s" % new_password)
        say("  This is shown once and stored nowhere the owner can reach — it is "
            "not in ~/rbr/credentials,")
        say("  which holds the MQTT password instead. /recover with this MAC and "
            "email issues a new one.")
    say("Give the owner: MAC %s%s" % (mac, " and the password above" if new_password else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
