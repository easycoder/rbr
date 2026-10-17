#!/usr/bin/env bash
#
# apply-retired-map.sh — swap map-retired.json (from retire-rbr-now.allspeak)
# over the live map.json, safely.
#
# Why this needs a script rather than a `mv`. The controller loads map.json
# once, at startup, and keeps it in memory; it writes the map back only when
# something in it changes (a relay failure count, a schedule event). So a swap
# under a running controller does not take effect, and the next write silently
# restores the very fields the migration removed. The swap has to happen while
# the controller is stopped, which is why this needs root.
#
#   0. validate the replacement map (a bad map must cost no downtime)
#   1. stop controller.service (only if it was running)
#   2. keep the old map as map.json.bak-<timestamp>
#   3. move map-retired.json into place as map.json, owned by its original user
#   4. start the controller again, and wait for it to settle
#   5. verify: the map has no retired fields, and the service is up
#
# Usage:  ./apply-retired-map.sh --dry-run [rbr-dir]
#         sudo ./apply-retired-map.sh [rbr-dir]      (default: this script's dir)

set -euo pipefail

DRY_RUN=no
ARGS=()
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=yes ;;
        -h|--help) sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) ARGS+=("$arg") ;;
    esac
done

RBR_DIR="$(cd "${ARGS[0]:-$(dirname "$0")}" && pwd)"
RETIRED="$RBR_DIR/map-retired.json"
LIVE="$RBR_DIR/map.json"

if [ ! -f "$RETIRED" ]; then
    echo "No $RETIRED — run 'allspeak retire-rbr-now.allspeak' in $RBR_DIR first." >&2
    exit 1
fi
if [ ! -f "$LIVE" ]; then
    echo "No $LIVE — this does not look like a controller directory." >&2
    exit 1
fi

# Validate a map before trusting it: shape, and none of the retired fields.
# Used on the replacement before anything is stopped, and on the live file
# afterwards — so a bad map costs an error message rather than downtime.
mapcheck() {
    python3 - "$1" <<'PYCHECK'
import json, sys
RETIRED_FIELDS = {"ssid", "password", "email", "message", "address", "extenders",
                  "controller-ssid", "controller-password", "user-password"}
try:
    m = json.load(open(sys.argv[1]))
except Exception as e:
    print("  does not parse: %s" % e)
    sys.exit(1)
present = RETIRED_FIELDS & set(m)
if present:
    print("  still carries retired fields: %s" % sorted(present))
    sys.exit(1)
profiles = m.get("profiles") or []
rooms = sum(len(p.get("rooms", {}) or {}) for p in profiles)
if not profiles or not rooms:
    print("  %d profile(s) and %d room entries — refusing" % (len(profiles), rooms))
    sys.exit(1)
print("  %d profile(s), %d room entries, no retired fields" % (len(profiles), rooms))
PYCHECK
}

echo "Replacement: $RETIRED"
if ! mapcheck "$RETIRED"; then
    echo "Refusing to install it." >&2
    exit 1
fi

if [ "$DRY_RUN" = yes ]; then
    echo "Dry run — nothing stopped, nothing moved."
    echo "Would: stop controller.service, keep the old map as map.json.bak-<timestamp>,"
    echo "       move map-retired.json into place, restart the controller, verify."
    exit 0
fi

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
    echo "This needs root — the controller service has to be stopped and started." >&2
    exit 1
fi

# The new file must be left owned by the owner of the existing map, or the
# controller (running as that user) cannot write the map back afterwards.
RBR_USER="$(stat -c %U "$LIVE")"

was_running=no
if systemctl is-active --quiet controller.service 2>/dev/null; then
    was_running=yes
fi

echo "RBR dir: $RBR_DIR"
echo "Controller was running: $was_running"

if [ "$was_running" = yes ]; then
    echo "Stopping controller.service so it cannot write the old map back..."
    systemctl stop controller.service
    # Restart=always means systemd may race us; confirm it is actually down.
    for _ in $(seq 1 10); do
        systemctl is-active --quiet controller.service || break
        sleep 1
    done
fi

BACKUP="$LIVE.bak-$(date +%Y%m%d-%H%M%S)"
cp -p "$LIVE" "$BACKUP"
echo "Old map kept as $(basename "$BACKUP")"

mv "$RETIRED" "$LIVE"
chown "$RBR_USER:" "$LIVE"
echo "map-retired.json is now map.json (owned by $RBR_USER)"

if [ "$was_running" = yes ]; then
    echo "Starting controller.service..."
    systemctl start controller.service
    sleep 10
fi

echo
echo "── verification ──"
if ! mapcheck "$LIVE"; then
    echo
    echo "The live map is wrong. Roll back with:"
    echo "  sudo systemctl stop controller.service"
    echo "  sudo cp -p '$BACKUP' '$LIVE'"
    echo "  sudo systemctl start controller.service"
    exit 1
fi

if [ "$was_running" = yes ]; then
    if systemctl is-active --quiet controller.service; then
        echo "  controller.service: active"
    else
        echo "  controller.service: NOT ACTIVE — check: journalctl -u controller -n 40"
        exit 1
    fi
fi

echo
echo "Done. The old map is at $BACKUP."
