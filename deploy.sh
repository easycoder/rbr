#!/usr/bin/env bash
# Deploy RBR web UI + controller files to rbrheating.com.
#
# Layout on the server:
#   /                   <- legacy UI entry points (index.html, auth.php, ...)
#   /resources/         <- legacy UI resources
#   /controller.as      <- AllSpeak controller source pulled by IXHUB
#   /deviceControl.as   <- ditto
#   /simulator.as       <- ditto
#   /version            <- single-line version stamp; bumping this triggers
#                          IXHUB's CheckForUpdate to pull the .as files
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

# Controller AllSpeak source files. Always pushed so the cloud copy is
# current, but customer IXHUBs won't pull them until the version bumps.
echo "Deploying controller files..."
rsync -vz --no-perms -e "$SSH_OPTS" \
    "$LOCAL/controller.as" \
    "$LOCAL/deviceControl.as" \
    "$LOCAL/simulator.as" \
    "$REMOTE/"

if [[ $RELEASE -eq 1 ]]; then
    # Bump and publish the version stamp. Format YYMMDDHHMM gives multiple
    # releases per day distinct, monotonically-increasing values that
    # compare correctly as integers in CheckForUpdate.
    NEW_VERSION="$(date +%y%m%d%H%M)"
    echo "$NEW_VERSION" > "$LOCAL/version"
    echo "Releasing version $NEW_VERSION..."
    rsync -vz --no-perms -e "$SSH_OPTS" "$LOCAL/version" "$REMOTE/"
    echo "Done. IXHUB controllers will pick up version $NEW_VERSION on their next hourly check."
else
    echo "Done. Files uploaded; version stamp unchanged. Run with --release to publish to customers."
fi
