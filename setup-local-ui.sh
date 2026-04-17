#!/bin/bash
#
# setup-local-ui.sh - Set up the RBR local UI on the controller
#
# Configures Mosquitto websocket, creates credentials,
# and enables a local web server so the UI works without internet.
#
# The web server serves directly from /home/linaro so UI files
# are edited in place with no copying needed.
#
# Run as root on the controller (e.g. over SSH).
#
# Usage: sudo ./setup-local-ui.sh
#

set -e

HOME_DIR="/home/linaro"
UI_PORT=8082
WS_PORT=9001

echo "=== RBR Local UI Setup ==="
echo ""

# Check we're root
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (use sudo)"
    exit 1
fi

# 1. Generate local credentials.json for the UI
echo "--- Generating credentials.json ---"

# Read credentials from the controller's credentials file
CRED_FILE="$HOME_DIR/credentials"
if [[ ! -f "$CRED_FILE" ]]; then
    echo "Error: Controller credentials file not found at $CRED_FILE"
    echo "Run the controller at least once so it fetches credentials, or create the file manually."
    exit 1
fi

# Extract username, password and mac from the controller credentials
USERNAME=$(python3 -c "import json; d=json.load(open('$CRED_FILE')); print(d.get('username','rbr'))")
PASSWORD=$(python3 -c "import json; d=json.load(open('$CRED_FILE')); print(d['password'])")

# Get MAC address (same logic as the controller)
if [[ -f "$HOME_DIR/.mac_override" ]]; then
    MAC=$(cat "$HOME_DIR/.mac_override" | tr -d '[:space:]')
else
    MAC=$(ip link show $(ip route show default | awk '{print $5}') | awk '/ether/ {print $2}')
fi

if [[ -z "$MAC" ]]; then
    echo "Error: Could not determine MAC address"
    exit 1
fi

MAC_TOPIC="${MAC}"

cat > "$HOME_DIR/credentials.json" << CRED
{
    "broker": "localhost",
    "port": ${WS_PORT},
    "username": "${USERNAME}",
    "password": "${PASSWORD}",
    "mac": "${MAC_TOPIC}"
}
CRED

chmod 640 "$HOME_DIR/credentials.json"
chown linaro:linaro "$HOME_DIR/credentials.json"
echo "  Created credentials.json (broker: localhost:$WS_PORT, mac: $MAC_TOPIC)"

# 2. Configure Mosquitto websocket listener
echo ""
echo "--- Configuring Mosquitto ---"

# Extract cloud broker details from controller credentials
# If already set to localhost (from a previous run), use the known cloud broker
CLOUD_BROKER=$(python3 -c "import json; d=json.load(open('$CRED_FILE')); b=d['broker']; print(b if b not in ('localhost','127.0.0.1') else d.get('cloud_broker','rbrheating.duckdns.org'))")
CLOUD_PORT=8883

# Websocket listener for local browser UI
MOSQUITTO_CONF="/etc/mosquitto/conf.d/rbr-local.conf"
cat > "$MOSQUITTO_CONF" << CONF
# RBR local configuration

# Default listener for local MQTT clients (controller, zigbee-bridge)
listener 1883
allow_anonymous true

# Websocket listener for local browser UI
listener $WS_PORT
protocol websockets
allow_anonymous true

# Bridge to cloud broker - messages flow both ways
connection rbr-cloud
address ${CLOUD_BROKER}:${CLOUD_PORT}
remote_username ${USERNAME}
remote_password ${PASSWORD}
bridge_capath /etc/ssl/certs
topic # both 0
bridge_protocol_version mqttv311
CONF

echo "  Installed $MOSQUITTO_CONF"
echo "  Websocket on port $WS_PORT"
echo "  Bridge to $CLOUD_BROKER:$CLOUD_PORT"
systemctl restart mosquitto
echo "  Mosquitto restarted"

# 3. Install and enable the UI web server service
echo ""
echo "--- Installing rbr-ui service ---"
cat > /etc/systemd/system/rbr-ui.service << SERVICE
[Unit]
Description=RBR Local UI Web Server
After=network.target mosquitto.service

[Service]
Type=simple
User=linaro
WorkingDirectory=${HOME_DIR}
ExecStart=/usr/bin/python3 -m http.server ${UI_PORT}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable rbr-ui.service
systemctl restart rbr-ui.service
echo "  rbr-ui service enabled and started on port $UI_PORT"

# 4. Point controller at local broker
echo ""
echo "--- Updating controller credentials ---"
python3 -c "
import json
with open('$CRED_FILE') as f:
    d = json.load(f)
if d['broker'] not in ('localhost', '127.0.0.1'):
    d['cloud_broker'] = d['broker']
d['broker'] = 'localhost'
d['port'] = 1883
with open('$CRED_FILE', 'w') as f:
    json.dump(d, f, indent=4)
"
echo "  Controller broker set to localhost (bridge handles cloud connectivity)"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Local UI available at: http://localhost:${UI_PORT}/index.html"
echo "MQTT websocket on:     ws://localhost:${WS_PORT}"
echo ""
echo "UI files are served directly from $HOME_DIR - edit in place."
