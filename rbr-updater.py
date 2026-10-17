#!/usr/bin/env python3
"""
rbr-updater.py — standalone updater for the RBR controller

Replaces the old CheckForUpdate routine that lived inside controller.allspeak.
Runs as a one-shot systemd service triggered by an hourly timer
(rbr-updater.timer, installed by rbr-setup.sh), so code updates keep
arriving even when the controller itself is down or misbehaving — and it
can restart the controller and bridge services itself.

How it works
------------
1. Check the mosquitto cloud bridge's password against the one the cloud
   currently expects, and correct it if it has drifted — see "The cloud bridge"
   below. This is independent of any release, and while it is wrong the web
   interface cannot reach the controller at all.
2. Download rbr-controller.tar.gz from rbrheating.com/heat/ (a local file path
   or file:// URL is also accepted, mainly for testing).
3. Read the VERSION stamp embedded in the tarball and compare it with the
   local .version file. If the remote version is not newer, do nothing.
4. Extract to a staging directory under the RBR dir, verify the tarball
   contains the complete runtime file set, then atomically swap each file
   into place (os.replace — same filesystem, no torn writes).
5. Write the new version to .version.
6. Restart the services affected by the change:
     controller.allspeak / deviceControl.allspeak / simulator.allspeak  ->  controller.service
     zigbee-bridge.py                                 ->  rbr-zigbee-bridge.service
   If a service isn't installed or isn't running (e.g. the controller is
   run manually with `allspeak controller.allspeak` in a terminal), the updater
   logs a clear notice instead of killing anything.
7. If rbr-updater.py itself changed, re-exec once so the new code
   finishes the job.

The cloud bridge
----------------
The local mosquitto bridges every topic to rbrheating.duckdns.org, and the web
UI reaches the controller over that bridge — so when the bridge is refused, the
interface silently stops working on every device while the controller itself
looks perfectly healthy. The bridge authenticates with `remote_password` in
/etc/mosquitto/conf.d/rbr-local.conf, which is a *copy* of an account the cloud
owns; when the cloud side changes, the copy goes stale.

So every run compares the two. The current value comes from credentials.php
when a token is present in .mqtt_token (the same endpoint and token a paired
browser uses), and otherwise from the local `credentials` file that
rbr-setup.sh writes. Only when they differ is the config rewritten — with a
timestamped backup — and mosquitto and the controller restarted, because
mosquitto rereads its config only on restart and the controller would otherwise
stay on a dead socket.

`--check` reports whether they match and changes nothing, but a mismatch counts
as a problem, so the exit code reflects it.

Only code files from the tarball are ever replaced. Machine-specific
data (credentials, .mac_override, .mqtt_password, map.json, the map
history, heatlog-root and volatile-root) is never touched — those files
are not shipped in the tarball at all. Neither are the regenerable files
that live in the volatile directory named by volatile-root (thermometers,
zigbee-temperatures, heatlog-state, the dashboard JSON), which is a tmpfs
and is emptied on every reboot anyway. Every plain file that IS shipped in the
tarball is applied, so runtime files that are new in a release (e.g.
heatlog.py) reach controllers with that same release; TARBALL_FILES below
is the minimum required set that a valid upload must contain.

Usage:
    python3 rbr-updater.py [--url URL_OR_PATH] [--dir RBR_DIR] [--force] [--check]

    --url    tarball location; default https://rbrheating.com/heat/rbr-controller.tar.gz
    --dir    RBR directory; default = directory containing this script
    --force  apply even if the remote version is not newer
    --check  full self-check: update infrastructure (files, units, timer)
             plus remote-vs-local versions; changes nothing, works offline
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.parse
import urllib.request

# The minimum required runtime file set: every file here must be present in
# the tarball or the update is refused (guards against a truncated or wrong
# upload). Every plain file in the tarball is applied, so a file that is
# NEW in a release (e.g. heatlog.py) installs with that same release —
# there is no manifest to keep in sync and no one-release lag for additions.
# VERSION is the release stamp; it is never copied into the RBR dir as a
# file — it is recorded as .version instead.
TARBALL_FILES = [
    "controller.allspeak",
    "deviceControl.allspeak",
    "simulator.allspeak",
    "diagnose.allspeak",
    "zigbee-bridge.py",
    "zigbee-pair.py",
    "zigbee-mesh.py",
    "rbr-dashboard.py",
    "heatlog.py",
    "dashboard.txt",
    "rbr-updater.py",
    "VERSION",
]

VERSION_FILE = ".version"
SELF = "rbr-updater.py"
DEFAULT_URL = "https://rbrheating.com/heat/rbr-controller.tar.gz"
DOWNLOAD_TIMEOUT = 60

# Services restarted when the corresponding files change. (name, [files])
SERVICE_RULES = [
    ("controller.service", ["controller.allspeak", "deviceControl.allspeak", "simulator.allspeak", "heatlog.py"]),
    ("rbr-zigbee-bridge.service", ["zigbee-bridge.py"]),
]

# --- the cloud bridge's credentials -----------------------------------------
#
# The local mosquitto bridges every topic to the cloud broker, and the web UI
# reaches the controller over that bridge. No bridge, no map — on every device,
# with nothing in the browser and nothing in the controller to say why. The
# bridge authenticates with `remote_username` / `remote_password` in the file
# below, and that password is a copy of an account the *cloud* owns. When the
# cloud side changes, the copy goes stale and the bridge is refused with "not
# authorised": silently, until someone notices the interface has stopped.
#
# So every hourly run re-checks it. Fetch the credentials the cloud currently
# expects, compare with the config, and only if they differ rewrite the file
# and restart the broker and controller. The value never has to be typed in by
# hand again, and the failure cannot be silent.
#
# Where the current value comes from, in order:
#   1. credentials.php, when a token is available in .mqtt_token — the same
#      endpoint and token a paired browser uses, so the box asks the cloud the
#      same question the UI does;
#   2. otherwise the local `credentials` file, which rbr-setup.sh writes and an
#      operator can correct by hand.
# A broker credential written into mosquitto's config must be one token: no
# whitespace, nothing that could start a new line and become a directive.
_SAFE_TOKEN = re.compile(r"[A-Za-z0-9._~+/=:@-]{1,256}")

BRIDGE_CONF = "/etc/mosquitto/conf.d/rbr-local.conf"
CREDENTIALS_URL = "https://rbrheating.com/credentials.php"
TOKEN_FILE = ".mqtt_token"


def _conf_get(text, key):
    """Value of a `key value` line in the mosquitto config, or None."""
    found = re.search(r"^" + re.escape(key) + r"\s+(\S+)\s*$", text, re.MULTILINE)
    return found.group(1) if found else None


def _conf_set(text, key, value):
    """Replace a `key value` line. Returns (text, matched)."""
    pattern = re.compile(r"^" + re.escape(key) + r"\s+.*$", re.MULTILINE)
    if not pattern.search(text):
        return text, False
    return pattern.sub(key + " " + value, text, count=1), True


def current_broker_credentials(rbr_dir):
    """(username, password, source) the cloud currently expects, or (None, None, None)."""
    mac = token = ""
    for name, target in ((".mac_override", "mac"), (TOKEN_FILE, "token")):
        try:
            with open(os.path.join(rbr_dir, name), encoding="utf-8") as fh:
                value = fh.read().strip()
        except OSError:
            value = ""
        if target == "mac":
            mac = value
        else:
            token = value

    if mac and token:
        url = "%s?mac=%s&token=%s" % (CREDENTIALS_URL,
                                      urllib.parse.quote(mac), urllib.parse.quote(token))
        try:
            with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT) as resp:
                data = json.load(resp)
            if data.get("username") and data.get("password"):
                return data["username"], data["password"], "credentials.php"
        except Exception as e:
            log(f"Bridge credentials: could not fetch from credentials.php "
                f"(falling back to the local copy): {e}")

    try:
        with open(os.path.join(rbr_dir, "credentials"), encoding="utf-8") as fh:
            data = json.load(fh)
        if data.get("username") and data.get("password"):
            return data["username"], data["password"], "local credentials"
    except (OSError, ValueError):
        pass
    return None, None, None


def bridge_state():
    """True if the cloud bridge is connected, False if not, None if unknown.

    mosquitto publishes a retained `$SYS/broker/connection/<id>/state` for each
    configured bridge: 1 connected, 0 not. Reading the broker's own view is the
    only way to know — the bridge failing does not make anything else fail.
    """
    try:
        result = subprocess.run(
            ["mosquitto_sub", "-h", "localhost", "-t", "$SYS/broker/connection/#", "-v", "-W", "3"],
            capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    states = [line.rsplit(" ", 1)[-1].strip()
              for line in result.stdout.splitlines() if line.strip()]
    if not states:
        return None
    return "0" not in states


def _report_bridge_state():
    state = bridge_state()
    if state is True:
        log("Bridge to the cloud: connected")
    elif state is False:
        log("Bridge to the cloud: NOT CONNECTED — the web UI cannot reach this "
            "controller until it is")
    else:
        log("Bridge to the cloud: state unknown (mosquitto_sub unavailable?)")
    return state


def ensure_bridge_credentials(rbr_dir, conf_path=BRIDGE_CONF, apply_changes=True):
    """Bring the bridge password in step with the cloud. Returns True if stale."""
    if not os.path.isfile(conf_path):
        log(f"Bridge credentials: no {conf_path} — not a bridged install, skipping")
        return False
    try:
        with open(conf_path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        log(f"Bridge credentials: cannot read {conf_path}: {e}")
        return False

    username, password, source = current_broker_credentials(rbr_dir)
    want_user = username or _conf_get(text, "remote_username")
    if not password:
        log("Bridge credentials: cannot establish the current password "
            "(no .mqtt_token and no usable credentials file)")
        _report_bridge_state()
        return False

    # The value is written into a line-oriented config file, so it has to be a
    # single token. A password carrying a newline would append a directive to
    # mosquitto's configuration, and one carrying a space would corrupt the
    # line. Both are unlikely — the cloud generates hex — but the local
    # `credentials` file is hand-editable, and this writes as root.
    if not _SAFE_TOKEN.fullmatch(password) or (want_user and not _SAFE_TOKEN.fullmatch(want_user)):
        log(f"Bridge credentials: refusing to use the value from {source} — it is "
            "not a single token (whitespace or control characters in it), and it "
            "would corrupt or add to mosquitto's configuration")
        _report_bridge_state()
        return False

    have_user = _conf_get(text, "remote_username")
    have_pw = _conf_get(text, "remote_password")

    if have_pw == password and have_user == want_user:
        log(f"Bridge credentials: up to date (from {source})")
        _report_bridge_state()
        return False

    log(f"Bridge credentials: STALE — config has {len(have_pw or '')} characters, "
        f"the cloud expects {len(password)} (from {source})")
    if not apply_changes:
        log("Bridge credentials: check only — nothing changed")
        _report_bridge_state()
        return True

    new_text, matched = _conf_set(text, "remote_username", want_user)
    if matched:
        new_text, matched = _conf_set(new_text, "remote_password", password)
    if not matched:
        log(f"Bridge credentials: no remote_username/remote_password lines in "
            f"{conf_path} — nothing changed")
        return False

    backup = "%s.bak-%s" % (conf_path, time.strftime("%Y%m%d-%H%M%S"))
    try:
        shutil.copy2(conf_path, backup)
        with open(conf_path, "w", encoding="utf-8") as fh:
            fh.write(new_text)
    except OSError as e:
        log(f"Bridge credentials: could not write {conf_path}: {e} (running as root?)")
        return False
    log(f"Bridge credentials: updated (backup {os.path.basename(backup)})")

    # Keep the operator's own record in step, so a future rbr-setup.sh reuses
    # this value instead of prompting with a stale one.
    try:
        path = os.path.join(rbr_dir, ".mqtt_password")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(password + "\n")
        # This runs as root; leave the file readable by whoever owns the RBR
        # directory, so an operator can still read it.
        os.chmod(path, 0o600)
        os.chown(path, os.stat(rbr_dir).st_uid, os.stat(rbr_dir).st_gid)
    except OSError as e:
        log(f"Bridge credentials: could not update .mqtt_password: {e}")

    # mosquitto rereads the file only on restart; the controller then needs its
    # own MQTT connection re-established rather than left on a dead socket.
    restart_service("mosquitto.service")
    time.sleep(3)
    restart_service("controller.service")
    time.sleep(3)
    _report_bridge_state()
    return True


def log(msg):
    print(f"[rbr-updater] {msg}", flush=True)


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_local_version(rbr_dir):
    path = os.path.join(rbr_dir, VERSION_FILE)
    if not os.path.exists(path):
        return 0
    try:
        return int(open(path).read().strip() or 0)
    except ValueError:
        log(f"Warning: unparseable {VERSION_FILE}; treating as 0")
        return 0


def download_tarball(source, dest):
    """Fetch the tarball to dest. source may be an http(s) URL, file:// URL, or a local path."""
    if source.startswith("http://") or source.startswith("https://"):
        log(f"Downloading {source}")
        with urllib.request.urlopen(source, timeout=DOWNLOAD_TIMEOUT) as resp:
            with open(dest, "wb") as f:
                shutil.copyfileobj(resp, f)
    elif source.startswith("file://"):
        src = source[len("file://"):]
        shutil.copyfile(src, dest)
    else:
        shutil.copyfile(source, dest)


def _norm_name(name):
    """Strip the leading './' that tar adds when archiving with '.'."""
    return name[2:] if name.startswith("./") else name


def extract_tarball(tarball, staging):
    """Extract and verify; returns {name: abs_path} for EVERY plain file.

    Every plain file in the tarball is staged and returned, so files that
    are new in a release are applied by the same update that introduces
    them. TARBALL_FILES is the minimum required set: an upload missing any
    of those files is refused. Raises on any problem.
    """
    try:
        with tarfile.open(tarball, "r:gz") as tf:
            # Safety: only plain files; reject symlinks/hardlinks/devices and
            # any path traversal or absolute path. The tarball is produced by
            # deploy.sh, but this keeps a compromised/mis-uploaded tarball
            # from writing outside the staging dir.
            members = []
            files = {}
            for member in tf.getmembers():
                norm = _norm_name(member.name)
                if norm in ("", "."):
                    continue  # the '.' root entry tar adds when archiving '.'
                if norm.startswith("/") or ".." in norm.split("/"):
                    raise ValueError(f"unsafe path in tarball: {member.name}")
                if member.isdir():
                    members.append(member)  # plain dirs are harmless
                    continue
                if not member.isfile():
                    raise ValueError(f"unsupported file type in tarball: {member.name}")
                member.name = norm
                members.append(member)
                files[norm] = os.path.join(staging, norm)
            tf.extractall(staging, members=members)
    except (tarfile.TarError, OSError, ValueError) as e:
        raise RuntimeError(f"invalid tarball: {e}")

    missing = [n for n in TARBALL_FILES if n not in files]
    if missing:
        raise RuntimeError(f"tarball missing required file(s): {', '.join(missing)}")
    return files


def service_active(name):
    try:
        r = subprocess.run(
            ["systemctl", "is-active", name], capture_output=True, text=True, timeout=15
        )
        return r.returncode == 0 and r.stdout.strip() == "active"
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def restart_service(name):
    """Restart a systemd service; returns True on success."""
    log(f"Restarting {name}...")
    try:
        r = subprocess.run(
            ["systemctl", "restart", name], capture_output=True, text=True, timeout=60
        )
        if r.returncode != 0:
            log(f"Warning: could not restart {name}: {r.stderr.strip()}")
            return False
        log(f"  {name} restarted")
        return True
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        log(f"Warning: could not restart {name}: {e}")
        return False


def ensure_restart_policy():
    """Make controller.service restart after ANY exit, not just failures.

    controller.allspeak exits cleanly (code 0) when a new release is applied, expecting
    the service to bring it straight back. Units written by an older
    rbr-setup.sh used Restart=on-failure, so that clean exit left the heating
    controller DOWN until the next hourly watchdog run. A drop-in is used so the
    unit file itself is untouched; when the unit is absent or already
    Restart=always this is a no-op. Runs as root, like the rest of the updater.
    """
    dropin_dir = "/etc/systemd/system/controller.service.d"
    dropin = os.path.join(dropin_dir, "restart.conf")
    try:
        r = subprocess.run(["systemctl", "show", "controller.service", "-p", "Restart"],
                           capture_output=True, text=True, timeout=15)
        if (r.stdout or "").strip().endswith("=always"):
            return True
        load = subprocess.run(["systemctl", "show", "controller.service", "-p", "LoadState"],
                              capture_output=True, text=True, timeout=15)
        if "not-found" in (load.stdout or ""):
            return True  # controller isn't run as a service here — nothing to do
        os.makedirs(dropin_dir, exist_ok=True)
        with open(dropin, "w") as f:
            f.write("[Service]\nRestart=always\nRestartSec=5\n")
        subprocess.run(["systemctl", "daemon-reload"],
                       capture_output=True, text=True, timeout=30)
        log("controller.service: Restart=always set via drop-in — a clean exit "
            "(as happens when an update is applied) now restarts automatically")
        return True
    except (OSError, subprocess.SubprocessError) as e:
        log(f"Warning: could not set the controller restart policy: {e}")
        return False


def _unit_state(unit):
    """Return (active, enabled) state strings for a systemd unit."""
    try:
        ra = subprocess.run(["systemctl", "is-active", unit],
                            capture_output=True, text=True, timeout=15)
        re_ = subprocess.run(["systemctl", "is-enabled", unit],
                             capture_output=True, text=True, timeout=15)
        active = (ra.stdout or ra.stderr).strip()
        enabled = (re_.stdout or re_.stderr).strip()
        if (active in ("not-found", "not found") or "could not be found" in active
                or enabled in ("not-found", "not found") or "could not be found" in enabled):
            return ("not installed", "not installed")
        return (active, enabled)
    except (subprocess.SubprocessError, FileNotFoundError):
        return ("no systemd", "no systemd")


# Files the updater manages; all must be present in the RBR dir.
CHECK_FILES = [f for f in TARBALL_FILES if f != "VERSION"]

# Units the update chain depends on. controller.service is optional — the
# controller may legitimately be run manually (allspeak controller.allspeak).
# A 4th field of "oneshot" marks units that are only active *while they run*
# (Type=oneshot), so their active state is meaningless between runs: for those
# only presence + enabled state are checked.
CHECK_SERVICES = [
    ("rbr-updater.service", True, "updater service (one-shot)", "oneshot"),
    ("rbr-updater.timer", True, "updater timer (drives hourly runs)"),
    ("rbr-watchdog.timer", True, "component watchdog timer (hourly health check)"),
    ("mosquitto.service", True, "local MQTT broker"),
    ("zigbee2mqtt.service", True, "Zigbee2MQTT (dongle bridge)"),
    ("rbr-zigbee-bridge.service", True, "RBR HTTP/MQTT bridge (restarted on update)"),
    ("controller.service", False, "controller (optional if run manually)"),
]

_ENABLED_OK = ("enabled", "static", "indirect", "alias")


def check_infrastructure(rbr_dir):
    """Self-check of the update chain. Returns 0 if healthy, 1 if problems."""
    problems = 0
    print("── RBR update infrastructure ──")

    missing = [f for f in CHECK_FILES
               if not os.path.isfile(os.path.join(rbr_dir, f))]
    if missing:
        problems += 1
        print(f"  ✗ missing runtime files: {', '.join(missing)}")
    else:
        print(f"  ✓ all {len(CHECK_FILES)} runtime files present")

    for entry in CHECK_SERVICES:
        unit, required, label = entry[0], entry[1], entry[2]
        oneshot = len(entry) > 3 and entry[3] == "oneshot"
        active, enabled = _unit_state(unit)
        if active == "not installed":
            if required:
                problems += 1
                print(f"  ✗ {label} ({unit}): NOT INSTALLED")
            else:
                print(f"  - {label} ({unit}): not installed (ok if run manually)")
            continue
        if active == "no systemd":
            print(f"  ? {label} ({unit}): systemd unavailable")
            continue
        if oneshot:
            # Inactive between runs is normal for Type=oneshot, so judge it on
            # presence + enabled state only (a oneshot unit is 'static').
            if required and enabled not in _ENABLED_OK:
                problems += 1
                print(f"  ✗ {label} ({unit}): not enabled ({enabled})")
            else:
                print(f"  ✓ {label} ({unit}): installed ({enabled}) — runs on its timer")
            continue
        if active != "active":
            if required:
                problems += 1
                print(f"  ✗ {label} ({unit}): {active} / {enabled}")
            else:
                print(f"  - {label} ({unit}): {active} (ok — run manually?)")
        elif required and enabled not in _ENABLED_OK:
            problems += 1
            print(f"  ✗ {label} ({unit}): active but not enabled ({enabled})")
        else:
            print(f"  ✓ {label} ({unit}): {active} / {enabled}")

    if problems:
        print(f"── {problems} problem(s) found ──")
        return 1
    print("── all checks passed ──")
    return 0


def read_remote_version(tarball_path):
    """Extract the VERSION stamp from a downloaded tarball; returns int."""
    with tarfile.open(tarball_path, "r:gz") as tf:
        member = next(
            (m for m in tf.getmembers() if _norm_name(m.name) == "VERSION"), None
        )
        if member is None:
            raise KeyError("VERSION")
        return int(tf.extractfile(member).read().decode().strip())


def main():
    ap = argparse.ArgumentParser(description="RBR controller updater")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--dir", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="self-check infrastructure + versions, change nothing")
    ap.add_argument("--bridge-conf", default=BRIDGE_CONF,
                    help="mosquitto config holding the cloud bridge (default %s)" % BRIDGE_CONF)
    args = ap.parse_args()

    rbr_dir = os.path.abspath(args.dir)
    if not os.path.isdir(rbr_dir):
        log(f"Error: {rbr_dir} is not a directory")
        return 2
    log(f"RBR dir: {rbr_dir}")

    # --- the cloud bridge's password --------------------------------------
    # Before anything release-shaped: this drifts independently of any release,
    # and while it is stale the interface cannot reach this controller at all,
    # so it is the first thing worth knowing about. In --check mode it reports
    # and changes nothing, but a stale password counts as a problem.
    try:
        credentials_stale = ensure_bridge_credentials(rbr_dir, args.bridge_conf,
                                                      apply_changes=not args.check)
    except Exception as e:
        log(f"Bridge credentials: unexpected error, continuing: {e}")
        credentials_stale = False

    # --- download to a temp file -----------------------------------------
    tmp = tempfile.NamedTemporaryFile(prefix="rbr-update-", suffix=".tar.gz", delete=False)
    tmp.close()
    try:
        download_ok = True
        try:
            download_tarball(args.url, tmp.name)
        except Exception as e:
            download_ok = False
            if args.check:
                log(f"Download failed (offline?): {e}")
            else:
                log(f"Download failed: {e}")
                return 1

        remote_version = None
        if download_ok:
            try:
                remote_version = read_remote_version(tmp.name)
            except Exception as e:
                if args.check:
                    log(f"Could not read VERSION from tarball: {e}")
                else:
                    log(f"Could not read VERSION from tarball: {e}")
                    return 1

        if args.check:
            # Full self-check: update infrastructure + version comparison.
            # Works even when the tarball is unreachable.
            problems = check_infrastructure(rbr_dir)
            local_version = read_local_version(rbr_dir)
            if remote_version is not None:
                log(f"Remote version {remote_version}, local version {local_version}")
            else:
                log(f"Local version {local_version} (remote unreachable)")
            log("Check only — no changes made")
            return 1 if (problems or credentials_stale) else 0

        local_version = read_local_version(rbr_dir)
        log(f"Remote version {remote_version}, local version {local_version}")

        if not args.force and remote_version <= local_version:
            log(f"Up to date (local {local_version})")
            return 0

        # --- extract + verify --------------------------------------------
        staging = tempfile.mkdtemp(prefix="rbr-stage-", dir=rbr_dir)
        try:
            try:
                extracted = extract_tarball(tmp.name, staging)
            except RuntimeError as e:
                log(f"Update refused: {e}")
                return 1

            # --- figure out what actually changed ------------------------
            changed = []
            for name, staged in extracted.items():
                if name == "VERSION":
                    continue
                live = os.path.join(rbr_dir, name)
                if not os.path.exists(live) or sha256_of(live) != sha256_of(staged):
                    changed.append(name)

            if not changed and not args.force:
                log("Newer version but files identical — re-attempting service restarts")
            elif changed:
                log(f"Updating: {', '.join(changed)}")
                for name in changed:
                    if name == SELF:
                        continue  # handled last, via re-exec
                    live = os.path.join(rbr_dir, name)
                    os.replace(os.path.join(staging, name), live)
                    log(f"  replaced {name}")

            # --- restart affected services -------------------------------
            # Done BEFORE recording .version: a failed restart leaves the old
            # stamp in place so the next hourly run retries. The
            # identical-files-but-newer case IS the retry — a previous run
            # may have failed a restart before recording the version.
            if changed:
                affected = [s for s, files in SERVICE_RULES if any(f in changed for f in files)]
            elif remote_version > local_version and not args.force:
                affected = [s for s, _ in SERVICE_RULES]
            else:
                affected = []

            restart_failed = False
            for service in affected:
                if service_active(service):
                    if not restart_service(service):
                        restart_failed = True
                else:
                    log(
                        f"{service} is not running (controller run manually?) — "
                        "restart the controller yourself to pick up new code"
                    )

            # Make sure a *clean* controller exit also restarts it. controller.allspeak
            # exits 0 when a new release lands (it expects to be restarted with
            # the new code), so Restart=on-failure would leave the heating
            # controller down until something else noticed. Idempotent.
            ensure_restart_policy()

            if restart_failed:
                log(
                    "Warning: a service failed to restart; leaving .version unrecorded "
                    "so the next hourly run retries. New code is on disk; if the "
                    "controller runs manually, restart it yourself."
                )
                return 1

            # --- record version ------------------------------------------
            with open(os.path.join(rbr_dir, VERSION_FILE), "w") as f:
                f.write(f"{remote_version}\n")
            log(f"Recorded version {remote_version} in {VERSION_FILE}")

            # --- self-update ---------------------------------------------
            if SELF in changed:
                log("rbr-updater.py changed — replacing and re-running")
                os.replace(os.path.join(staging, SELF), os.path.join(rbr_dir, SELF))
                os.chmod(os.path.join(rbr_dir, SELF), 0o755)
                # execv never returns, so the finally blocks below won't run
                # for this process — clean up explicitly first. The re-run
                # does its own download/staging housekeeping.
                shutil.rmtree(staging, ignore_errors=True)
                try:
                    os.unlink(tmp.name)
                except OSError:
                    pass
                log("Update complete")
                os.execv(sys.executable, [sys.executable, os.path.join(rbr_dir, SELF)] + sys.argv[1:])

            log("Update complete")
        finally:
            shutil.rmtree(staging, ignore_errors=True)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
