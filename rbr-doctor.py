#!/usr/bin/env python3
"""
rbr-doctor.py — read-only health report for an RBR controller box.

Run this on the controller when the system misbehaves: the UI loads but stays
empty, rooms stop updating, or a service will not stay up. It gathers the
running state of every RBR service, the controller's own journal, the state
files, the network path to the broker, and — the decisive test — a real MQTT
round-trip that asks the controller for its map and waits for the reply.

    sudo ./rbr-doctor.py > rbr-doctor.txt      # full report, journal included
    ./rbr-doctor.py > rbr-doctor.txt           # same, but journal reads may be refused
    sudo ./rbr-doctor.py --no-probe            # skip the MQTT round-trip
    ./rbr-doctor.py --json > rbr-doctor.json   # machine-readable

Nothing here writes to the system, restarts anything or changes a setting. The
only side effect is the round-trip probe: it registers a throwaway UI sender
("MAC/doctor-<pid>") with the controller, which expires after 100 seconds.

Exit code: 0 when nothing failed, 1 when at least one [FAIL] was reported.
Warnings do not affect the exit code.

It exists because the failure that matters most — a controller process that is
"active (running)" but has lost its MQTT session, or connected without ever
entering its main loop — looks healthy to systemd and to the watchdog. The UI
then sits on "Reconnecting..." with a correctly populated console and no error
anywhere, and there is nothing to read. This tool is meant to be the thing you
run first, and the file you send back.
"""

import argparse
import datetime
import glob
import grp
import json
import os
import platform
import re
import shutil
import socket
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request

VERSION_URL = "https://rbrheating.com/heat/version"
BROKER_PORT = 1883          # the port the controller hardcodes in controller.allspeak
BROKER_WS_PORT = 443        # the port the PWA uses for MQTT over WebSocket
Z2M_HTTP = "http://127.0.0.1:8080/"
BRIDGE_HEALTH = "http://127.0.0.1:8889/health"
BRIDGE_DEVICES = "http://127.0.0.1:8889/devices"

# Unit names as installed by rbr-setup.sh (rbr-watchdog.sh probes the same set).
# The aliases in the second column are older names still found on boxes that
# have not been through the current installer; either name counts.
SERVICES = [
    ("controller", ("rbr-controller",), "the AllSpeak controller"),
    ("mosquitto", (), "the local MQTT broker"),
    ("zigbee2mqtt", (), "the Zigbee coordinator daemon"),
    ("rbr-zigbee-bridge", ("zigbee-bridge",), "the controller's Zigbee HTTP bridge"),
]

TIMERS = [
    ("rbr-updater.timer", "hourly code updates — without it the box stays on its install release"),
    ("rbr-watchdog.timer", "15-minute service and heating watchdog"),
    ("rbr-backup.timer", "monthly controller + Zigbee backup"),
    ("rbr-journal-export.timer", "daily journal export and email"),
]

lines = []      # (level, text) where level is section|ok|warn|fail|note
facts = {}
hints = []


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------

def say(level, text):
    lines.append((level, text))


def section(title):
    lines.append(("section", title))


def hint(text):
    if text not in hints:
        hints.append(text)


def run(cmd, timeout=15):
    """Run a command and return (returncode, stdout, stderr). Never raises."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=timeout)
        return result.returncode, (result.stdout or "").strip(), (result.stderr or "").strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, "", str(exc)


def read(path, limit=1000000):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read(limit)
    except OSError:
        return ""


def human_age(seconds):
    """A duration a person can read: 42 s, 7 min, 2 h 15 min, 3 d 4 h."""
    if seconds is None:
        return "unknown"
    seconds = max(0, int(seconds))
    if seconds < 120:
        return "%d s" % seconds
    if seconds < 7200:
        return "%d min" % (seconds // 60)
    if seconds < 172800:
        hours, minutes = seconds // 3600, (seconds % 3600) // 60
        return "%d h %d min" % (hours, minutes) if minutes else "%d h" % hours
    days, hours = seconds // 86400, (seconds % 86400) // 3600
    return "%d d %d h" % (days, hours) if hours else "%d d" % days


def file_age(path):
    try:
        return max(0, time.time() - os.path.getmtime(path))
    except OSError:
        return None


def freshness_level(age, warn_after, fail_after):
    if age is None:
        return "note"
    if age > fail_after:
        return "fail"
    if age > warn_after:
        return "warn"
    return "ok"


def parse_show(text):
    """Turn `systemctl show` key=value output into a dictionary."""
    info = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            info[key.strip()] = value.strip()
    return info


def systemd_show(unit):
    props = ("LoadState,ActiveState,SubState,UnitFileState,NRestarts,"
             "ExecMainPID,MemoryCurrent,ExecMainStartTimestamp,"
             "ExecMainStartTimestampMonotonic,FragmentPath,User,"
             "WorkingDirectory,ExecStart,Result,ExecMainStatus,"
             "NextElapseUSecRealtime,NextElapseUSecMonotonic,LastTriggerUSec")
    _rc, out, _err = run(["systemctl", "show", unit,
                           "--property=" + props])
    return parse_show(out)


def boot_uptime():
    """/proc/uptime in seconds, or None."""
    text = read("/proc/uptime").split()
    try:
        return float(text[0])
    except (IndexError, ValueError):
        return None


def service_uptime(info):
    """Seconds the unit's current main process has been running."""
    mono = info.get("ExecMainStartTimestampMonotonic", "0")
    try:
        mono_seconds = float(mono) / 1e6
    except ValueError:
        return None
    uptime = boot_uptime()
    if uptime is None or mono_seconds <= 0:
        return None
    return max(0, uptime - mono_seconds)


def human_bytes(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "unknown"
    if number <= 0 or number > 1e15:      # systemd reports a sentinel for "not set"
        return "unknown"
    for unit in ("B", "KB", "MB", "GB"):
        if number < 1024:
            return "%.0f %s" % (number, unit)
        number /= 1024
    return "%.1f TB" % number


def usec_time(value):
    """systemd's NextElapseUSecRealtime / LastTriggerUSec as local text."""
    try:
        seconds = float(value) / 1e6
    except (TypeError, ValueError):
        return ""
    if seconds <= 0:
        return ""
    try:
        return datetime.datetime.fromtimestamp(seconds).strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, OverflowError, ValueError):
        return ""


def user_groups():
    names = []
    try:
        names = [grp.getgrgid(gid).gr_name for gid in os.getgroups()]
    except (ImportError, KeyError):
        pass
    return names


def journal_read(args, what="the journal"):
    """Return (text, note) for `journalctl <args>`. Falls back to sudo -n."""
    command = ["journalctl"] + args
    _rc, out, err = run(command, timeout=20)
    bare = out.strip()
    if bare and bare != "-- No entries --":
        return bare, ""
    if bare == "-- No entries --" and "not seeing messages" not in err:
        return "", "no journal entries for %s" % what

    if os.geteuid() != 0:
        _rc2, out2, err2 = run(["sudo", "-n"] + command, timeout=20)
        if out2.strip() and out2.strip() != "-- No entries --":
            return out2.strip(), "read with sudo -n"
        if "password is required" in err2 or "a password is required" in err2:
            return "", ("not readable as this user and sudo wants a password — "
                        "re-run the doctor with sudo")
        if out2.strip() == "-- No entries --":
            return "", "no journal entries for %s" % what

    if "not seeing messages" in err:
        return "", ("not readable as this user (not in systemd-journal or adm) — "
                    "re-run the doctor with sudo")
    return "", err or "journal unavailable"


def journal_text(unit, count=250):
    """Return (text, note) for one unit's journal."""
    return journal_read(["-u", unit, "--no-pager", "-o", "short-iso",
                         "-n", str(count)], unit)


def http_get(url, timeout=6):
    """Return (status, body bytes) for any HTTP answer, or raise OSError."""
    request = urllib.request.Request(url, headers={"User-Agent": "rbr-doctor/1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.read(200000)


def tcp_check(host, port, timeout=5):
    try:
        with socket.create_connection((host, port), timeout=timeout) as probe:
            return True, probe.getpeername()[0]
    except OSError as exc:
        return False, str(exc)


# ---------------------------------------------------------------------------
# Installation directory, identity and versions
# ---------------------------------------------------------------------------

def dashboard_enabled(*commandlines):
    """True unless a controller command line carries --no-dashboard."""
    return not any("--no-dashboard" in (line or "") for line in commandlines)


def parse_established(text, port=1883):
    """Peer addresses of established TCP connections to `port` from `ss -tnp`."""
    peers = []
    for row in text.splitlines():
        if "ESTAB" not in row:
            continue
        parts = row.split()
        if len(parts) < 5:
            continue
        peer = parts[4]
        if peer.rsplit(":", 1)[-1] == str(port):
            peers.append(peer)
    return peers


def parse_failed_units(text):
    """Unit names from `systemctl --failed --no-legend --plain`."""
    units = []
    for row in text.splitlines():
        row = row.strip().lstrip("*\u25cf ").strip()
        if not row:
            continue
        name = row.split()[0]
        if re.match(r"^[\w@:.-]+\.(service|socket|timer|mount|target)$", name):
            units.append(name)
    return units


def inode_use_percent(text):
    """The IUse% from the last line of `df -Pi` output, or None."""
    rows = [row for row in text.splitlines() if row.strip()]
    if len(rows) < 2:
        return None
    for token in rows[-1].split():
        if token.endswith("%"):
            try:
                return int(token[:-1])
            except ValueError:
                return None
    return None


def wifi_signal(iface):
    """Signal in dBm for a wireless interface, or None."""
    for row in read("/proc/net/wireless").splitlines():
        if row.strip().startswith(iface + ":"):
            parts = row.replace(":", " ").split()
            try:
                return float(parts[3].rstrip("."))
            except (IndexError, ValueError):
                return None
    return None


def rbr_cron_entries():
    """Cron lines that launch the controller, from /etc and user crontabs."""
    entries = []
    for path in ["/etc/crontab"] + sorted(glob.glob("/etc/cron.d/*")):
        for row in read(path).splitlines():
            if row.strip().startswith("#"):
                continue
            if "allspeak" in row or "controller.allspeak" in row:
                entries.append("%s: %s" % (path, row.strip()))

    sudo_user = os.environ.get("SUDO_USER", "")
    users = []
    if os.geteuid() == 0:
        users.append("root")
        if sudo_user and sudo_user != "root":
            users.append(sudo_user)
    else:
        users.append(os.environ.get("USER") or os.environ.get("LOGNAME") or "")
    seen = set()
    for name in users:
        if not name or name in seen:
            continue
        seen.add(name)
        command = ["crontab", "-u", name, "-l"] if os.geteuid() == 0 else ["crontab", "-l"]
        rc, out, _err = run(command)
        if rc == 0:
            for row in out.splitlines():
                if row.strip().startswith("#"):
                    continue
                if "allspeak" in row:
                    entries.append("crontab %s: %s" % (name, row.strip()))
    return entries


def find_install_dir(explicit):
    if explicit:
        return os.path.abspath(os.path.expanduser(explicit))
    home = os.path.expanduser("~")
    candidates = [
        os.getcwd(),
        os.path.join(os.getcwd(), "rbr"),
        home,
        os.path.join(home, "rbr"),
    ]
    # Under sudo, HOME is root's; the controller usually lives in the invoking
    # user's home. Try that user before the historical service-user names.
    sudo_user = os.environ.get("SUDO_USER", "")
    if sudo_user and sudo_user != "root":
        user_home = os.path.join("/home", sudo_user)
        candidates += [user_home, os.path.join(user_home, "rbr")]
    for user in ("rbr", "linaro", "pi"):
        candidates.append(os.path.join("/home", user))
        candidates.append(os.path.join("/home", user, "rbr"))
    for candidate in candidates:
        if os.path.isfile(os.path.join(candidate, "controller.allspeak")):
            return os.path.abspath(candidate)
    return os.path.abspath(os.getcwd())


def find_allspeak(install_dir=""):
    """The allspeak binary the controller is likely to run, not just ours."""
    candidates = []
    homes = [os.path.expanduser("~")]
    sudo_user = os.environ.get("SUDO_USER", "")
    if sudo_user and sudo_user != "root":
        homes.append(os.path.join("/home", sudo_user))
    if install_dir:
        # Running as root directly leaves HOME=/root and SUDO_USER unset. The
        # controller's own directory is the reliable clue: its owner's home is
        # where its allspeak lives.
        homes.append(os.path.dirname(os.path.abspath(install_dir)))
        try:
            import pwd
            homes.append(pwd.getpwuid(os.stat(install_dir).st_uid).pw_dir)
        except (ImportError, KeyError, OSError):
            pass
    homes += ["/home/rbr", "/home/linaro", "/home/pi"]
    seen = set()
    for home in homes:
        if not home or home in seen:
            continue
        seen.add(home)
        candidates.append(os.path.join(home, ".local", "bin", "allspeak"))
    # A service unit may run `python3 ~/.local/bin/allspeak`, so the file can
    # be readable without being executable. Accept it and run it with the
    # interpreter; only `shutil.which` needs the execute bit.
    candidates.append(shutil.which("allspeak") or "")
    candidates += sorted(glob.glob("/home/*/.local/bin/allspeak"))
    candidates += ["/usr/local/bin/allspeak", "/usr/bin/allspeak"]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.R_OK):
            return candidate
    return ""


def default_interface():
    _rc, out, _err = run(["ip", "route", "show", "default"])
    match = re.search(r"\bdev\s+(\S+)", out)
    return match.group(1) if match else ""


def interface_mac(ifname):
    if not ifname:
        return ""
    return read("/sys/class/net/%s/address" % ifname).strip()


def read_override(path):
    return read(path).strip()


def check_identity(install_dir):
    section("IDENTITY")
    facts["install_dir"] = install_dir
    say("ok", "install directory: %s" % install_dir)
    if not os.path.isfile(os.path.join(install_dir, "controller.allspeak")):
        say("fail", "controller.allspeak is not in %s — run with --dir pointing "
                    "at the directory the controller runs from" % install_dir)
        hint("The doctor is looking in the wrong directory. Re-run it with "
             "--dir <controller directory>.")

    iface = default_interface()
    actual_mac = interface_mac(iface)
    facts["interface"] = iface
    facts["mac_actual"] = actual_mac
    if iface:
        say("ok", "default route on %s (%s)" % (iface, actual_mac or "no MAC"))
    else:
        say("warn", "no default route — this machine may be offline")
        hint("No default route: check the network cable/Wi-Fi before anything "
             "else; nothing RBR does can reach the broker without it.")

    override_path = os.path.join(install_dir, ".mac_override")
    home_override = os.path.join(os.path.expanduser("~"), ".mac_override")
    override = read_override(override_path)
    facts["mac_override"] = override
    if override:
        say("ok", ".mac_override: %s" % override)
        if actual_mac and override.lower() != actual_mac.lower():
            say("note", "the override differs from this host's own MAC (%s) — "
                        "expected only if the box is standing in for another"
                % actual_mac)
        if home_override != override_path and os.path.isfile(home_override):
            say("note", "a second .mac_override exists at %s" % home_override)
    elif os.path.isfile(home_override):
        say("warn", ".mac_override is in the home directory, not %s — the "
                    "controller reads it relative to its working directory"
            % install_dir)
        hint("The controller's MAC override is in the wrong place. Move it "
             "into the controller's working directory.")
    else:
        say("note", "no .mac_override — the system identity is this host's MAC "
                    "(%s)" % (actual_mac or "unavailable"))
    facts["mac"] = override or actual_mac

    creds_path = os.path.join(install_dir, "credentials")
    if os.path.isfile(creds_path):
        mode = os.stat(creds_path).st_mode
        facts["credentials"] = creds_path
        say("ok" if stat.S_IMODE(mode) <= 0o640 else "warn",
            "credentials present (%s%s)" %
            (creds_path, "" if stat.S_IMODE(mode) <= 0o640 else
             ", mode %o — should be 600" % stat.S_IMODE(mode)))
        if stat.S_IMODE(mode) & 0o004:
            hint("The MQTT credentials file is world-readable. Run "
                 "`chmod 600` on it.")
    else:
        facts["credentials"] = ""
        say("warn", "no credentials file in %s — the controller falls back to "
                    "https://rbrheating.com/credentials.php at every start, and "
                    "cannot start at all if that fetch fails" % install_dir)
        hint("No local credentials file: the controller depends on the cloud "
             "credentials script at every start. Restore ./credentials.")

    volatile = os.path.join(install_dir, "volatile-root")
    raw = read_override(volatile)
    facts["volatile_root"] = raw
    if raw:
        say("ok", "volatile data in %s" % raw)
        if not os.path.isdir(raw):
            say("fail", "volatile directory %s does not exist — the controller "
                        "cannot write its readings there" % raw)
            hint("The volatile directory is missing (often /run/rbr, a tmpfs "
                 "that is recreated at boot). Create it, or remove "
                 "volatile-root to use the install directory.")
        elif not os.access(raw, os.W_OK):
            say("warn", "volatile directory %s is not writable by this user" % raw)
    else:
        say("note", "no volatile-root file — readings are written into the "
                    "install directory")


def check_versions(install_dir):
    section("VERSIONS")
    installed = read(os.path.join(install_dir, ".version")).strip()
    release = read(os.path.join(install_dir, "version")).strip()
    facts["version_installed"] = installed
    facts["version_file"] = release
    if installed:
        say("ok", "installed release (.version): %s" % installed)
    else:
        say("warn", "no .version — this box was installed by hand or the "
                    "updater has never run, so it cannot tell whether a release "
                    "is newer")
        hint("No .version: the updater cannot compare releases. Re-run the "
             "installer or restore .version.")
    if release and release != installed:
        say("note", "version file on disk says %s (the updater writes .version "
                    "separately)" % release)

    binary = find_allspeak(install_dir)
    runtime = ""
    if binary:
        command = ([binary, "--version"] if os.access(binary, os.X_OK)
                   else [sys.executable, binary, "--version"])
        rc, out, err = run(command)
        if rc == 0:
            runtime = (out or err).splitlines()[0].strip() if (out or err) else ""
    facts["allspeak_installed"] = runtime
    facts["allspeak_binary"] = binary
    if runtime:
        say("ok", "installed AllSpeak runtime: %s" % runtime)
    elif binary:
        say("warn", "found %s but it did not answer --version: %s"
            % (binary, err or "no output"))
    else:
        say("warn", "allspeak not found on PATH or in the usual ~/.local/bin")

    try:
        _status, body = http_get(VERSION_URL, timeout=15)
        latest = body.decode("utf-8", "replace").strip()
        facts["version_latest"] = latest
        if installed and latest and latest != installed:
            say("warn", "latest release is %s, this box has %s — it is behind "
                        "the published build" % (latest, installed))
            hint("The box is on an older release than the site publishes. "
                 "Check rbr-updater.timer and its journal first: a missing "
                 "timer is the usual reason.")
        else:
            say("ok", "latest published release: %s" % latest)
    except (OSError, ValueError) as exc:
        facts["version_latest"] = ""
        say("warn", "cannot read %s: %s" % (VERSION_URL, exc))


# ---------------------------------------------------------------------------
# Services and timers
# ---------------------------------------------------------------------------

def check_services():
    section("SERVICES")
    for unit, aliases, purpose in SERVICES:
        info = systemd_show(unit)
        used = unit
        if info.get("LoadState") == "not-found":
            for alias in aliases:
                alt = systemd_show(alias)
                if alt.get("LoadState") != "not-found":
                    info, used = alt, alias
                    break
        facts.setdefault("services", {})[used] = info

        load = info.get("LoadState", "unknown")
        active = info.get("ActiveState", "unknown")
        sub = info.get("SubState", "")
        if load == "not-found":
            say("fail", "%s: unit not installed (%s)" % (used, purpose))
            hint("%s (%s) is not installed. Run the installer's service step; "
                 "do not hand-write the unit." % (used, purpose))
            continue

        uptime = service_uptime(info)
        detail = "%s — %s" % (active, sub) if sub else active
        if uptime is not None and active == "active":
            detail += ", up %s" % human_age(uptime)
        if active == "active":
            say("ok", "%s: %s" % (used, detail))
        else:
            say("fail", "%s: %s (%s)" % (used, detail, purpose))
            hint("%s is not running. Restart it and read its journal: "
                 "`sudo systemctl restart %s && sudo journalctl -u %s -n 60`."
                 % (used, used, used))

        enabled = info.get("UnitFileState", "")
        if enabled and enabled not in ("enabled", "enabled-runtime"):
            say("warn", "%s is %s — it will not come back after a reboot"
                % (used, enabled or "unknown"))
            hint("%s is not enabled at boot; the Sep-2026 outage was exactly "
                 "this after a power cut." % used)

        try:
            restarts = int(info.get("NRestarts", "0") or 0)
        except ValueError:
            restarts = 0
        if restarts:
            level = "warn" if restarts > 20 else "note"
            say(level, "%s has restarted %d time(s) since the unit was loaded"
                % (used, restarts))
            if restarts > 20:
                hint("%s has restarted %d times — look for a crash loop in its "
                     "journal rather than restarting it again."
                     % (used, restarts))

        memory = human_bytes(info.get("MemoryCurrent", ""))
        pid = info.get("ExecMainPID", "")
        if pid and pid != "0":
            say("note", "%s main PID %s, memory %s" % (used, pid, memory))
        if unit == "controller":
            facts["controller"] = info
            facts["controller_unit"] = used
            facts["controller_uptime"] = uptime
            say("note", "controller unit: %s" % (info.get("FragmentPath") or "unknown"))
            say("note", "run as %s in %s" %
                (info.get("User") or "root",
                 info.get("WorkingDirectory") or "unknown"))

    # Lightweight health probes, matching rbr-watchdog.sh. A process can be
    # "active" and still be wedged; these are the checks that notice.
    up, detail = tcp_check("127.0.0.1", 1883, timeout=3)
    say("ok" if up else "fail",
        "mosquitto listens on 127.0.0.1:1883" if up
        else "no TCP answer on 127.0.0.1:1883 (%s)" % detail)
    if not up:
        hint("Nothing is accepting MQTT connections locally. The controller "
             "cannot publish or receive; start mosquitto.")

    try:
        status, _body = http_get(Z2M_HTTP, timeout=3)
        say("ok", "zigbee2mqtt frontend answers on 127.0.0.1:8080 (HTTP %s)" % status)
    except (OSError, urllib.error.URLError) as exc:
        say("warn", "zigbee2mqtt frontend does not answer on 127.0.0.1:8080: %s" % exc)

    try:
        _status, body = http_get(BRIDGE_HEALTH, timeout=3)
        health = json.loads(body.decode("utf-8", "replace"))
        devices = health.get("devices")
        facts["bridge_devices"] = devices
        say("ok", "rbr-zigbee-bridge /health answers%s" %
            (", %s known device(s)" % devices if devices is not None else ""))
        failures = health.get("failures") or health.get("setFailures")
        if failures:
            if isinstance(failures, dict):
                rows, recent = [], 0

                def rank(item):
                    detail = item[1]
                    age = detail.get("age") if isinstance(detail, dict) else None
                    fresh = 1 if isinstance(age, (int, float)) and age <= 600 else 0
                    count = detail.get("count", 0) if isinstance(detail, dict) else 0
                    return (fresh, count)

                for name, detail in sorted(failures.items(), key=rank, reverse=True):
                    if isinstance(detail, dict):
                        age = detail.get("age")
                        if isinstance(age, (int, float)) and age <= 600:
                            recent += 1
                        rows.append("%s %s (last %s ago)"
                                    % (name, detail.get("count", "?"),
                                       human_age(age)))
                    else:
                        rows.append("%s %s" % (name, detail))
                say("warn" if recent else "note",
                    "the bridge reports %d device failure(s)%s: %s"
                    % (len(failures),
                       " (%d in the last 10 min)" % recent if recent else
                       " (none recent; counts are cumulative)",
                       "; ".join(rows[:6])))
                if recent:
                    hint("Relays have failed to acknowledge commands in the last "
                         "10 minutes. A wedged mains relay stays on the network "
                         "and looks healthy while ignoring commands — power-cycle "
                         "it before changing software.")
            else:
                say("warn", "the bridge reports device failures: %s" % failures)
    except (OSError, ValueError, urllib.error.URLError) as exc:
        say("fail", "rbr-zigbee-bridge /health does not answer on 127.0.0.1:8889: %s" % exc)
        hint("The Zigbee bridge is the controller's only route to the radios. "
             "Restart rbr-zigbee-bridge and check that the dongle is present.")


def check_timers():
    section("TIMERS")
    for unit, purpose in TIMERS:
        info = systemd_show(unit)
        facts.setdefault("timers", {})[unit] = info
        if info.get("LoadState") == "not-found":
            say("warn", "%s: not installed (%s)" % (unit, purpose))
            if unit == "rbr-updater.timer":
                hint("The updater timer is missing, so this box never takes a "
                     "new release. That alone explains a controller running "
                     "code weeks older than the published build.")
            else:
                hint("%s is missing (%s)." % (unit, purpose))
            continue

        active = info.get("ActiveState", "unknown")
        enabled = info.get("UnitFileState", "")
        if active == "active":
            say("ok", "%s: %s" % (unit, purpose))
        else:
            say("warn", "%s: %s (%s)" % (unit, active, purpose))
            hint("%s is not active, so %s does not happen." % (unit, purpose))
        if enabled and enabled not in ("enabled", "enabled-runtime", "static"):
            say("warn", "%s is %s — it will not start after a reboot"
                % (unit, enabled))

        next_at = usec_time(info.get("NextElapseUSecRealtime")
                            or info.get("NextElapseUSecMonotonic"))
        last_at = usec_time(info.get("LastTriggerUSec"))
        if next_at or last_at:
            say("note", "%s next: %s, last: %s"
                % (unit, next_at or "never", last_at or "never"))

    # The updater's own last result answers "why is this box on an old release?"
    updater = systemd_show("rbr-updater.service")
    if updater.get("LoadState") != "not-found":
        result = updater.get("Result", "")
        status = updater.get("ExecMainStatus", "")
        if result in ("", "success"):
            say("ok", "last updater run: %s" % ("success" if result else "not yet run"))
        else:
            say("warn", "last updater run: %s (exit status %s)"
                % (result, status or "unknown"))
            hint("The updater's last run failed (%s). That is why this box can "
                 "sit on an old release; read `journalctl -u rbr-updater`."
                 % result)

    _rc, out, _err = run(["systemctl", "list-timers", "--all", "--no-pager"])
    if out:
        facts["timers_list"] = out


# ---------------------------------------------------------------------------
# Journal and controller process
# ---------------------------------------------------------------------------

def analyse_controller_log(text):
    """Pull the facts that matter out of a controller journal.

    Kept free of system calls so the contract can be tested: the failure this
    exists to catch is a session that logs `Subscribed to topic` and then
    nothing — systemd calls that healthy, and the UI calls it "Reconnecting...".
    """
    rows = [row for row in text.splitlines() if row.strip()]
    last = {}
    starts = []
    systemd_starts = []
    exits = []

    def remember(key, index, value=None):
        last[key] = (index, value)

    for index, row in enumerate(rows):
        if "Started RBR Controller" in row or "Run Controller" in row:
            remember("start", index)
        if "Run Controller" in row:
            starts.append(row)
        if re.search(r"Started .*controller.*service", row, re.IGNORECASE):
            systemd_starts.append(row)
        if re.search(r"(Main process exited|Failed with result|Scheduled restart "
                     r"job|Stopping .*controller|Stopped .*controller|"
                     r"Killing .*controller|code=exited|status=\d+)",
                     row, re.IGNORECASE):
            exits.append(row)
        match = re.search(r"AllSpeak version (\S+)", row)
        if match:
            remember("runtime", index, match.group(1))
        match = re.search(r"MAC address (?:overridden to|is) (\S+)", row)
        if match:
            remember("mac", index, match.group(1))
        match = re.search(r"Subscribed to topic:\s*(\S+)", row)
        if match:
            remember("topic", index, match.group(1))
        if "Load the system map" in row:
            remember("map", index)
        match = re.search(r"Update applied: version (\S+) -> (\S+)", row)
        if match:
            remember("update", index, (match.group(1), match.group(2)))
        if "Compile error" in row or "Duplicate symbol" in row:
            remember("compile", index, row)
        if "Unable to load credentials" in row or "NoCredentials" in row:
            remember("nocreds", index, row)
        if re.search(r"\b(Traceback|Error:|ERROR|failed|failure)\b", row,
                     re.IGNORECASE):
            remember("error", index, row)

    result = {
        "rows": len(rows),
        "start_index": last.get("start", (None, None))[0],
        "topic": last.get("topic", (None, ""))[1],
        "topic_index": last.get("topic", (None, None))[0],
        "runtime": last.get("runtime", (None, ""))[1],
        "mac": last.get("mac", (None, ""))[1],
        "map_index": last.get("map", (None, None))[0],
        "update": last.get("update", (None, None))[1],
        "compile_error": last.get("compile", (None, None))[1],
        "credentials_error": last.get("nocreds", (None, None))[1],
        "error": last.get("error", (None, None))[1],
        "starts": len(starts),
        "start_lines": (systemd_starts or starts)[-4:],
        "exit_lines": exits[-6:],
        "findings": [],
    }

    def finding(level, text):
        result["findings"].append((level, text))

    if not rows:
        finding("note", "the controller journal is empty (or unreadable)")
        return result

    # A start marker with no map load after it is the "connected but silent"
    # session. `Load the system map` is the first thing Start does, so it is a
    # reliable witness that the MQTT connect handler actually ran.
    if result["topic_index"] is not None:
        if result["map_index"] is None or result["map_index"] < result["topic_index"]:
            finding("fail",
                    "the controller subscribed to the broker (%s) but never "
                    "reached its main loop: no 'Load the system map' after the "
                    "subscription. The UI will show 'Reconnecting...'."
                    % result["topic"])
            hint("The controller is connected to the broker but has not run its "
                 "start-up path. Restart it and watch: "
                 "`sudo systemctl restart controller && sudo journalctl -u "
                 "controller -f`. If the same session repeats, the code and the "
                 "runtime are mismatched, or map.json is unreadable.")
        else:
            finding("ok", "the controller reached its main loop after connecting")
    elif result["start_index"] is not None:
        finding("warn",
                "the controller started but the journal shows no MQTT "
                "subscription — it may not have connected at all")
        hint("The controller never logged a subscription. Check the broker "
             "address, DNS and the credentials file; the UI cannot reach a "
             "controller that is not subscribed.")

    if result["compile_error"]:
        finding("fail", "compiler error in the controller log: %s"
                % result["compile_error"])
        hint("The controller will not start while the code does not compile. "
             "Take the release again; do not edit the installed file.")
    if result["credentials_error"]:
        finding("fail", "the controller could not load credentials: %s"
                % result["credentials_error"])
        hint("The controller has no usable MQTT credentials. Restore "
             "./credentials or make credentials.php reachable.")
    if result["update"]:
        finding("note", "a new release was applied during the last session: "
                        "%s -> %s" % result["update"])

    # Keep the most recent error line, but do not treat "Heat logging disabled"
    # or "Event journal disabled" as a fault: they are optional features.
    if result["error"]:
        finding("warn", "most recent error-like line: %s" % result["error"])
    return result


def proc_start_epoch(pid):
    stat_text = read("/proc/%s/stat" % pid)
    if ")" not in stat_text:
        return None
    fields = stat_text.rsplit(")", 1)[1].split()
    try:
        ticks = int(fields[19])              # field 22 of /proc/pid/stat
    except (IndexError, ValueError):
        return None
    boot = None
    for row in read("/proc/stat").splitlines():
        if row.startswith("btime "):
            try:
                boot = int(row.split()[1])
            except (IndexError, ValueError):
                boot = None
    try:
        hz = os.sysconf("SC_CLK_TCK")
    except (ValueError, OSError):
        hz = 100
    if boot is None:
        return None
    return boot + ticks / float(hz)


def check_controller(install_dir):
    section("CONTROLLER")
    unit = facts.get("controller_unit", "controller")
    info = facts.get("controller") or systemd_show(unit)
    text, note = journal_text(unit, count=300)
    facts["controller_journal_note"] = note
    if note:
        say("note", "controller journal: %s" % note)
        if "sudo" in note:
            hint("The journal is not readable as this user — that is why "
                 "`journalctl` answers 'No entries' while `systemctl status` "
                 "still shows lines. Run the doctor with sudo for the full "
                 "picture, or add the user to systemd-journal.")

    analysis = analyse_controller_log(text)
    facts["controller_log"] = analysis
    for level, message in analysis["findings"]:
        say(level, message)

    if analysis.get("starts", 0) >= 3:
        say("warn", "%d controller start(s) in the last %d journal lines — a "
                    "restart loop rather than a one-off"
            % (analysis["starts"], analysis["rows"]))
        for row in analysis.get("start_lines", [])[-3:]:
            say("warn", "  " + row[:220])
        hint("The controller is being restarted repeatedly. Read the line before "
             "each start: a `Main process exited` status says whether it crashed "
             "(status=1/FAILURE) or exited cleanly (status=0/SUCCESS, usually a "
             "version update). Do that before restarting it again.")
    if analysis.get("exit_lines"):
        say("note", "restart/exit evidence (newest last):")
        for row in analysis["exit_lines"][-6:]:
            say("note", "  " + row[:220])

    if text:
        say("note", "last controller log line: %s" % text.splitlines()[-1])

    pid = info.get("ExecMainPID", "")
    if pid and pid != "0" and os.path.isdir("/proc/%s" % pid):
        cmdline = read("/proc/%s/cmdline" % pid).replace("\x00", " ").strip()
        try:
            cwd = os.readlink("/proc/%s/cwd" % pid)
        except OSError:
            cwd = ""
        facts["controller_pid"] = pid
        facts["controller_cmdline"] = cmdline
        facts["controller_cwd"] = cwd
        say("note", "running: %s" % (cmdline or "unknown"))
        if cwd and os.path.abspath(cwd) != os.path.abspath(install_dir):
            say("warn", "the controller's working directory is %s, not %s — it "
                        "is reading and writing a different map/credentials"
                % (cwd, install_dir))
            hint("The controller is running from a different directory than the "
                 "one inspected. Re-run the doctor with --dir %s." % cwd)

        started = proc_start_epoch(pid)
        if started:
            say("note", "process started %s ago" % human_age(time.time() - started))
            newest = None
            for name in ("controller.allspeak", "deviceControl.allspeak"):
                path = os.path.join(install_dir, name)
                try:
                    newest = max(newest or 0, os.path.getmtime(path))
                except OSError:
                    pass
            if newest and newest > started + 5:
                say("warn", "code on disk is newer than the running process — a "
                            "release was applied but this process has not "
                            "restarted to load it")
                hint("The running controller is older than the files on disk. "
                     "Restart it: `sudo systemctl restart controller`.")

    if text and analysis.get("runtime") and facts.get("allspeak_installed"):
        installed_version = facts["allspeak_installed"]
        match = re.search(r"(\d{8,})", installed_version)
        if match and analysis["runtime"] != match.group(1):
            say("warn", "the journal says the running controller uses AllSpeak "
                        "%s, but the installed runtime reports %s — the process "
                        "predates the installed runtime"
                % (analysis["runtime"], match.group(1)))

    expected_mac = facts.get("mac", "")
    if analysis.get("topic") and expected_mac:
        if analysis["topic"].lower() != expected_mac.lower():
            say("fail", "the controller subscribed to topic %s but this system's "
                        "identity is %s — the UI publishes to the identity topic"
                % (analysis["topic"], expected_mac))
            hint("The controller is listening on the wrong topic. The UI will "
                 "connect to the broker and never get a map. Fix the MAC "
                 "override or the topic it is started with.")

    if text:
        say("note", "the controller log is quiet by design: at normal running "
                    "the only start-up lines are 'Run Controller', "
                    "'MAC address is ...', 'Client ... connected' and "
                    "'Subscribed to topic: ...'. A healthy session also has "
                    "'Load the system map' immediately after the subscription.")
        # The tail is useful when the report is read by somebody else; keep it
        # short so the report stays a page or two.
        tail = text.splitlines()[-20:]
        facts["controller_tail"] = tail
        say("note", "last 20 controller log lines:")
        for row in tail:
            say("note", "  " + row)


# ---------------------------------------------------------------------------
# MQTT path and round-trip probe
# ---------------------------------------------------------------------------

def load_credentials(install_dir):
    path = os.path.join(install_dir, "credentials")
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data, ""
        return {}, "credentials is not a JSON object"
    except OSError:
        return {}, "no credentials file at %s" % path
    except ValueError as exc:
        return {}, "credentials is not valid JSON: %s" % exc


def check_broker(install_dir):
    section("BROKER")
    creds, problem = load_credentials(install_dir)
    facts["credentials_problem"] = problem
    if problem:
        say("warn", problem)
        return creds

    broker = str(creds.get("broker", "")).strip()
    facts["broker"] = broker
    if not broker:
        say("warn", "credentials has no broker entry")
        return creds
    say("ok", "controller broker: %s:%d" % (broker, BROKER_PORT))
    say("note", "UI broker: %s:%d over WebSocket (from credentials.port)"
        % (broker, creds.get("port", BROKER_WS_PORT)))

    try:
        addresses = socket.getaddrinfo(broker, None)
        resolved = sorted({item[4][0] for item in addresses})
        facts["broker_dns"] = resolved
        say("ok", "DNS: %s -> %s" % (broker, ", ".join(resolved[:3])))
    except socket.gaierror as exc:
        say("fail", "cannot resolve %s: %s" % (broker, exc))
        hint("DNS fails for the broker. The controller's own start-up loop waits "
             "for the name to resolve before it will run; check the network and "
             "/etc/resolv.conf.")
        return creds

    reachable, detail = tcp_check(broker, BROKER_PORT, timeout=8)
    facts["broker_1883"] = reachable
    say("ok" if reachable else "fail",
        "%s:%d reachable (%s)" % (broker, BROKER_PORT, detail)
        if reachable else
        "%s:%d unreachable (%s) — the controller cannot connect"
        % (broker, BROKER_PORT, detail))
    if not reachable:
        hint("The cloud broker is unreachable on 1883. The controller cannot "
             "connect; check the ISP/router/firewall before the controller.")

    try:
        ws_port = int(creds.get("port", BROKER_WS_PORT) or BROKER_WS_PORT)
    except (TypeError, ValueError):
        ws_port = BROKER_WS_PORT
    ws_reachable, ws_detail = tcp_check(broker, ws_port, timeout=8)
    facts["broker_websocket"] = ws_reachable
    say("ok" if ws_reachable else "warn",
        "UI WebSocket port %s reachable (%s)" % (ws_port, ws_detail))
    if not ws_reachable:
        hint("The UI's WebSocket port is unreachable. Browsers will never "
             "connect, whatever the controller does.")
    return creds


def mqtt_probe(creds, mac, timeout):
    """Register a throwaway sender and ask the controller for a full map.

    Returns (facts, reason). `facts` is None when the probe cannot run; the
    caller therefore always unpacks two values, whatever happened.
    This is the only test that proves the whole path: broker -> controller ->
    reply topic -> subscriber. A running process and a closed socket both look
    the same from `systemctl`.
    """
    broker = str(creds.get("broker", "")).strip()
    username = str(creds.get("username", ""))
    password = str(creds.get("password", ""))
    if not broker or not mac:
        return None, "no broker or no system identity"
    if not username or not password:
        return None, "credentials has no username/password"

    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        return None, "paho-mqtt is not installed (python3-paho-mqtt)"

    sender = "%s/doctor-%d" % (mac, os.getpid())
    payload = json.dumps({"sender": {"name": sender, "qos": 1},
                          "action": "first"}).encode("utf-8")
    state = {"connected": False, "connected_at": None, "published": False,
             "published_at": None, "reply": None, "reply_at": None,
             "granted": None, "code": None, "error": ""}

    try:
        try:
            client = mqtt.Client(
                client_id=sender, protocol=mqtt.MQTTv311,
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        except (AttributeError, TypeError):
            client = mqtt.Client(client_id=sender, protocol=mqtt.MQTTv311)
    except Exception as exc:                    # noqa: BLE001 — diagnostic tool
        return None, "cannot create MQTT client: %s" % exc

    def on_connect(_client, _userdata, _flags, rc, _properties=None):
        code = getattr(rc, "value", rc)
        state["code"] = code
        try:
            state["connected"] = int(code) == 0
        except (TypeError, ValueError):
            state["connected"] = getattr(rc, "is_failure", True) is False
        if state["connected"]:
            state["connected_at"] = time.time()
            _client.subscribe(sender, qos=1)

    def on_subscribe(_client, _userdata, _mid, granted_qos, _properties=None):
        # v1 passes a tuple of ints; v2 a list of ReasonCode objects. 128 means
        # the broker refused the subscription.
        codes = []
        for code in (granted_qos or []):
            codes.append(getattr(code, "value", code))
        state["granted"] = codes

    def on_publish(_client, _userdata, _mid, _reason=None, _properties=None):
        state["published"] = True
        state["published_at"] = time.time()

    def on_message(_client, _userdata, message):
        state["reply"] = message.payload
        state["reply_at"] = time.time()

    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_publish = on_publish
    client.on_message = on_message
    client.username_pw_set(username, password)

    started = time.time()
    try:
        client.connect(broker, BROKER_PORT, 30)
        client.loop_start()
        deadline = started + max(3, timeout / 3.0)
        while time.time() < deadline and not state["connected"] and not state["code"]:
            time.sleep(0.05)
        if not state["connected"]:
            return ({"connected": False, "connect_elapsed": None,
                     "published": False, "reply": None, "code": state["code"],
                     "elapsed": time.time() - started, "sender": sender,
                     "payload": payload.decode("utf-8")}, "")
        # Let the broker confirm the subscription before publishing: a reply
        # that arrives before the SUBACK would be delivered nowhere.
        while time.time() < deadline and state["granted"] is None:
            time.sleep(0.05)
        client.publish(mac, payload, qos=1)
        deadline = time.time() + timeout
        while time.time() < deadline and state["reply"] is None:
            time.sleep(0.05)
    except Exception as exc:                    # noqa: BLE001 — diagnostic tool
        state["error"] = str(exc)
    finally:
        try:
            client.loop_stop()
            client.disconnect()
        except Exception:                       # noqa: BLE001
            pass

    return ({
        "connected": state["connected"],
        "connect_elapsed": (state["connected_at"] - started
                            if state["connected_at"] else None),
        "published": state["published"],
        "publish_elapsed": (state["published_at"] - started
                            if state["published_at"] else None),
        "reply": state["reply"],
        "reply_elapsed": (state["reply_at"] - state["published_at"]
                          if state["reply_at"] and state["published_at"] else None),
        "granted": state["granted"],
        "code": state["code"],
        "error": state["error"],
        "elapsed": time.time() - started,
        "sender": sender,
        "payload": payload.decode("utf-8"),
    }, "")


def check_round_trip(creds, mac, timeout):
    section("ROUND TRIP")
    if not creds:
        say("note", "skipped: no usable credentials")
        return
    if not mac:
        say("note", "skipped: no system identity (MAC)")
        return

    say("note", "sending a 'first' map request as sender %s/doctor-<pid> "
                "and waiting up to %d s" % (mac, timeout))
    result, reason = mqtt_probe(creds, mac, timeout)
    if result:
        facts["probe"] = {
            "connected": result.get("connected"),
            "published": result.get("published"),
            "reply_bytes": len(result["reply"]) if result.get("reply") is not None else None,
            "connect_elapsed": round(result.get("connect_elapsed") or 0, 2),
            "reply_elapsed": (round(result["reply_elapsed"], 2)
                              if result.get("reply_elapsed") is not None else None),
            "granted": result.get("granted"),
            "elapsed": round(result.get("elapsed", 0), 2),
            "sender": result.get("sender"),
            "code": result.get("code"),
        }
    else:
        facts["probe"] = {"skipped": reason}
    if result is None:
        say("note", "probe skipped: %s" % reason)
        hint("The round-trip probe could not run (%s). Install python3-paho-mqtt "
             "and re-run; it is the only check that proves the controller "
             "answers." % reason)
        return

    if result.get("error"):
        say("fail", "MQTT probe error: %s" % result["error"])
    if not result.get("connected"):
        code = result.get("code")
        say("fail", "the probe could not connect to the broker (code %s)" % code)
        hint("The probe cannot connect with the controller's own credentials. "
             "The credential may be stale or fenced to a different system; "
             "check credentials.php and .mqtt_token.")
        return

    connect_elapsed = result.get("connect_elapsed")
    say("ok", "probe connected to the broker%s"
        % (" in %.1f s" % connect_elapsed if connect_elapsed is not None else ""))

    granted = result.get("granted")
    refused = [code for code in (granted or [])
               if isinstance(code, int) and code >= 128]
    if refused:
        say("warn", "the broker refused the probe's subscription to %s (code %s) "
                    "— this account can publish but cannot receive a reply"
            % (result.get("sender"), refused))
        hint("The probe uses the controller's own credentials. A fenced bridge "
             "account may be allowed to publish to the system topic but not to "
             "subscribe to a throwaway one. This is not evidence that the "
             "controller is silent; the UI's own account is the one that gets "
             "replies.")
        return
    if granted is None:
        say("note", "the broker did not confirm the subscription before the "
                    "probe published; a missing reply is then inconclusive")
    else:
        say("ok", "probe subscription granted (QoS %s)"
            % (", ".join(str(code) for code in granted) or "none"))

    if not result.get("published"):
        say("warn", "the broker did not acknowledge the probe's publish — an "
                    "ACL may be fenced to a different topic namespace")
        return

    reply = result.get("reply")
    if reply is None:
        uptime = facts.get("controller_uptime")
        if uptime is not None:
            say("note", "the controller had been running %s when the probe "
                        "started" % human_age(uptime))
        level = "fail" if granted is not None else "warn"
        say(level, "no reply from the controller within %d s — %s"
            % (timeout, "the broker path works, but the controller does not "
                        "answer its own topic" if level == "fail" else
               "and the subscription was not confirmed, so this is inconclusive"))
        if level == "fail":
            hint("The broker is fine and the controller is not answering. This "
                 "is the state that shows up as 'Reconnecting...' in the UI. "
                 "The controller drains its message queue between room cycles, "
                 "so a four-room cycle can outlast a short probe; try "
                 "`--probe-timeout 40` before concluding it is wedged. If it "
                 "still does not answer, read the journal for 'Subscribed to "
                 "topic' with no 'Load the system map' after it.")
        else:
            hint("The probe could not confirm its subscription, so the missing "
                 "reply does not prove the controller is silent. Re-run, or "
                 "check from the UI.")
        return

    length = len(reply)
    summary = "empty reply (a heartbeat, not a map)"
    try:
        parsed = json.loads(reply.decode("utf-8", "replace"))
        if isinstance(parsed, dict):
            if parsed.get("action"):
                summary = "action=%s" % parsed["action"]
            elif parsed.get("profiles") is not None:
                summary = "full map, %d profile(s)" % len(parsed.get("profiles") or [])
            else:
                summary = "JSON reply"
    except (ValueError, UnicodeDecodeError):
        pass
    say("ok", "the controller replied%s (%d bytes, %s)"
        % (" in %.1f s" % result["reply_elapsed"]
           if result.get("reply_elapsed") is not None else "", length, summary))
    if not length:
        say("warn", "the reply was empty — a 'first' request should carry the "
                    "full map; the UI will stay on its loading state")
        hint("The controller acknowledges the request but sends no map. Check "
             "map.json is readable and non-empty in the controller's working "
             "directory.")


# ---------------------------------------------------------------------------
# State files and freshness
# ---------------------------------------------------------------------------

def check_state_files(install_dir):
    section("STATE FILES")
    # Check the filesystem the install actually lives on: on a box with a
    # separate /home, / can be read-only while the controller's own disk is fine.
    _rc, _out, _err = run(["findmnt", "-T", install_dir, "-no", "OPTIONS"])
    root_options = _out

    map_path = os.path.join(install_dir, "map.json")
    age = file_age(map_path)
    facts["map_age"] = age
    if not os.path.isfile(map_path):
        say("fail", "no map.json in %s — the controller has nothing to send the UI"
            % install_dir)
        hint("map.json is missing. Restore it from the backup (or from "
             "map-sim.json only for a test) before restarting the controller.")
    else:
        text, problem = _read_json(map_path)
        if problem:
            say("fail", "map.json is not valid JSON: %s" % problem)
            hint("map.json is corrupt. Restore it from the last backup rather "
                 "than editing it in place.")
        else:
            rooms = text.get("rooms") if isinstance(text, dict) else None
            profiles = text.get("profiles") if isinstance(text, dict) else None
            say("ok", "map.json: %s, %s room(s), %s profile(s), modified %s ago"
                % (human_bytes(os.path.getsize(map_path)),
                   len(rooms) if isinstance(rooms, list) else "?",
                   len(profiles) if isinstance(profiles, list) else "?",
                   human_age(age)))
            facts["map_rooms"] = len(rooms) if isinstance(rooms, list) else None
            facts["map_profiles"] = len(profiles) if isinstance(profiles, list) else None
        if root_options and "ro" in [option.strip() for option in root_options.split(",")]:
            say("fail", "the filesystem holding %s is mounted read-only — the "
                        "controller cannot save its map or readings" % install_dir)
            hint("The controller's filesystem is read-only. That usually follows "
                 "a storage fault or a failed fsck; check dmesg and reboot.")

    volatile = read_override(os.path.join(install_dir, "volatile-root"))
    base = volatile or install_dir
    dashboard_on = dashboard_enabled(facts.get("controller_cmdline", ""),
                                     facts.get("controller", {}).get("ExecStart", ""))
    for name, warn_after, fail_after, what in [
        ("thermometers.json", 300, 900,
         "temperature readings from the Zigbee bridge"),
        ("rbr-dashboard.json", 120, 600,
         "terminal/companion dashboard snapshot"),
    ]:
        path = os.path.join(base, name)
        age = file_age(path)
        facts[name] = age
        if name == "rbr-dashboard.json" and not dashboard_on:
            say("note", "rbr-dashboard.json: %s (controller runs with "
                        "--no-dashboard; safe to delete)" %
                ("not written" if age is None
                 else "stale for %s, left from an earlier run" % human_age(age)))
            continue
        if age is None:
            # The dashboard is disabled by the service unit (--no-dashboard), so
            # its absence is normal. Readings are not: the controller refreshes
            # them at least once a minute whenever the bridge has data.
            if name == "thermometers.json":
                say("warn", "%s: absent in %s" % (name, base))
                hint("No thermometers.json: the controller has no readings to "
                     "merge. Check the bridge's /devices and the Zigbee mesh.")
            else:
                say("note", "%s: not written yet (dashboard enabled)" % name)
            continue
        level = freshness_level(age, warn_after, fail_after)
        say(level, "%s: modified %s ago (%s)" % (name, human_age(age), what))
        if level in ("warn", "fail"):
            hint("The %s file has not changed for %s. The controller writes it "
                 "once a minute when the bridge has data, so check the bridge "
                 "and the Zigbee mesh, not the UI." % (name, human_age(age)))

    journal_root = read_override(os.path.join(install_dir, "journal-root"))
    if not journal_root:
        heatlog_root = read_override(os.path.join(install_dir, "heatlog-root"))
        if heatlog_root:
            journal_root = os.path.join(heatlog_root, "events")
    facts["journal_root"] = journal_root
    if journal_root:
        if not os.path.isdir(journal_root):
            say("warn", "journal directory %s does not exist" % journal_root)
        else:
            files = sorted(glob.glob(os.path.join(journal_root, "journal-*.json")),
                           key=os.path.getmtime, reverse=True)
            if files:
                age = file_age(files[0])
                say("ok", "event journal: %d bundle(s), newest %s ago"
                    % (len(files), human_age(age)))
            else:
                say("note", "event journal enabled but no bundle written yet")
    else:
        say("note", "event journal disabled (no journal-root or heatlog-root)")

    try:
        usage = shutil.disk_usage(install_dir)
        free_gb = usage.free / 1e9
        facts["free_gb"] = round(free_gb, 2)
        say("ok" if free_gb >= 1.0 else "fail",
            "disk: %.1f GB free of %.1f GB" % (free_gb, usage.total / 1e9))
        if free_gb < 2.0:
            # Name what is actually using the space: a controller with a small
            # root partition fills with journal exports, backups or apt caches,
            # not with the controller's own files.
            candidates = [
                ("backups", os.path.join(install_dir, "backup")),
                ("journal exports", os.path.join(journal_root, "exports")
                 if journal_root else ""),
                ("journal", journal_root),
                ("system log", "/var/log"),
                ("apt cache", "/var/cache/apt/archives"),
                ("temporary files", "/tmp"),
            ]
            parts = []
            for label, path in candidates:
                if not path or not os.path.exists(path):
                    continue
                rc, out, _err = run(["du", "-sh", path], timeout=10)
                if rc == 0 and out:
                    parts.append("%s %s" % (label, out.split()[0]))
            if parts:
                say("note", "space used: " + "; ".join(parts))
            rc, out, _err = run(["journalctl", "--disk-usage"])
            if rc == 0 and out:
                say("note", out.splitlines()[-1])
            if journal_root:
                rc, out, _err = run(["df", "-h", journal_root])
                if rc == 0 and out:
                    say("note", "journal filesystem: " + out.splitlines()[-1])
        if free_gb < 1.0:
            hint("Less than 1 GB free. The controller's own small writes are "
                 "still working, but the updater, journal exporter and backups "
                 "can fail. Clear old exports/backups and the apt cache, then "
                 "re-check: `sudo du -x -h -d1 /home /data /var | sort -h | "
                 "tail`, `sudo journalctl --disk-usage`.")
    except OSError as exc:
        say("warn", "cannot read disk usage for %s: %s" % (install_dir, exc))


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle), ""
    except (OSError, ValueError) as exc:
        return None, str(exc)


# ---------------------------------------------------------------------------
# Operating system, resources and Zigbee hardware
# ---------------------------------------------------------------------------

def check_system():
    section("SYSTEM")
    release = {}
    for row in read("/etc/os-release").splitlines():
        if "=" in row:
            key, _, value = row.partition("=")
            release[key] = value.strip('"')
    pretty = release.get("PRETTY_NAME", platform.platform())
    facts["os"] = pretty
    facts["kernel"] = platform.release()
    say("ok", "%s (kernel %s)" % (pretty, platform.release()))
    say("note", "hostname %s" % socket.gethostname())

    model = ""
    for path in ("/proc/device-tree/model", "/sys/firmware/devicetree/base/model"):
        model = read(path).replace("\x00", "").strip()
        if model:
            break
    if model:
        facts["model"] = model
        say("ok", "hardware: %s" % model)

    uptime = boot_uptime()
    facts["uptime"] = uptime
    if uptime is not None:
        say("ok", "up %s" % human_age(uptime))
        if uptime < 300:
            say("note", "the box booted less than 5 minutes ago — a power cut or "
                        "a reboot may be part of the story")

    _rc, out, _err = run(["timedatectl", "show", "-p", "Timezone", "--value"])
    timezone = out
    _rc, synced, _err = run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"])
    _rc, now, _err = run(["date"])
    facts["timezone"] = timezone
    facts["ntp"] = synced
    say("ok" if synced == "yes" else "warn",
        "clock: %s %s, NTP %s" % (now or "unknown", timezone or "",
                                  "synchronised" if synced == "yes" else "NOT synchronised"))
    if synced != "yes":
        hint("The clock is not NTP-synchronised. Every schedule decision is "
             "local time, so a wrong clock heats the wrong rooms.")

    meminfo = {}
    for row in read("/proc/meminfo").splitlines():
        key, _, value = row.partition(":")
        meminfo[key] = value.strip()
    try:
        available_mb = int(meminfo.get("MemAvailable", "0 kB").split()[0]) // 1024
        facts["available_mb"] = available_mb
        say("ok" if available_mb > 100 else "warn",
            "memory available: %d MB" % available_mb)
    except (IndexError, ValueError):
        pass
    try:
        load = os.getloadavg()
        say("note", "load average: %.2f %.2f %.2f" % load)
    except OSError:
        pass

    for path in ("/sys/class/thermal/thermal_zone0/temp",):
        raw = read(path).strip()
        try:
            say("note", "CPU temperature: %.1f °C" % (int(raw) / 1000.0))
        except ValueError:
            pass
    rc, throttled, _err = run(["vcgencmd", "get_throttled"])
    if rc == 0 and throttled:
        facts["throttled"] = throttled
        level = "ok" if throttled.endswith("0x0") else "warn"
        say(level, "power/thermal throttle flags: %s" % throttled)
        if level == "warn":
            hint("The Pi reports throttling/under-voltage (%s). A marginal PSU "
                 "causes exactly the kind of service loss that looks like a "
                 "software fault; check the supply and cable." % throttled)

    # Kernel-level evidence, when readable.
    rc, dmesg, _err = run(["dmesg", "--level=err,warn"], timeout=10)
    if rc != 0 and os.geteuid() != 0:
        rc, dmesg, _err = run(["sudo", "-n", "dmesg", "--level=err,warn"], timeout=10)
    if rc == 0 and dmesg:
        interesting = [row for row in dmesg.splitlines()
                       if re.search(r"(oom|under-voltage|I/O error|EXT4-fs error|"
                                    r"read-only|mmc|usb.*disconnect|tty.*error)",
                                    row, re.IGNORECASE)]
        if interesting:
            say("warn", "kernel messages worth reading (%d):" % len(interesting))
            for row in interesting[-8:]:
                say("warn", "  " + row[:200])
            hint("The kernel reports hardware/storage/USB problems. These come "
                 "before any RBR symptom and need fixing first.")
        else:
            say("ok", "no storage/USB errors in the recent kernel log")


def check_linux_health(install_dir):
    section("LINUX HEALTH")

    # systemd's own verdict, and every unit it has given up on.
    _rc, state, _err = run(["systemctl", "is-system-running"])
    facts["system_state"] = state
    if state == "running":
        say("ok", "systemd reports the system running normally")
    elif state:
        say("fail" if state == "degraded" else "warn",
            "systemd reports the system %s" % state)
        if state == "degraded":
            hint("systemd is degraded: one or more units failed. The list below "
                 "names them; their journals say why.")
    else:
        say("note", "systemd is not answering (is this a systemd host?)")

    _rc, failed, _err = run(["systemctl", "--failed", "--no-legend",
                             "--plain", "--no-pager"])
    units = parse_failed_units(failed)
    facts["failed_units"] = units
    if units:
        say("fail", "%d failed systemd unit(s): %s"
            % (len(units), ", ".join(units[:10])))
        hint("Failed units come before most RBR symptoms. Read the first one's "
             "journal (`journalctl -u <unit>`), not the last one's.")
    else:
        say("ok", "no failed systemd units")

    for path in ("/var/run/reboot-required", "/run/reboot-required"):
        if os.path.exists(path):
            packages = read(path + ".pkgs").strip()
            say("note", "a reboot is pending%s" % (": " + packages if packages else ""))
            break

    # Inodes: a full inode table looks like a full disk, but df -h is happy.
    _rc, df_out, _err = run(["df", "-Pi", install_dir])
    inode_pct = inode_use_percent(df_out)
    facts["inode_percent"] = inode_pct
    if inode_pct is None:
        say("note", "inode usage: unavailable")
    elif inode_pct >= 98:
        say("fail", "inode usage is %d%% — the filesystem cannot create files "
                    "even though space remains" % inode_pct)
        hint("The inode table is full. Find the directory with millions of "
             "small files (often the journal or a log) before deleting blindly.")
    elif inode_pct >= 90:
        say("warn", "inode usage is %d%%" % inode_pct)
    else:
        say("ok", "inode usage: %d%%" % inode_pct)

    meminfo = {}
    for row in read("/proc/meminfo").splitlines():
        key, _, value = row.partition(":")
        meminfo[key] = value.strip()
    try:
        swap_total = int(meminfo.get("SwapTotal", "0 kB").split()[0])
        swap_free = int(meminfo.get("SwapFree", "0 kB").split()[0])
    except (IndexError, ValueError):
        swap_total = swap_free = 0
    if swap_total:
        used = swap_total - swap_free
        pct = int(100 * used / swap_total)
        facts["swap_used_percent"] = pct
        say("ok" if pct < 80 else "warn", "swap: %d%% used (%d MB of %d MB)"
            % (pct, used // 1024, swap_total // 1024))
        if pct >= 80:
            hint("Swap is nearly full. Something is leaking or the machine needs "
                 "more RAM; swapping also makes the controller miss its timings.")
    else:
        say("note", "no swap configured")

    _rc, procs, _err = run(["ps", "-eo", "stat=,pid=,comm="])
    zombies = [row.strip() for row in procs.splitlines()
               if row.strip().startswith("Z")]
    facts["zombies"] = zombies
    if zombies:
        say("warn", "%d zombie process(es): %s"
            % (len(zombies), ", ".join(row.split()[-1] for row in zombies[:6])))
    else:
        say("ok", "no zombie processes")

    # A cron entry left over from the old launch method starts a second
    # controller on the same topic, which looks exactly like a silent UI.
    _rc, out, _err = run(["pgrep", "-af", "controller.allspeak"])
    controllers = [row for row in out.splitlines()
                   if "pgrep" not in row and "controller.allspeak" in row]
    facts["controller_processes"] = controllers
    if len(controllers) > 1:
        say("fail", "%d controller processes running — they will fight over the "
                    "same MQTT topic:" % len(controllers))
        for row in controllers:
            say("fail", "  " + row[:200])
        hint("More than one controller is running. Stop the extra one first: two "
             "controllers publish conflicting maps to the same topic, which the "
             "UI reads as silence or flicker.")
    elif controllers:
        say("ok", "one controller process running")
    else:
        say("note", "no controller process found by pgrep")

    cron_entries = rbr_cron_entries()
    facts["cron_entries"] = cron_entries
    if cron_entries:
        unit_state = facts.get("controller", {}).get("UnitFileState", "")
        level = "warn" if unit_state in ("enabled", "enabled-runtime") else "note"
        say(level, "a cron entry also launches the controller%s"
            % (" while controller.service is enabled" if level == "warn" else ""))
        for row in cron_entries[:5]:
            say(level, "  " + row[:200])
        if level == "warn":
            hint("Two launch mechanisms: systemd and cron. Remove the cron entry "
                 "so only the service runs; otherwise a second controller starts "
                 "on the same topic.")
    else:
        say("ok", "no cron entry launching the controller")

    # The controller's live broker connection, as the kernel sees it. This is
    # the state systemd cannot report: active, but with its session gone.
    rc, sockets, _err = run(["ss", "-tnp"])
    if rc == 0:
        peers = parse_established(sockets, BROKER_PORT)
        facts["broker_connections"] = peers
        controller_info = facts.get("controller", {})
        controller_active = controller_info.get("ActiveState") == "active"
        if peers:
            say("ok", "%d established MQTT connection(s): %s"
                % (len(peers), ", ".join(sorted(set(peers))[:4])))
        elif controller_active:
            say("warn", "no established TCP connection to port %d — the "
                        "controller is running but has no broker session"
                % BROKER_PORT)
            hint("The controller is running but has no established broker "
                 "connection. A socket that died silently is exactly the state "
                 "the watchdog cannot see; restart the controller.")
        else:
            say("note", "no established TCP connection to port %d (the "
                        "controller is not active)" % BROKER_PORT)
    else:
        say("note", "ss unavailable — cannot inspect live broker connections")

    iface = facts.get("interface") or default_interface()
    if iface:
        errors = {}
        for stat in ("rx_errors", "tx_errors", "rx_dropped", "tx_dropped"):
            raw = read("/sys/class/net/%s/statistics/%s" % (iface, stat)).strip()
            try:
                errors[stat] = int(raw)
            except ValueError:
                errors[stat] = 0
        facts["interface_errors"] = errors
        bad = errors["rx_errors"] + errors["tx_errors"]
        if bad:
            say("warn", "%s: %d receive/transmit error(s) (drops: %d/%d)"
                % (iface, bad, errors["rx_dropped"], errors["tx_dropped"]))
            hint("The network interface is reporting errors. Check the cable, "
                 "the switch port and the PSU before blaming the software.")
        else:
            say("ok", "%s: no receive/transmit errors (drops: %d/%d)"
                % (iface, errors["rx_dropped"], errors["tx_dropped"]))
        if os.path.isdir("/sys/class/net/%s/wireless" % iface):
            signal = wifi_signal(iface)
            say("warn", "the default route is on wireless (%s)%s — a heating "
                        "controller should be wired"
                % (iface, "" if signal is None else ", signal %.0f dBm" % signal))
            hint("This controller is on Wi-Fi. Access points drop idle sockets, "
                 "and RBR assumes a wired connection survives.")

    # The system journal's own errors this boot, filtered to what touches RBR.
    text, note = journal_read(["-p", "3", "-b", "--no-pager", "-o", "short-iso",
                               "-n", "120"], "the system journal")
    if note:
        if note.startswith("no journal entries"):
            say("ok", "no error-priority system log lines this boot")
        else:
            say("note", "system journal: %s" % note)
    if text:
        rbr_like = re.compile(r"(rbr|controller|zigbee|mosquitto|allspeak|"
                              r"allpeak)", re.IGNORECASE)
        hardware = re.compile(r"(oom|out of memory|under-voltage|I/O error|"
                              r"EXT4-fs|read-only file system|mmc[0-9]|"
                              r"usb.*(disconnect|error)|failed to mount)",
                              re.IGNORECASE)
        interesting = [row for row in text.splitlines()
                       if rbr_like.search(row) or hardware.search(row)]
        if interesting:
            # The same line can repeat hundreds of times; show distinct ones.
            seen, distinct = set(), []
            for row in interesting:
                key = re.sub(r"^\S+\s+\S+\s+", "", row)[:180]
                if key in seen:
                    continue
                seen.add(key)
                distinct.append(row)
            say("warn", "%d error-priority system log line(s) touch RBR "
                        "(%d distinct):" % (len(interesting), len(distinct)))
            for row in distinct[-8:]:
                say("warn", "  " + row[:220])
            if any(re.search(r"oom|out of memory", row, re.IGNORECASE)
                   for row in distinct):
                hint("The kernel's OOM killer has run. That is why services can "
                     "vanish without a crash message; add RAM or reduce what "
                     "else runs on the box.")
        else:
            say("ok", "no RBR-relevant error-priority system log lines this boot")


def check_zigbee():
    section("ZIGBEE")
    devices = sorted(glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*"))
    facts["serial_devices"] = devices
    if devices:
        say("ok", "serial device(s): %s" % ", ".join(devices))
    else:
        say("fail", "no /dev/ttyACM* or /dev/ttyUSB* — the coordinator is not "
                    "attached, so no room can be read or heated")
        hint("No Zigbee coordinator device. Check the USB dongle and cable; "
             "Zigbee2MQTT will fail to start without it.")
    if os.path.exists("/dev/zigbee-dongle"):
        say("ok", "/dev/zigbee-dongle symlink present")

    config_paths = [
        "/userdata/zigbee2mqtt/configuration.yaml",
        "/opt/zigbee2mqtt/data/configuration.yaml",
        os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),
                     "zigbee2mqtt", "configuration.yaml"),
    ]
    found = next((path for path in config_paths if os.path.isfile(path)), "")
    facts["z2m_config"] = found
    if found:
        text = read(found)
        say("ok", "Zigbee2MQTT config: %s" % found)
        serial = ""
        mqtt_server = ""
        block = ""
        for row in text.splitlines():
            stripped = row.strip()
            if row and not row.startswith((" ", "\t", "#")):
                block = stripped.rstrip(":")
            if block == "serial" and stripped.startswith("port:"):
                serial = stripped.split(":", 1)[1].strip().strip("'\"")
            if block == "mqtt" and stripped.startswith("server:"):
                mqtt_server = stripped.split(":", 1)[1].strip().strip("'\"")
        if serial:
            facts["z2m_serial"] = serial
            exists = os.path.exists(serial) or bool(glob.glob(serial))
            say("ok" if exists else "warn",
                "coordinator port: %s%s" % (serial, "" if exists else " (MISSING)"))
            if not exists:
                hint("The coordinator port in the Zigbee2MQTT config does not "
                     "exist. Check the udev rule and re-plug the dongle.")
        if mqtt_server:
            facts["z2m_mqtt"] = mqtt_server
            say("ok", "Zigbee2MQTT MQTT server: %s" % mqtt_server)
    else:
        say("warn", "Zigbee2MQTT configuration.yaml not found in the usual places")

    rc, out, _err = run(["lsusb"])
    if rc == 0:
        if "10c4:ea60" in out:
            say("ok", "CP210x coordinator on USB (10c4:ea60)")
        else:
            say("note", "no 10c4:ea60 on USB — another coordinator model is fine, "
                        "but it may not have a stable device name")


def check_mosquitto_config():
    section("MQTT CONFIG")
    conf = "/etc/mosquitto/conf.d/rbr-local.conf"
    if os.path.isfile(conf):
        say("ok", "local bridge config: %s" % conf)
        text = read(conf)
        for row in text.splitlines():
            stripped = row.strip()
            if stripped.startswith(("address", "topic", "remote_username",
                                    "remote_clientid", "bridge_protocol")):
                # Never print a password line; these keys carry no secret.
                say("note", "  " + stripped)
        if "password" in text.lower() and "remote_password" in text:
            say("note", "remote password is present (not printed)")
    else:
        say("warn", "no %s — the local broker may not be bridged to the cloud"
            % conf)
        hint("The local mosquitto bridge config is missing. RBR expects the "
             "box's broker to bridge the system topics to the cloud broker; "
             "without it the UI has nothing to talk to.")

    _rc, listeners, _err = run(["ss", "-ltn"])
    ports = []
    for row in (listeners or "").splitlines()[1:]:
        parts = row.split()
        if len(parts) >= 4:
            ports.append(parts[3])
    facts["listening"] = ports
    for wanted in ("1883", "8080", "8889"):
        present = any(addr.endswith(":" + wanted) for addr in ports)
        say("ok" if present else "warn",
            "port %s %s" % (wanted, "listening" if present else "NOT listening"))


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def summarise():
    failures = [text for level, text in lines if level == "fail"]
    warnings = [text for level, text in lines if level == "warn"]
    return failures, warnings


def render_text():
    marks = {"ok": "[ OK ]", "warn": "[WARN]", "fail": "[FAIL]", "note": "[note]"}
    out = []
    stamp = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    out.append("RBR doctor — %s — %s" % (socket.gethostname(), stamp))
    if facts.get("install_dir"):
        out.append("install: %s%s" %
                   (facts["install_dir"],
                    " (release %s)" % facts["version_installed"]
                    if facts.get("version_installed") else ""))
    if os.geteuid() == 0:
        out.append("run as root")
    else:
        out.append("run as %s (not root: journal and hardware checks may be "
                   "limited)" % (os.environ.get("USER")
                                 or os.environ.get("LOGNAME") or "unknown"))
    out.append("")
    for level, text in lines:
        if level == "section":
            out.append("")
            out.append("== %s ==" % text)
            out.append("-" * (len(text) + 6))
            continue
        parts = str(text).split("\n")
        for index, part in enumerate(parts):
            out.append("%s %s" % (marks.get(level, "[note]") if index == 0 else "       ",
                                  part))

    failures, warnings = summarise()
    out.append("")
    out.append("=" * 66)
    if failures:
        out.append("%d failure(s), %d warning(s)" % (len(failures), len(warnings)))
    else:
        out.append("No failures, %d warning(s)" % len(warnings))

    if hints:
        out.append("")
        out.append("What this points at")
        for item in hints:
            out.append("  * %s" % item)

    # Next steps are conditional: a healthy report run as root must not tell
    # the reader to do what it has already done (the 2026-11-12 report did).
    journal_note = facts.get("controller_journal_note", "")
    needs_sudo = (os.geteuid() != 0 and
                  "re-run the doctor with sudo" in journal_note)
    controller_active = (facts.get("controller", {}).get("ActiveState")
                         == "active")
    failed_units = facts.get("failed_units") or []
    inactive = [name for name, info in (facts.get("services") or {}).items()
                if info.get("ActiveState") != "active"]

    out.append("")
    out.append("Next steps")
    if needs_sudo:
        out.append("  * Re-run as root for the controller journal: "
                   "sudo python3 rbr-doctor.py > rbr-doctor.txt")
    if failures:
        out.append("  * Work through the [FAIL] items above, starting with the "
                   "first in each section.")
    elif warnings:
        out.append("  * No failures. Review the [WARN] lines above; they are "
                   "advice, or a degradation that has not stopped the system.")
    else:
        out.append("  * No action needed: the checks above found no failures "
                   "or warnings.")
    if failed_units:
        out.append("  * Failed units: sudo systemctl --failed")
    if inactive:
        out.append("  * Services not running: sudo systemctl status "
                   + " ".join(inactive))
    if not controller_active:
        out.append("  * Watch the controller while it starts: "
                   "sudo journalctl -u controller -f")
    out.append("  * Send rbr-doctor.txt with any report — it contains no passwords.")
    return "\n".join(out)


def render_json():
    failures, warnings = summarise()
    return json.dumps({
        "facts": facts,
        "failures": failures,
        "warnings": warnings,
        "hints": hints,
        "lines": [{"level": level, "text": text} for level, text in lines],
    }, indent=2, default=str)


def main():
    parser = argparse.ArgumentParser(
        description="Read-only health report for an RBR controller box.")
    parser.add_argument("--dir", default="",
                        help="controller working directory (default: detected)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--no-probe", action="store_true",
                        help="skip the MQTT round-trip probe")
    parser.add_argument("--probe-timeout", type=int, default=30,
                        help="seconds to wait for the controller's reply (default 30; "
                             "the UI's own first-map watchdog is 30)")
    args = parser.parse_args()

    install_dir = find_install_dir(args.dir)
    checks = [
        check_system,
        lambda: check_identity(install_dir),
        lambda: check_versions(install_dir),
        check_services,
        check_timers,
        lambda: check_linux_health(install_dir),
        lambda: check_controller(install_dir),
        lambda: check_state_files(install_dir),
        check_zigbee,
        check_mosquitto_config,
    ]
    for check in checks:
        try:
            check()
        except Exception as exc:                # noqa: BLE001 — a doctor must finish
            say("warn", "a check could not complete: %s" % exc)

    try:
        creds = check_broker(install_dir)
    except Exception as exc:                    # noqa: BLE001
        say("warn", "the broker check could not complete: %s" % exc)
        creds = {}

    if args.no_probe:
        section("ROUND TRIP")
        say("note", "skipped (--no-probe)")
    else:
        try:
            check_round_trip(creds, facts.get("mac", ""), args.probe_timeout)
        except Exception as exc:                # noqa: BLE001
            say("warn", "the round-trip probe could not complete: %s" % exc)

    failures, _warnings = summarise()
    if args.json:
        print(render_json())
    else:
        print(render_text())
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
