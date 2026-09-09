#!/usr/bin/env bash
# Deploy RBR web UI + controller files to rbrheating.com.
#
# Layout on the server:
#   /                   <- legacy UI entry points (index.html, auth.php, ...)
#   /resources/         <- legacy UI resources
#   /new-ui/            <- new UI (PWA) — index.html, sw.js, resources/, icons/
#   /controller.as      <- AllSpeak controller source (legacy pull)
#   /deviceControl.as   <- ditto
#   /simulator.as       <- ditto
#   /rbr-controller.tar.gz <- versioned bundle of ALL controller runtime
#                          files, pulled by the standalone updater
#                          (rbr-updater.py) — see doc/UPDATE-MECHANISM.md
#   /rbr-controller.zip   <- same files + rbr-setup.sh + VERSION: the
#                          install pack fetched by get-controller.sh when
#                          setting up a new controller
#   /get-controller.sh    <- bootstrap downloader: wget it, run it, it
#                          fetches and unpacks rbr-controller.zip
#   /version            <- single-line version stamp; bumping this (with
#                          --release) makes controllers apply the tarball
#
# Usage:
#   ./deploy.sh             upload UI + .as files; do NOT bump the version.
#                           Customers keep their current version until you
#                           release. Safe to run during iteration; smoke-test
#                           on your own IXHUB by scp'ing controller.as
#                           directly before publishing.
#
#   ./deploy.sh --release   upload everything as above, then bump and push
#                           the version stamp. IXHUBs pick up the new .as
#                           files on their next hourly CheckForUpdate.
#
# The version file is uploaded LAST so a controller mid-check never sees a
# new version paired with stale source.
set -euo pipefail

REMOTE="rbrheating@rbrheating.com:/home/rbrheating/rbrheating.com"
LOCAL="$(cd "$(dirname "$0")" && pwd)"

# SSH connection multiplexing — share a single SSH session across all the
# rsync calls below. Without this, each rsync re-pays the SSH handshake
# cost (which can be 30+ s on a slow link); with it, only the first one
# pays. ControlPersist keeps the master alive briefly after the script
# exits so an immediate re-run is also fast.
SSH_CTL="/tmp/ssh-rbr-%r@%h:%p"
SSH_OPTS="ssh -o ControlMaster=auto -o ControlPath=$SSH_CTL -o ControlPersist=60"

RELEASE=0
for arg in "$@"; do
    case "$arg" in
        --release) RELEASE=1 ;;
        *) echo "Unknown argument: $arg"; echo "Usage: $0 [--release]"; exit 1 ;;
    esac
done

echo "Deploying RBR to ${REMOTE}..."

# Root-level web files (legacy UI)
rsync -rvz --no-perms -e "$SSH_OPTS" \
    "$LOCAL/index.html" \
    "$LOCAL/favicon.ico" \
    "$LOCAL/auth.php" \
    "$LOCAL/credentials.php" \
    "$LOCAL/.htaccess" \
    "$REMOTE/"

# Resources subdirectories — --delete keeps remote in sync with local
for dir in as css icon img json webson; do
    echo "  resources/$dir"
    rsync -rvz --no-perms --delete -e "$SSH_OPTS" \
        "$LOCAL/resources/$dir/" \
        "$REMOTE/resources/$dir/"
done

# New UI tree (PWA). One rsync of the whole new-ui/ directory keeps it
# in lock-step with the local copy, including shell.as, sw.js, webson
# templates, icons and the manifest. --delete prunes anything removed
# locally so stale files can't linger on the server.
echo "Deploying new-ui/..."
rsync -rvz --no-perms --delete -e "$SSH_OPTS" \
    "$LOCAL/new-ui/" \
    "$REMOTE/new-ui/"

# Controller AllSpeak source files. Always pushed so the cloud copy is
# current, but customer IXHUBs won't pull them until the version bumps.
echo "Deploying controller files..."
rsync -vz --no-perms -e "$SSH_OPTS" \
    "$LOCAL/controller.as" \
    "$LOCAL/deviceControl.as" \
    "$LOCAL/simulator.as" \
    "$LOCAL/diagnose.as" \
    "$REMOTE/"

# Controller runtime files shipped in BOTH the updater tarball and the
# bootstrap zip. VERSION (the deploy stamp) is added separately.
CONTROLLER_FILES=(controller.as deviceControl.as simulator.as \
                  diagnose.as zigbee-bridge.py zigbee-pair.py rbr-dashboard.py \
                  heatlog.py dashboard.txt rbr-updater.py)

# Versioned controller tarball for the standalone updater (rbr-updater.py).
# Contains the controller runtime files with a VERSION stamp embedded;
# controllers only apply it when the stamp is newer than their local
# .version. Built after the version stamp is final so a --release tarball
# carries the new stamp. See doc/UPDATE-MECHANISM.md.
build_controller_tarball() {
    local BUILD_DIR
    BUILD_DIR="$(mktemp -d)"
    for f in "${CONTROLLER_FILES[@]}"; do
        cp "$LOCAL/$f" "$BUILD_DIR/"
    done
    cp "$LOCAL/version" "$BUILD_DIR/VERSION"
    tar -C "$BUILD_DIR" -czf "$LOCAL/rbr-controller.tar.gz" .
    rm -rf "$BUILD_DIR"
    echo "  → $LOCAL/rbr-controller.tar.gz (version $(cat "$LOCAL/version"))"
}

upload_controller_tarball() {
    echo "Building controller update tarball..."
    build_controller_tarball
    echo "Uploading rbr-controller.tar.gz..."
    rsync -vz --no-perms -e "$SSH_OPTS" "$LOCAL/rbr-controller.tar.gz" "$REMOTE/"
}

# Bootstrap install pack: the same runtime files plus rbr-setup.sh (so a
# fresh machine can install the services) and the VERSION stamp. Fetched
# by get-controller.sh when setting up a new controller.
build_controller_zip() {
    local BUILD_DIR
    BUILD_DIR="$(mktemp -d)"
    for f in "${CONTROLLER_FILES[@]}" rbr-setup.sh; do
        cp "$LOCAL/$f" "$BUILD_DIR/"
    done
    cp "$LOCAL/version" "$BUILD_DIR/VERSION"
    (cd "$BUILD_DIR" && zip -q "$LOCAL/rbr-controller.zip" \
        controller.as deviceControl.as simulator.as diagnose.as zigbee-bridge.py \
        zigbee-pair.py rbr-dashboard.py heatlog.py dashboard.txt rbr-updater.py \
        rbr-setup.sh VERSION)
    rm -rf "$BUILD_DIR"
    echo "  → $LOCAL/rbr-controller.zip (version $(cat "$LOCAL/version"))"
}

upload_controller_pack() {
    echo "Building controller install pack..."
    build_controller_zip
    echo "Uploading rbr-controller.zip + get-controller.sh..."
    rsync -vz --no-perms -e "$SSH_OPTS" "$LOCAL/rbr-controller.zip" "$REMOTE/"
    rsync -vz --no-perms -e "$SSH_OPTS" "$LOCAL/get-controller.sh" "$REMOTE/"
}

if [[ $RELEASE -eq 1 ]]; then
    # Bump and publish the version stamp. Format YYMMDDHHMM gives multiple
    # releases per day distinct, monotonically-increasing values that
    # compare correctly as integers in rbr-updater.py.
    NEW_VERSION="$(date +%y%m%d%H%M)"
    echo "$NEW_VERSION" > "$LOCAL/version"
    echo "Releasing version $NEW_VERSION..."
    # The tarball/zip are built AFTER the bump so they embed the new
    # stamp; /version is uploaded last so mid-check controllers never see
    # a new stamp paired with stale .as source.
    upload_controller_tarball
    upload_controller_pack
    rsync -vz --no-perms -e "$SSH_OPTS" "$LOCAL/version" "$REMOTE/"
    echo "Done. Controllers will pick up version $NEW_VERSION on their next hourly check."
else
    # No version bump: the tarball keeps the last release stamp, so
    # controllers that already have it will skip it. Safe to iterate.
    upload_controller_tarball
    upload_controller_pack
    echo "Done. Files uploaded; version stamp unchanged. Run with --release to publish to customers."
fi
