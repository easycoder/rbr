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
thermometers.json, zigbee-temperatures.json, .mqtt_password) is never
touched — those files are not shipped in the tarball at all.

Usage:
    python3 rbr-updater.py [--url URL_OR_PATH] [--dir RBR_DIR] [--force] [--check]

    --url    tarball location; default https://rbrheating.com/rbr-controller.tar.gz
    --dir    RBR directory; default = directory containing this script
    --force  apply even if the remote version is not newer
    --check  report remote vs local versions and exit without applying
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

# The complete runtime file set. Every file must be present in the tarball
# or the update is refused (guards against a truncated or wrong upload).
# VERSION is the release stamp; it is never copied into the RBR dir as a
# file — it is recorded as .version instead.
TARBALL_FILES = [
    "controller.as",
    "deviceControl.as",
    "simulator.as",
    "zigbee-bridge.py",
    "zigbee-pair.py",
    "rbr-dashboard.py",
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
    ("controller.service", ["controller.as", "deviceControl.as", "simulator.as"]),
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
    """Extract and verify; returns {name: abs_path}. Raises on any problem."""
    try:
        with tarfile.open(tarball, "r:gz") as tf:
            # Safety: only plain files; reject symlinks/hardlinks/devices and
            # any path traversal or absolute path. The tarball is produced by
            # deploy.sh, but this keeps a compromised/mis-uploaded tarball
            # from writing outside the staging dir.
            members = []
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
            tf.extractall(staging, members=members)
    except (tarfile.TarError, OSError, ValueError) as e:
        raise RuntimeError(f"invalid tarball: {e}")

    extracted = {}
    for name in TARBALL_FILES:
        p = os.path.join(staging, name)
        if not os.path.isfile(p):
            raise RuntimeError(f"tarball missing required file: {name}")
        extracted[name] = p
    return extracted


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


def main():
    ap = argparse.ArgumentParser(description="RBR controller updater")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--dir", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--check", action="store_true")
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
        try:
            download_tarball(args.url, tmp.name)
        except Exception as e:
            log(f"Download failed: {e}")
            return 1

        # --- read remote version -----------------------------------------
        # Extract just VERSION first (cheap) so we can gate before full extraction.
        try:
            with tarfile.open(tmp.name, "r:gz") as tf:
                member = next(
                    (m for m in tf.getmembers() if _norm_name(m.name) == "VERSION"), None
                )
                if member is None:
                    raise KeyError("VERSION")
                remote_raw = tf.extractfile(member).read().decode().strip()
        except Exception as e:
            log(f"Could not read VERSION from tarball: {e}")
            return 1
        try:
            remote_version = int(remote_raw)
        except ValueError:
            log(f"Bad VERSION in tarball: {remote_raw!r}")
            return 1

        local_version = read_local_version(rbr_dir)
        log(f"Remote version {remote_version}, local version {local_version}")

        if args.check:
            log("Check only — no changes made")
            return 0

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
