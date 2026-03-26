#!/usr/bin/env bash
# Deploy RBR web UI to rbrheating.com
set -euo pipefail

REMOTE="rbrheating@rbrheating.com:/home/rbrheating/rbrheating.com"
LOCAL="$(cd "$(dirname "$0")" && pwd)"

echo "Deploying RBR to ${REMOTE}..."

# Root-level web files
rsync -rvz --no-perms \
    "$LOCAL/index.html" \
    "$LOCAL/favicon.ico" \
    "$REMOTE/"

# Resources subdirectories — --delete keeps remote in sync with local
for dir in css easycoder ecs icon img json webson; do
    echo "  resources/$dir"
    rsync -rvz --no-perms --delete \
        "$LOCAL/resources/$dir/" \
        "$REMOTE/resources/$dir/"
done

echo "Done."
