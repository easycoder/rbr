#!/usr/bin/env python3
"""
rbr-updater.py — standalone updater for the RBR controller

Replaces the old CheckForUpdate routine that lived inside controller.as.
Runs as a one-shot systemd service triggered by an hourly timer
(rbr-updater.timer, installed by rbr-setup.sh), so code updates keep
arriving even when the controller itself is down or misbehaving — and it
can restart the controller and bridge services itself.

How it works
------------
1. Download rbr-controller.tar.gz from rbrheating.com (a local file path
   or file:// URL is also accepted, mainly for testing).
2. Read the VERSION stamp embedded in the tarball and compare it with the
   local .version file. If the remote version is not newer, do nothing.
3. Extract to a staging directory under the RBR dir, verify the tarball
   contains the complete runtime file set, then atomically swap each file
   into place (os.replace — same filesystem, no torn writes).
4. Write the new version to .version.
5. Restart the services affected by the change:
     controller.as / deviceControl.as / simulator.as  ->  controller.service
     zigbee-bridge.py                                 ->  rbr-zigbee-bridge.service
   If a service isn't installed or isn't running (e.g. the controller is
   run manually with `allspeak controller.as` in a terminal), the updater
   logs a clear notice instead of killing anything.
6. If rbr-updater.py itself changed, re-exec once so the new code
   finishes the job.

Only code files from the tarball are ever replaced. Machine-specific
data (credentials, .mac_override, config.json, map.json,
thermometers.json, zigbee-temperatures.json, .mqtt_password,
heatlog-root, heatlog-state.json) is never touched — those files are not
shipped in the tarball at all. Every plain file that IS shipped in the
tarball is applied, so runtime files that are new in a release (e.g.
heatlog.py) reach controllers with that same release; TARBALL_FILES below
is the minimum required set that a valid upload must contain.

Usage:
    python3 rbr-updater.py [--url URL_OR_PATH] [--dir RBR_DIR] [--force] [--check]

    --url    tarball location; default https://rbrheating.com/rbr-controller.tar.gz
    --dir    RBR directory; default = directory containing this script
    --force  apply even if the remote version is not newer
    --check  full self-check: update infrastructure (files, units, timer)
             plus remote-vs-local versions; changes nothing, works offline
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

# The minimum required runtime file set: every file here must be present in
# the tarball or the update is refused (guards against a truncated or wrong
# upload). Every plain file in the tarball is applied, so a file that is
# NEW in a release (e.g. heatlog.py) installs with that same release —
# there is no manifest to keep in sync and no one-release lag for additions.
# VERSION is the release stamp; it is never copied into the RBR dir as a
# file — it is recorded as .version instead.
TARBALL_FILES = [
    "controller.as",
    "deviceControl.as",
    "simulator.as",
    "diagnose.as",
    "zigbee-bridge.py",
    "zigbee-pair.py",
    "rbr-dashboard.py",
    "heatlog.py",
    "dashboard.txt",
    "rbr-updater.py",
    "VERSION",
]

VERSION_FILE = ".version"
SELF = "rbr-updater.py"
DEFAULT_URL = "https://rbrheating.com/rbr-controller.tar.gz"
DOWNLOAD_TIMEOUT = 60

# Services restarted when the corresponding files change. (name, [files])
SERVICE_RULES = [
    ("controller.service", ["controller.as", "deviceControl.as", "simulator.as", "heatlog.py"]),
    ("rbr-zigbee-bridge.service", ["zigbee-bridge.py"]),
]


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

    controller.as exits cleanly (code 0) when a new release is applied, expecting
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
# controller may legitimately be run manually (allspeak controller.as).
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
    args = ap.parse_args()

    rbr_dir = os.path.abspath(args.dir)
    if not os.path.isdir(rbr_dir):
        log(f"Error: {rbr_dir} is not a directory")
        return 2
    log(f"RBR dir: {rbr_dir}")

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
            return 1 if problems else 0

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

            # Make sure a *clean* controller exit also restarts it. controller.as
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
