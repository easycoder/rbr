#!/usr/bin/env bash
# Pin the current local dist/allspeak.js as the version RBR loads in production.
# Kept deliberately separate from deploy.sh so the pinned copy only moves when
# you explicitly promote a known-good AllSpeak build.
#
# Workflow:
#   1. In ~/dev/allspeak: make changes, build, test (RBR tests, etc.)
#   2. When satisfied, run this script — it rsyncs dist/allspeak.js to
#      rbrheating.com/dist/allspeak.js
#   3. Bump the ?v=... cache-buster in index.html and deploy.sh as usual
set -euo pipefail

ALLSPEAK_JS="$HOME/dev/allspeak/dist/allspeak.js"
REMOTE="rbrheating@rbrheating.com:/home/rbrheating/rbrheating.com/dist/"

if [ ! -f "$ALLSPEAK_JS" ]; then
    echo "Error: $ALLSPEAK_JS not found. Run ./build-allspeak in ~/dev/allspeak first."
    exit 1
fi

echo "Pinning $(basename "$ALLSPEAK_JS") ($(stat -c%s "$ALLSPEAK_JS") bytes) to ${REMOTE}"
rsync -vz --no-perms "$ALLSPEAK_JS" "$REMOTE"
echo "Done. Remember to bump ?v= in index.html so browsers refetch."
