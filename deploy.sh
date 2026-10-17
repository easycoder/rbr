#!/usr/bin/env bash
# Deploy RBR web UI + controller files to rbrheating.com.
#
# Layout on the server:
#   /                   <- legacy UI entry points (index.html, auth.php, ...).
#                          Left running, unchanged, until it is deleted; the
#                          root is to become a product-information home page.
#   /resources/         <- legacy UI resources (as above)
#   /new-ui/            <- the PWA's old home. Still published, byte-identical
#                          to /heat/, until this folder is deleted.
#   /docs/              <- documentation reader — the page, the script and the
#                          layout. The documentation itself is fetched from the
#                          public repository at runtime, never copied here.
#   /dist/              <- pinned AllSpeak runtime, written by pin-allspeak.sh
#                          (not by this script)
#
#   /heat/              <- THE OPERATIONAL SET. Everything the controller and
#                          the UI need from this site, and the product's home
#                          from now on:
#     /heat/index.html, sw.js, manifest.webmanifest, icons/, resources/
#                          <- the PWA — the same files as new-ui/
#     /heat/controller.allspeak, deviceControl.allspeak,
#     /heat/simulator.allspeak, diagnose.allspeak
#                          <- AllSpeak controller source
#     /heat/rbr-controller.tar.gz
#                          <- versioned bundle of ALL controller runtime
#                          files, pulled by the standalone updater
#                          (rbr-updater.py) — see doc/UPDATE-MECHANISM.md
#     /heat/rbr-controller.zip
#                          <- same files + rbr-setup.sh + VERSION: the
#                          install pack fetched by get-controller.sh when
#                          setting up a new controller
#     /heat/get-controller.sh
#                          <- bootstrap downloader: wget it, run it, it
#                          fetches and unpacks rbr-controller.zip
#     /heat/version        <- single-line version stamp; bumping this (with
#                          --release) makes controllers apply the tarball
#
# auth.php, credentials.php and .htaccess deliberately stay at the site root and
# are NOT copied into /heat/. They read ../rbr-users.json, which is kept outside
# the web root on purpose; one level deeper would put that file inside the tree
# that is served. Both UIs reach them by the same paths from either location —
# credentials.php is one level above the page, relative, and /verify, /register
# and /recover are absolute.
#
# Usage:
#   ./deploy.sh             upload UI + .allspeak files; do NOT bump the version.
#                           Customers keep their current version until you
#                           release. Safe to run during iteration; smoke-test
#                           on your own IXHUB by scp'ing controller.allspeak
#                           directly before publishing.
#
#   ./deploy.sh --release   upload everything as above, then bump and push
#                           the version stamp. IXHUBs pick up the new .allspeak
#                           files on their next hourly CheckForUpdate.
#
# The version file is uploaded LAST so a controller mid-check never sees a
# new version paired with stale source.
set -euo pipefail

REMOTE="rbrheating@rbrheating.com:/home/rbrheating/rbrheating.com"
HEAT="$REMOTE/heat"
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
for dir in allspeak css icon img json webson; do
    echo "  resources/$dir"
    rsync -rvz --no-perms --delete -e "$SSH_OPTS" \
        "$LOCAL/resources/$dir/" \
        "$REMOTE/resources/$dir/"
done

# New UI tree (PWA). One rsync of the whole new-ui/ directory keeps it
# in lock-step with the local copy, including shell.allspeak, sw.js, webson
# templates, icons and the manifest. --delete prunes anything removed
# locally so stale files can't linger on the server.
echo "Deploying new-ui/..."
# -p with --chmod, not --no-perms: --chmod has no effect on a file that
# already exists on the receiver unless permissions are being set. The chmod
# makes the result deterministic — files 0644, directories 0755 — whatever the
# sending side happens to hold, so a stray 0640 file cannot leave a page
# unreadable behind a 403.
rsync -rvz -p --delete --chmod=F644,D755 -e "$SSH_OPTS" \
    "$LOCAL/new-ui/" \
    "$REMOTE/new-ui/"

# The documentation reader: the whole of /docs on the site — the page, the
# script and the layout. The documentation itself is NOT here and is never
# copied. The reader fetches the Markdown from the public repository at
# runtime, so docs/ in this repository stays the only copy of it.
echo "Deploying docs-reader/ to /docs/..."
rsync -rvz --no-perms --delete -e "$SSH_OPTS" \
    "$LOCAL/docs-reader/" \
    "$REMOTE/docs/"

# Controller AllSpeak source files, the update tarball and the install pack all
# go into /heat/ — see upload_heat() below. The old root copies are left on the
# server as they are; nothing refreshes them.

# Controller runtime files shipped in BOTH the updater tarball and the
# bootstrap zip. VERSION (the deploy stamp) is added separately.
CONTROLLER_FILES=(controller.allspeak deviceControl.allspeak simulator.allspeak \
                  diagnose.allspeak zigbee-bridge.py zigbee-pair.py zigbee-mesh.py \
                  rbr-dashboard.py heatlog.py dashboard.txt rbr-updater.py \
                  rbr-watchdog.sh rbr-mapbackup.py)

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
}

# Assemble /heat/ locally, then push it as one tree.
#
# The PWA and the controller files share the directory and the sync is
# --delete, so the tree is built in a temp dir first: rsyncing new-ui/ straight
# into /heat/ would delete the controller files already sitting there, and
# rsyncing those back afterwards would then defeat the pruning.
#
# `version` is excluded from the tree sync and uploaded on its own afterwards,
# so a controller mid-check never sees a fresh stamp paired with stale source —
# the guarantee the old script got by uploading /version last.
upload_heat() {
    local BUILD_DIR
    BUILD_DIR="$(mktemp -d)"
    mkdir -p "$BUILD_DIR/heat"
    # The PWA — byte-identical to what /new-ui/ gets.
    rsync -a "$LOCAL/new-ui/" "$BUILD_DIR/heat/"
    # Controller source and the artifacts fetched from this site.
    cp "$LOCAL/controller.allspeak" \
       "$LOCAL/deviceControl.allspeak" \
       "$LOCAL/simulator.allspeak" \
       "$LOCAL/diagnose.allspeak" \
       "$LOCAL/rbr-controller.tar.gz" \
       "$LOCAL/rbr-controller.zip" \
       "$LOCAL/get-controller.sh" \
       "$BUILD_DIR/heat/"
    echo "Uploading /heat/ (PWA + controller files)..."
    rsync -rz -p --delete --exclude=version --chmod=F644,D755 -e "$SSH_OPTS" \
        "$BUILD_DIR/heat/" "$HEAT/"
    rm -rf "$BUILD_DIR"
}

upload_heat_version() {
    rsync -vz --no-perms -e "$SSH_OPTS" "$LOCAL/version" "$HEAT/"
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
        controller.allspeak deviceControl.allspeak simulator.allspeak diagnose.allspeak zigbee-bridge.py \
        zigbee-pair.py zigbee-mesh.py rbr-dashboard.py heatlog.py dashboard.txt \
        rbr-updater.py rbr-watchdog.sh rbr-mapbackup.py rbr-setup.sh VERSION)
    rm -rf "$BUILD_DIR"
    echo "  → $LOCAL/rbr-controller.zip (version $(cat "$LOCAL/version"))"
}

upload_controller_pack() {
    echo "Building controller install pack..."
    build_controller_zip
}

if [[ $RELEASE -eq 1 ]]; then
    # Bump and publish the version stamp. Format YYMMDDHHMM gives multiple
    # releases per day distinct, monotonically-increasing values that
    # compare correctly as integers in rbr-updater.py.
    NEW_VERSION="$(date +%y%m%d%H%M)"
    echo "$NEW_VERSION" > "$LOCAL/version"
    echo "Releasing version $NEW_VERSION..."
    # The tarball/zip are built AFTER the bump so they embed the new stamp,
    # and /heat/version is uploaded after the tree so mid-check controllers
    # never see a new stamp paired with stale .allspeak source.
    upload_controller_tarball
    upload_controller_pack
    upload_heat
    upload_heat_version
    echo "Done. Controllers will pick up version $NEW_VERSION on their next hourly check."
else
    # No version bump: the tarball keeps the last release stamp, so
    # controllers that already have it will skip it. Safe to iterate.
    upload_controller_tarball
    upload_controller_pack
    upload_heat
    echo "Done. Files uploaded; version stamp unchanged. Run with --release to publish to customers."
fi

cat <<'EOF'

Reminders:
- The documentation reader at /docs follows the AllSpeak build pinned at
  /dist/allspeak.js. After a pin, bump the ?v= in docs-reader/index.html as
  well as the one in index.html, or a browser can hold the old runtime.
- The reader's documentation pages are not deployed with it. They come from
  https://raw.githubusercontent.com/easycoder/rbr/main/docs/ as they are read,
  so a documentation change needs only a commit and a push — no deploy.
EOF
