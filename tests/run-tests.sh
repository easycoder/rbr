#!/bin/bash
# Start test infrastructure, run Playwright tests, then clean up.
# Usage: ./tests/run-tests.sh [playwright args...]
#   e.g. ./tests/run-tests.sh --headed
#        ./tests/run-tests.sh --grep "banner"

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PIDS=()
MOSQUITTO_CONF="/etc/mosquitto/conf.d/rbr-test.conf"

cleanup() {
    echo ""
    echo "Shutting down test services..."
    # Kill the controller process tree
    if [ -n "$CONTROLLER_PID" ]; then
        # Kill all descendants then the process itself
        pkill -P "$CONTROLLER_PID" 2>/dev/null || true
        kill "$CONTROLLER_PID" 2>/dev/null || true
        wait "$CONTROLLER_PID" 2>/dev/null
    fi
    # Kill the HTTP server
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null && wait "$pid" 2>/dev/null
    done
    sudo systemctl stop mosquitto 2>/dev/null || true
    sudo rm -f "$MOSQUITTO_CONF"
    rm -f "$SCRIPT_DIR/params.json" "$SCRIPT_DIR/thermometers.json"
    echo "Done."
}
trap cleanup EXIT

# Check prerequisites
if ! command -v mosquitto &>/dev/null; then
    echo "Error: mosquitto is not installed. Run: sudo apt install mosquitto"
    exit 1
fi
if ! command -v allspeak &>/dev/null; then
    echo "Error: allspeak is not installed. Run: pip install allspeak"
    exit 1
fi

# 1. Start mosquitto via systemd (avoids AppArmor and permission issues)
echo "Starting mosquitto broker..."
sudo systemctl stop mosquitto 2>/dev/null || true
sudo cp "$SCRIPT_DIR/mosquitto-test.conf" "$MOSQUITTO_CONF"
sudo systemctl start mosquitto
sleep 1

# 2. Start HTTP server serving the tests directory
# Kill any leftover HTTP server from a previous run
lsof -ti:9000 | xargs -r kill 2>/dev/null || true
echo "Starting HTTP server on port 9000..."
python3 -m http.server 9000 --directory "$SCRIPT_DIR" &
PIDS+=($!)
sleep 1

# 3. Start the controller (with simulator) from the tests directory
# Copy controller scripts (symlinks don't work - AllSpeak resolves them)
cp "$PROJECT_DIR/controller.as" "$SCRIPT_DIR/controller.as"
cp "$PROJECT_DIR/simulator.as" "$SCRIPT_DIR/simulator.as"
cp "$PROJECT_DIR/deviceControl.as" "$SCRIPT_DIR/deviceControl.as"
# Clean state before starting so the controller loads a fresh empty map
rm -f "$SCRIPT_DIR/map-sim.json"
rm -f "$SCRIPT_DIR/params.json" "$SCRIPT_DIR/thermometers.json"
echo "Starting controller with simulator..."
cd "$SCRIPT_DIR"
allspeak controller.as &
CONTROLLER_PID=$!
cd "$PROJECT_DIR"

# Wait for the controller to connect to MQTT
sleep 3

echo ""
echo "All services running. Starting tests..."
echo ""

# 4. Run Playwright tests
npx playwright test "$@"
TEST_EXIT=$?

# Wait for the controller to save map-sim.json before shutting down
echo ""
echo "Waiting for controller to save map..."
sleep 65

exit $TEST_EXIT
