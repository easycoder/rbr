#!/bin/bash
#
# setup-zigbee2mqtt.sh - Install and configure Zigbee2MQTT on Debian
#
# For use with SONOFF Zigbee 3.0 USB Dongle Plus (EFR32MG21)
# Run as root or with sudo.
#
# Usage: sudo ./setup-zigbee2mqtt.sh [--dongle /dev/ttyACM0]
#

set -e

DONGLE_PATH="/dev/ttyACM0"
Z2M_DIR="/opt/zigbee2mqtt"
Z2M_USER="zigbee2mqtt"
MQTT_BROKER="localhost"
MQTT_PORT=1883

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --dongle) DONGLE_PATH="$2"; shift 2 ;;
        *) echo "Usage: $0 [--dongle /dev/ttyACM0]"; exit 1 ;;
    esac
done

echo "=== RBR Zigbee2MQTT Setup ==="
echo "Dongle path: $DONGLE_PATH"
echo ""

# Check we're root
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (use sudo)"
    exit 1
fi

# Check dongle exists
if [[ ! -e "$DONGLE_PATH" ]]; then
    echo "Warning: $DONGLE_PATH not found."
    echo "Plug in the SONOFF dongle and check with: ls /dev/ttyACM* /dev/ttyUSB*"
    echo "Then re-run with: sudo $0 --dongle /dev/ttyXXX"
    echo ""
    echo "Continuing with setup anyway (you can fix the config later)..."
    echo ""
fi

# 1. Install Node.js (if not present)
echo "--- Checking Node.js ---"
if command -v node &>/dev/null; then
    NODE_VER=$(node --version)
    echo "Node.js $NODE_VER already installed"
else
    echo "Installing Node.js 20.x..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
    echo "Node.js $(node --version) installed"
fi

# 2. Install dependencies
echo ""
echo "--- Installing dependencies ---"
apt-get install -y git make g++ gcc libsystemd-dev

# 3. Create zigbee2mqtt user if needed
if ! id "$Z2M_USER" &>/dev/null; then
    echo "Creating user $Z2M_USER..."
    useradd -r -s /usr/sbin/nologin -d "$Z2M_DIR" "$Z2M_USER"
fi

# Add user to dialout group for serial access
usermod -aG dialout "$Z2M_USER"

# 4. Install Zigbee2MQTT
echo ""
echo "--- Installing Zigbee2MQTT ---"
if [[ -d "$Z2M_DIR" ]]; then
    echo "$Z2M_DIR already exists. Updating..."
    cd "$Z2M_DIR"
    git pull
else
    git clone --depth 1 https://github.com/Koenkk/zigbee2mqtt.git "$Z2M_DIR"
    cd "$Z2M_DIR"
fi

npm ci

# 5. Install Mosquitto local MQTT broker
echo ""
echo "--- Installing Mosquitto ---"
apt-get install -y mosquitto
systemctl enable mosquitto

# 6. Create configuration
echo ""
echo "--- Creating configuration ---"
cat > "$Z2M_DIR/data/configuration.yaml" << YAML
# Zigbee2MQTT configuration for RBR heating system

homeassistant: false

mqtt:
  base_topic: zigbee2mqtt
  server: mqtt://${MQTT_BROKER}:${MQTT_PORT}

serial:
  port: ${DONGLE_PATH}
  adapter: zstack

frontend:
  port: 8080
  host: 127.0.0.1

advanced:
  log_level: info
  log_output:
    - console
  network_key: GENERATE
  pan_id: GENERATE
  channel: 15

availability: true
YAML

chown -R "$Z2M_USER:$Z2M_USER" "$Z2M_DIR"

# 7. Create systemd service
echo ""
echo "--- Creating systemd service ---"
cat > /etc/systemd/system/zigbee2mqtt.service << SERVICE
[Unit]
Description=Zigbee2MQTT
After=mosquitto.service
Wants=mosquitto.service

[Service]
Type=simple
User=${Z2M_USER}
WorkingDirectory=${Z2M_DIR}
ExecStart=/usr/bin/node index.js
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

# 8. Create udev rule for the SONOFF dongle
echo ""
echo "--- Creating udev rule ---"
cat > /etc/udev/rules.d/99-zigbee-dongle.rules << UDEV
# SONOFF Zigbee 3.0 USB Dongle Plus (Silicon Labs EFR32MG21)
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="zigbee-dongle", GROUP="dialout", MODE="0660"
UDEV

udevadm control --reload-rules
udevadm trigger

# 9. Also create systemd service for the RBR zigbee bridge
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/zigbee-bridge.py" ]]; then
    echo ""
    echo "--- Creating zigbee-bridge service ---"
    BRIDGE_USER=$(stat -c '%U' "$SCRIPT_DIR/zigbee-bridge.py")
    cat > /etc/systemd/system/rbr-zigbee-bridge.service << SERVICE
[Unit]
Description=RBR Zigbee Bridge (HTTP/MQTT)
After=mosquitto.service zigbee2mqtt.service
Wants=mosquitto.service zigbee2mqtt.service

[Service]
Type=simple
User=${BRIDGE_USER}
WorkingDirectory=${SCRIPT_DIR}
ExecStart=/usr/bin/python3 ${SCRIPT_DIR}/zigbee-bridge.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE
fi

# 10. Enable and start services
echo ""
echo "--- Enabling services ---"
systemctl daemon-reload
systemctl enable zigbee2mqtt.service

if [[ -f /etc/systemd/system/rbr-zigbee-bridge.service ]]; then
    systemctl enable rbr-zigbee-bridge.service
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Plug in the SONOFF Zigbee dongle"
echo "  2. Check it appears at: ls /dev/ttyACM* /dev/ttyUSB* /dev/zigbee-dongle"
echo "  3. If the path differs from $DONGLE_PATH, edit $Z2M_DIR/data/configuration.yaml"
echo "  4. Start Zigbee2MQTT:     sudo systemctl start zigbee2mqtt"
echo "  5. Check logs:            sudo journalctl -u zigbee2mqtt -f"
echo "  6. Start the bridge:      sudo systemctl start rbr-zigbee-bridge"
echo "  7. Pair devices:          python3 $SCRIPT_DIR/zigbee-pair.py"
echo ""
echo "Zigbee2MQTT web UI (local only): http://127.0.0.1:8080"
echo ""
