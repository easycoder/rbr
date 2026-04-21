#!/bin/bash
# Start test infrastructure, run the Advance/Boost (ops) Playwright tests, clean up.
# Assumes `run-setup-tests.sh` has already been run at least once so that map-sim.json
# exists with the 4 rooms configured by the setup specs. Unlike run-setup-tests.sh
# this script preserves the existing map so ops tests can operate on it.
#
# Usage: ./tests/run-ops-tests.sh [playwright args...]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PIDS=()
MOSQUITTO_CONF="/etc/mosquitto/conf.d/rbr-test.conf"

cleanup() {
    echo ""
    echo "Shutting down test services..."
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
    rm -f "$SCRIPT_DIR/params.json" "$SCRIPT_DIR/thermometers.json"
    echo "Done."
}
trap cleanup EXIT

if ! command -v mosquitto &>/dev/null; then
    echo "Error: mosquitto is not installed. Run: sudo apt install mosquitto"
    exit 1
fi
if ! command -v allspeak &>/dev/null; then
    echo "Error: allspeak is not installed."
    exit 1
fi
if [ ! -f "$SCRIPT_DIR/map-sim.json" ]; then
    echo "Error: $SCRIPT_DIR/map-sim.json is missing."
    echo "Run ./tests/run-setup-tests.sh first to build the map with the setup specs."
    exit 1
fi

echo "Starting mosquitto broker..."
sudo systemctl stop mosquitto 2>/dev/null || true
sudo cp "$SCRIPT_DIR/mosquitto-test.conf" "$MOSQUITTO_CONF"
sudo systemctl start mosquitto
sleep 1

lsof -ti:9000 | xargs -r kill 2>/dev/null || true
echo "Starting HTTP server on port 9000..."
python3 -m http.server 9000 --directory "$SCRIPT_DIR" 2>/dev/null &
PIDS+=($!)
sleep 1

pkill -f "allspeak controller.as" 2>/dev/null || true
sleep 1
cp "$PROJECT_DIR/controller.as" "$SCRIPT_DIR/controller.as"
cp "$PROJECT_DIR/simulator.as" "$SCRIPT_DIR/simulator.as"
cp "$PROJECT_DIR/deviceControl.as" "$SCRIPT_DIR/deviceControl.as"
# Test-only patch: treat boost duration as seconds instead of minutes so a
# click on "1 hr" expires in 60 real seconds. Matches the lone
# `multiply T by 60000$` on the boost-request path (controller.as:1259);
# the other 60000 occurrences end with ` giving Time` so are unaffected.
sed -i 's/multiply T by 60000$/multiply T by 1000/' "$SCRIPT_DIR/controller.as"
# NOTE: do not delete map-sim.json — ops tests run against the setup map.
rm -f "$SCRIPT_DIR/params.json" "$SCRIPT_DIR/thermometers.json"
echo "Starting controller with simulator..."
cd "$SCRIPT_DIR"
allspeak controller.as &
CONTROLLER_PID=$!
cd "$PROJECT_DIR"

sleep 3

echo ""
echo "All services running. Starting ops tests..."
echo ""

npx playwright test tests/ops-*.spec.js "$@"
TEST_EXIT=$?

echo ""
echo "Waiting for controller to save map..."
sleep 65

exit $TEST_EXIT
