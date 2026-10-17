#!/usr/bin/env python3
"""
rbr-preflight.py — check a machine before RBR is installed on it.

Run this on the controller that is about to be set up, before anything else. It
changes nothing: every check is a read, and the only network traffic is a
version fetch and a socket connect.

    python3 rbr-preflight.py            # human report
    python3 rbr-preflight.py --json     # same facts, machine-readable

This file is not part of the deployed set (it is absent from CONTROLLER_FILES
and from the tarball): it is for the machine *before* it is a controller. Copy
it across on its own.

It exists because the things that go wrong on an install are almost never in the
software — they are the dongle that was plugged in afterwards, the clock in the
wrong timezone, the SD card that the whole storage design exists to avoid, or a
sudo prompt nobody can answer. Each of those costs an hour; each is visible in
ten seconds here.

Exit code: 0 if nothing was flagged as a problem, 1 if anything was. Warnings
(!) do not affect the exit code.
"""

import argparse
import glob
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import urllib.request

# What the installer and the running system expect. Each is a hard requirement
# somewhere, so a miss is a problem rather than a note.
VERSION_URL = "https://rbrheating.com/heat/version"
BROKER_HOST = "rbrheating.duckdns.org"
BROKER_PORT = 8883
# Ports RBR binds *locally*. 8883 is deliberately absent: the bridge dials out to
# the cloud broker on that port, so a listener there is not a conflict.
NEEDED_PORTS = [1883, 8080, 8889]
MIN_FREE_GB = 1.0
MIN_RAM_MB = 480

lines = []       # (level, text) where level is one of "ok", "warn", "problem", "note"
facts = {}


def say(level, text):
    lines.append((level, text))


def section(title):
    lines.append(("section", title))


def run(cmd, timeout=15):
    """Run a command and return (ok, stdout). Never raises."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return False, ""


def read(path, limit=65536):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read(limit).strip()
    except OSError:
        return ""


def findmnt(target):
    """Source and fstype of the filesystem holding `target`, or ("", "")."""
    ok, out = run(["findmnt", "-no", "SOURCE,FSTYPE", target])
    if not ok or not out:
        return "", ""
    parts = out.split()
    return (parts[0], parts[1] if len(parts) > 1 else "")


def port_free(port):
    """True if nothing is listening on localhost:`port` (a connect is the test)."""
    with socket.socket() as probe:
        probe.settimeout(1.5)
        try:
            probe.connect(("127.0.0.1", port))
            return False
        except OSError:
            return True


def check_system():
    section("SYSTEM")
    details = {}
    release = {}
    for line in read("/etc/os-release").splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            release[key] = value.strip('"')
    pretty = release.get("PRETTY_NAME", platform.platform())
    facts["os"] = pretty
    say("ok", pretty)

    meminfo = read("/proc/meminfo")
    total_kb = 0
    for line in meminfo.splitlines():
        if line.startswith("MemTotal:"):
            total_kb = int(line.split()[1])
    cpus = os.cpu_count() or 0
    facts["cpu"], facts["ram_mb"] = cpus, total_kb // 1024
    say("ok" if total_kb // 1024 >= MIN_RAM_MB else "warn",
        "%d core(s), %d MB RAM" % (cpus, total_kb // 1024))

    source, fstype = findmnt("/")
    facts["root_source"], facts["root_fstype"] = source, fstype
    free_gb = shutil.disk_usage("/").free / 1e9
    facts["free_gb"] = round(free_gb, 1)
    if source.startswith("/dev/mmcblk"):
        say("warn", "root filesystem is on %s — an SD card or eMMC. RBR writes "
                    "constantly and expects an SSD or built-in storage; if a card "
                    "is unavoidable it must be high-endurance." % source)
    else:
        say("ok", "root filesystem on %s (%s), %.1f GB free" % (source, fstype, free_gb))
    if free_gb < MIN_FREE_GB:
        say("problem", "only %.1f GB free on / — the install needs room for "
                       "Zigbee2MQTT and its dependencies" % free_gb)

    _source, run_fstype = findmnt("/run")
    facts["run_fstype"] = run_fstype
    if run_fstype == "tmpfs":
        say("ok", "/run is a tmpfs — RBR's volatile data directory will be in RAM as designed")
    else:
        say("problem", "/run is not a tmpfs (it is %r). RBR puts its regenerable "
                       "files there expecting RAM; without that they would be "
                       "written to the disk on every update." % (run_fstype or "unknown"))


def check_access():
    section("ACCESS")
    user = os.environ.get("USER") or os.environ.get("LOGNAME") or platform.node()
    facts["user"] = user
    groups = []
    try:
        import grp
        groups = [grp.getgrgid(gid).gr_name for gid in os.getgroups()]
    except (ImportError, KeyError):
        pass
    facts["groups"] = groups
    say("ok", "running as %s" % user)
    if "dialout" in groups:
        say("ok", "member of dialout — Zigbee2MQTT can open the serial dongle")
    else:
        say("warn", "not in dialout — the installer adds the zigbee2mqtt *service* "
                    "user to it, but check this if you also want to run pairing "
                    "tools as yourself")

    passwordless = os.geteuid() == 0
    if not passwordless:
        ok, _ = run(["sudo", "-n", "true"], timeout=10)
        passwordless = ok
    facts["passwordless_sudo"] = passwordless
    if passwordless:
        say("ok", "root access available without a password prompt")
    else:
        say("warn", "sudo needs a password. The install needs root; run 'sudo -v' "
                    "first to cache it, or expect to be asked for a couple of steps.")


def check_clock():
    section("CLOCK")
    ok, tz = run(["timedatectl", "show", "-p", "Timezone", "--value"])
    facts["timezone"] = tz if ok else ""
    say("ok" if ok else "warn", "timezone: %s" % (tz or "unknown"))
    ok, synced = run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"])
    facts["ntp"] = synced if ok else ""
    if synced == "yes":
        say("ok", "clock synchronised by NTP")
    else:
        say("warn", "clock not NTP-synchronised (%s). Every schedule decision is "
                    "made in local time on this machine, so a wrong clock heats "
                    "the wrong rooms at the wrong times." % (synced or "unknown"))
    say("note", "now: %s" % run(["date"], timeout=5)[1])


def check_network():
    section("NETWORK")
    try:
        with urllib.request.urlopen(VERSION_URL, timeout=20) as response:
            version = response.read().decode("utf-8", "replace").strip()
        facts["version_url"] = version
        say("ok", "%s reachable (version %s)" % (VERSION_URL, version))
    except Exception as e:
        facts["version_url"] = ""
        say("problem", "%s unreachable: %s — the install cannot fetch the "
                       "controller pack without it" % (VERSION_URL, e))

    try:
        with socket.create_connection((BROKER_HOST, BROKER_PORT), timeout=10) as probe:
            facts["broker_reachable"] = True
            facts["broker_ip"] = probe.getpeername()[0]
        say("ok", "%s:%d reachable (%s) — the cloud broker the UI talks to"
            % (BROKER_HOST, BROKER_PORT, facts["broker_ip"]))
    except OSError as e:
        facts["broker_reachable"] = False
        say("problem", "%s:%d unreachable: %s — a controller behind a firewall "
                       "that blocks this cannot be reached by the web UI"
            % (BROKER_HOST, BROKER_PORT, e))

    facts["hostname"] = socket.gethostname()
    ok, addresses = run(["hostname", "-I"])
    facts["addresses"] = [a for a in addresses.split() if ":" not in a] if ok else []
    if facts["addresses"]:
        say("ok", "hostname %s, address(es) %s"
            % (facts["hostname"], ", ".join(facts["addresses"])))
    else:
        say("warn", "no IPv4 address found — is it on the network?")


def check_zigbee():
    section("ZIGBEE")
    devices = sorted(glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*"))
    facts["serial_devices"] = devices
    if devices:
        say("ok", "serial device(s) present: %s" % ", ".join(devices))
    else:
        say("problem", "no /dev/ttyACM* or /dev/ttyUSB* — plug the coordinator in "
                       "BEFORE running the setup. The installer derives both the "
                       "udev symlink and Zigbee2MQTT's port from what is attached "
                       "at startup; attaching it afterwards leaves placeholders.")

    ok, out = run(["lsusb"])
    if ok:
        if "10c4:ea60" in out:
            facts["dongle_usb_id"] = "10c4:ea60"
            say("ok", "Silicon Labs CP210x (10c4:ea60) on USB — the coordinator the "
                      "installer gives a stable /dev/zigbee-dongle name")
        else:
            say("warn", "no 10c4:ea60 on USB. Any coordinator works, but another "
                        "model is pinned to whichever /dev/tty* it happens to get, "
                        "which can change between reboots.")
    else:
        say("note", "lsusb unavailable — cannot confirm the coordinator model")

    if os.path.exists("/dev/zigbee-dongle"):
        say("ok", "/dev/zigbee-dongle symlink exists")
    else:
        say("note", "no /dev/zigbee-dongle yet — the installer creates the udev "
                    "rule that provides it")
    say("note", "keep the coordinator on a USB extension lead and clear of "
                "metalwork: a dongle pressed against a case or bracket degrades "
                "every link in the mesh at once")


def check_runtime():
    section("RUNTIME")
    facts["python"] = platform.python_version()
    if sys.version_info >= (3, 8):
        say("ok", "python3 %s" % facts["python"])
    else:
        say("problem", "python3 %s — the daemons need 3.8 or newer" % facts["python"])

    ok, node = run(["node", "--version"])
    facts["node"] = node if ok else ""
    if not ok:
        say("warn", "node not installed — Zigbee2MQTT needs it; the installer "
                    "installs the distro package")
    elif int(node.lstrip("v").split(".")[0]) >= 18:
        say("ok", "node %s" % node)
    else:
        say("problem", "node %s — Zigbee2MQTT needs 18 or newer" % node)

    # Presence checks, not PATH lookups: mosquitto lives in /usr/sbin (which is
    # not a normal user's PATH) and zigbee2mqtt is a directory run by systemd,
    # never a command. Looking them up by name reports a working install as
    # missing — the first version of this script did exactly that.
    tools = [
        ("pnpm", shutil.which("pnpm") or ""),
        ("mosquitto", shutil.which("mosquitto")
         or ("/usr/sbin/mosquitto" if os.path.exists("/usr/sbin/mosquitto") else "")),
        ("zigbee2mqtt", "/opt/zigbee2mqtt" if os.path.isdir("/opt/zigbee2mqtt") else ""),
    ]
    for name, found in tools:
        say("ok" if found else "note",
            "%s: %s" % (name, found or "not installed (the setup script installs it)"))

    allspeak = shutil.which("allspeak") or (
        os.path.expanduser("~/.local/bin/allspeak")
        if os.access(os.path.expanduser("~/.local/bin/allspeak"), os.X_OK) else "")
    facts["allspeak"] = allspeak
    if allspeak:
        say("ok", "allspeak at %s" % allspeak)
    else:
        say("warn", "allspeak not installed — 'pip install allspeak-ai' (add "
                    "--break-system-packages if pip refuses); the setup script "
                    "does not do this for you")


def check_ports(installed):
    section("PORTS")
    taken = [port for port in NEEDED_PORTS if not port_free(port)]
    facts["ports_taken"] = taken
    if not taken:
        say("ok", "all of %s are free" % ", ".join(str(p) for p in NEEDED_PORTS))
    elif installed:
        say("note", "in use: %s — expected, this machine is already running RBR"
            % ", ".join(str(p) for p in taken))
    else:
        say("problem", "already listening: %s — something else holds a port RBR "
                       "needs, and it will not start until that is resolved"
            % ", ".join(str(p) for p in taken))


def check_existing(rbr_dir):
    section("EXISTING RBR")
    if not os.path.isdir(rbr_dir):
        facts["existing_install"] = False
        say("note", "no %s — this is a fresh install" % rbr_dir)
        return False
    facts["existing_install"] = True
    files = [f for f in ("controller.allspeak", "deviceControl.allspeak", ".version",
                         "map.json", "credentials") if os.path.isfile(os.path.join(rbr_dir, f))]
    version = read(os.path.join(rbr_dir, ".version"))
    facts["existing_files"] = files
    facts["existing_version"] = version
    say("ok", "%s already exists (%d of 5 expected files, version %s)"
        % (rbr_dir, len(files), version or "none"))
    if os.path.isfile(os.path.join(rbr_dir, "map.json")):
        say("warn", "a map.json is already here — this is not a blank machine. "
                    "Installing over it keeps the map, but check that is what "
                    "you want.")
    running = os.path.isfile(os.path.join(rbr_dir, "controller.allspeak"))
    if os.path.isfile(os.path.join(rbr_dir, ".mqtt_token")):
        say("ok", ".mqtt_token present — the updater can refresh the bridge "
                  "password from the cloud by itself")
    elif os.path.isfile(os.path.join(rbr_dir, "credentials")):
        say("note", "no .mqtt_token — the updater can only bring the bridge "
                    "password into line with the local credentials file, not "
                    "fetch it from the cloud")
    return running


def main():
    parser = argparse.ArgumentParser(description="Read-only pre-install check for an RBR controller.")
    parser.add_argument("--dir", default=os.path.expanduser("~/rbr"),
                        help="where RBR will live (default ~/rbr)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    check_system()
    check_access()
    check_clock()
    check_network()
    check_zigbee()
    check_runtime()
    installed = check_existing(os.path.abspath(os.path.expanduser(args.dir)))
    check_ports(installed)

    problems = sum(1 for level, _ in lines if level == "problem")
    warnings = sum(1 for level, _ in lines if level == "warn")

    if args.json:
        print(json.dumps({"facts": facts,
                          "problems": problems,
                          "warnings": warnings,
                          "lines": [{"level": l, "text": t} for l, t in lines]},
                         indent=2))
        return 1 if problems else 0

    marks = {"ok": "  ✓ ", "warn": "  ! ", "problem": "  ✗ ", "note": "  - "}
    print()
    print("RBR pre-flight — %s — %s" % (platform.node(), run(["date"], timeout=5)[1]))
    for level, text in lines:
        if level == "section":
            print("\n" + text)
        else:
            for index, part in enumerate(text.split("\n")):
                print((marks[level] if index == 0 else "    ") + part)
    print()
    installed = facts.get("existing_install")
    if problems:
        print("%d problem(s), %d warning(s) — fix the ✗ items %s."
              % (problems, warnings,
                 "and re-check" if installed else "before installing"))
    elif installed:
        print("No problems, %d warning(s). RBR is already installed here — this "
              "reads as a health check, not a pre-install pass." % warnings)
    else:
        print("No problems, %d warning(s). Ready to install." % warnings)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
