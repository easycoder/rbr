#!/bin/bash
# Start test infrastructure for manual browser testing.
# Open http://localhost:9000/index.html in your browser.
# Press Ctrl+C to shut everything down.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PIDS=()
MOSQUITTO_CONF="/etc/mosquitto/conf.d/rbr-test.conf"

cleanup() {
    echo ""
    echo "Shutting down..."
    # Kill the controller process tree
    if [ -n "$CONTROLLER_PID" ]; then
        pkill -P "$CONTROLLER_PID" 2>/dev/null || true
        kill "$CONTROLLER_PID" 2>/dev/null || true
        wait "$CONTROLLER_PID" 2>/dev/null
    fi
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null && wait "$pid" 2>/dev/null
    done
    sudo systemctl stop mosquitto 2>/dev/null || true
    sudo rm -f "$MOSQUITTO_CONF"
    rm -f "$SCRIPT_DIR/map.json" "$SCRIPT_DIR/map-sim.json"
    rm -f "$SCRIPT_DIR/params.json" "$SCRIPT_DIR/thermometers.json"
    echo "Done."
}
trap cleanup EXIT

# Check prerequisites
for cmd in mosquitto allspeak; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "Error: $cmd is not installed."
        exit 1
    fi
done

# Start mosquitto via systemd (avoids AppArmor and permission issues)
echo "Starting mosquitto..."
sudo systemctl stop mosquitto 2>/dev/null || true
sudo cp "$SCRIPT_DIR/mosquitto-test.conf" "$MOSQUITTO_CONF"
sudo systemctl start mosquitto
sleep 1

# Start HTTP server
lsof -ti:9000 | xargs -r kill 2>/dev/null || true
echo "Starting HTTP server on port 9000..."
python3 -m http.server 9000 --directory "$SCRIPT_DIR" &
PIDS+=($!)

# Copy controller scripts (symlinks don't work - AllSpeak resolves them)
cp "$PROJECT_DIR/controller.as" "$SCRIPT_DIR/controller.as"
cp "$PROJECT_DIR/simulator.as" "$SCRIPT_DIR/simulator.as"
cp "$PROJECT_DIR/deviceControl.as" "$SCRIPT_DIR/deviceControl.as"
echo "Starting controller..."
cd "$SCRIPT_DIR"
allspeak controller.as &
CONTROLLER_PID=$!
cd "$PROJECT_DIR"

sleep 2
echo ""
echo "Ready — open http://localhost:9000/index.html"
echo "Press Ctrl+C to stop."
wait
