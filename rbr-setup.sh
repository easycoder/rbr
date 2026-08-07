#!/bin/bash
#
# rbr-setup.sh — one-shot setup for RBR on a fresh Debian/Ubuntu/Neon machine
#
# Installs and configures:
#   • Mosquitto (local MQTT broker with WebSocket + cloud bridge)
#   • Zigbee2MQTT (for the SONOFF Zigbee dongle)
#   • RBR zigbee-bridge (HTTP↔MQTT bridge for the controller)
#   • Controller credentials (pointing at local Mosquitto)
#
# Usage:
#   sudo ./rbr-setup.sh
#
# You'll be prompted for:
#   • MQTT password (from rbrheating.com credentials — you have this)
#   • MAC address of the controller (the MQTT topic identifier)
#
# On a fresh machine, run this from the rbr repo directory (~/rbr/).
#
set -euo pipefail

# ---------------------------------------------------------------------------
# Config — adjust these to match your machine
# ---------------------------------------------------------------------------
RBR_DIR="$(cd "$(dirname "$0")" && pwd)"
RBR_USER="$(stat -c '%U' "$RBR_DIR" 2>/dev/null || echo 'graham')"
DONGLE_DEVICE="/dev/ttyUSB0"

Z2M_DIR="/opt/zigbee2mqtt"
Z2M_USER="zigbee2mqtt"

MOSQUITTO_CONF="/etc/mosquitto/conf.d/rbr-local.conf"
WS_PORT=9001

# ---------------------------------------------------------------------------
# Helper: confirm before proceeding
# ---------------------------------------------------------------------------
confirm() {
    echo ""
    echo "─── $* ───"
    echo ""
}

prompt_value() {
    local label="$1" var_name="$2" default="${3:-}"
    local val
    if [[ -n "$default" ]]; then
        read -r -p "$label [$default]: " val
        echo "${val:-$default}"
    else
        read -r -p "$label: " val
        echo "$val"
    fi
}

# ---------------------------------------------------------------------------
# Must be root
# ---------------------------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (use sudo)."
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  RBR Full Setup — $(date)"
echo "═══════════════════════════════════════════════════════"
echo "  Repo dir:     $RBR_DIR"
echo "  User:         $RBR_USER"
echo "  Dongle:       $DONGLE_DEVICE"
echo "  Zigbee2MQTT:  $Z2M_DIR"
echo ""

# ===========================================================================
# COLLECT CREDENTIALS
# ===========================================================================
confirm "Step 0 — Credentials"

# Read MQTT password
MQTT_PASSWORD=""
if [[ -f "$RBR_DIR/.mqtt_password" ]]; then
    MQTT_PASSWORD="$(cat "$RBR_DIR/.mqtt_password")"
    echo "  Using existing .mqtt_password"
elif [[ -f ~/.mqtt_password ]]; then
    MQTT_PASSWORD="$(cat ~/.mqtt_password)"
    echo "  Using existing ~/.mqtt_password"
fi
if [[ -z "$MQTT_PASSWORD" ]]; then
    echo ""
    echo "  You need the MQTT password from your RBR credentials."
    echo "  It's the 'password' field from https://rbrheating.com/credentials.php"
    echo "  (or from the credentials.example.json file in the repo)."
    echo ""
    MQTT_PASSWORD="$(prompt_value "  Enter MQTT password" "pw")"
fi
echo "$MQTT_PASSWORD" > "$RBR_DIR/.mqtt_password"
chown "$RBR_USER:$RBR_USER" "$RBR_DIR/.mqtt_password"
chmod 600 "$RBR_DIR/.mqtt_password"
echo "  → Saved $RBR_DIR/.mqtt_password"

# MQTT username (defaults to "rbr")
MQTT_USERNAME="$(prompt_value "  MQTT username" "user" "rbr")"

# MAC address — the MQTT topic that identifies this controller
DEFAULT_MAC="$(ip link show "$(ip route show default | awk '{print $5}')" 2>/dev/null | awk '/ether/ {print $2}' || echo "")"
MAC="$(prompt_value "  Controller MAC address" "mac" "$DEFAULT_MAC")"
echo "$MAC" > "$RBR_DIR/.mac_override"
chown "$RBR_USER:$RBR_USER" "$RBR_DIR/.mac_override"
echo "  → Saved $RBR_DIR/.mac_override"

# ===========================================================================
# STEP 1 — Install system packages
# ===========================================================================
confirm "Step 1 — Installing system packages"

apt-get update -qq
apt-get install -y \
    mosquitto mosquitto-clients \
    git make g++ gcc libsystemd-dev \
    python3-pip curl ca-certificates

# Install Python MQTT library for the bridge
pip3 install paho-mqtt 2>/dev/null || pip3 install --break-system-packages paho-mqtt 2>/dev/null || true

# Ensure Node.js is recent enough for Zigbee2MQTT (needs >= 18, but pnpm needs >= 22)
NODE_MAJOR="$(node --version 2>/dev/null | sed 's/v//; s/\..*//')"
if [[ -z "$NODE_MAJOR" || "$NODE_MAJOR" -lt 22 ]]; then
    echo "  Node.js v$(node --version 2>/dev/null || echo 'none') too old — installing Node.js 22.x..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
    apt-get install -y nodejs
    echo "  Node.js $(node --version) installed"
fi

# Install pnpm for Zigbee2MQTT build
npm install -g pnpm 2>/dev/null || true

echo "  Done."

# ===========================================================================
# STEP 2 — Configure Mosquitto (local broker + cloud bridge)
# ===========================================================================
confirm "Step 2 — Configuring Mosquitto"

systemctl enable mosquitto

cat > "$MOSQUITTO_CONF" << CONF
# RBR local configuration — generated by rbr-setup.sh

# Local MQTT for controller, zigbee2mqtt, zigbee-bridge
listener 1883
allow_anonymous true

# WebSocket listener for browser UI
listener ${WS_PORT}
protocol websockets
allow_anonymous true

# Bridge to cloud broker — messages flow both ways
connection rbr-cloud
address rbrheating.duckdns.org:8883
remote_username ${MQTT_USERNAME}
remote_password ${MQTT_PASSWORD}
bridge_capath /etc/ssl/certs
topic # both 0
bridge_protocol_version mqttv311
CONF

echo "  → Installed $MOSQUITTO_CONF"
systemctl restart mosquitto
echo "  → Mosquitto restarted (port 1883, ws://$WS_PORT, bridge to cloud)"

# Wait for Mosquitto to be ready
sleep 1
if systemctl is-active --quiet mosquitto; then
    echo "  ✓ Mosquitto is running"
else
    echo "  ⚠ Mosquitto failed to start — check: journalctl -u mosquitto -n 20"
fi

# ===========================================================================
# STEP 3 — Install Zigbee2MQTT
# ===========================================================================
confirm "Step 3 — Installing Zigbee2MQTT"

# Create dedicated user
if ! id "$Z2M_USER" &>/dev/null; then
    useradd -r -s /usr/sbin/nologin -d "$Z2M_DIR" "$Z2M_USER"
    echo "  Created user $Z2M_USER"
fi
usermod -aG dialout "$Z2M_USER"

# Clone or update
# Mark as safe for git (handles root-then-user access)
git config --global --add safe.directory "$Z2M_DIR" 2>/dev/null || true

if [[ -d "$Z2M_DIR/.git" ]]; then
    echo "  $Z2M_DIR already exists — updating..."
    cd "$Z2M_DIR"
    git pull --ff-only
else
    echo "  Cloning Zigbee2MQTT..."
    git clone --depth 1 https://github.com/Koenkk/zigbee2mqtt.git "$Z2M_DIR"
    cd "$Z2M_DIR"
fi

# Install dependencies
echo "  Running pnpm install (needs dev deps for TypeScript build)..."
cd "$Z2M_DIR"
pnpm install 2>&1 | tail -5
echo "  pnpm install done"

# Create configuration
RESOLVED_DONGLE="$(readlink -f "$DONGLE_DEVICE" 2>/dev/null || echo "$DONGLE_DEVICE")"
mkdir -p "$Z2M_DIR/data"
cat > "$Z2M_DIR/data/configuration.yaml" << YAML
# Zigbee2MQTT configuration for RBR — generated by rbr-setup.sh

homeassistant: false

mqtt:
  base_topic: zigbee2mqtt
  server: mqtt://localhost:1883

serial:
  port: ${RESOLVED_DONGLE}
  adapter: ezsp

frontend:
  port: 8080
  host: 0.0.0.0

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
echo "  → Created $Z2M_DIR/data/configuration.yaml (dongle: $RESOLVED_DONGLE)"

# Create systemd service
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

systemctl daemon-reload
systemctl enable zigbee2mqtt.service
echo "  → Created and enabled zigbee2mqtt.service"

# ===========================================================================
# STEP 4 — RBR zigbee-bridge
# ===========================================================================
confirm "Step 4 — Setting up RBR zigbee-bridge"

# Create zigbee-config.json for the bridge
cat > "$RBR_DIR/zigbee-config.json" << JSON
{
    "_doc": "Zigbee bridge config — generated by rbr-setup.sh",
    "broker": "localhost",
    "port": 1883,
    "http_port": 8889,
    "username": "${MQTT_USERNAME}",
    "password": "${MQTT_PASSWORD}",
    "tls": false
}
JSON
chown "$RBR_USER:$RBR_USER" "$RBR_DIR/zigbee-config.json"
echo "  → Created $RBR_DIR/zigbee-config.json"

# Create systemd service
cat > /etc/systemd/system/rbr-zigbee-bridge.service << SERVICE
[Unit]
Description=RBR Zigbee Bridge (HTTP/MQTT)
After=mosquitto.service zigbee2mqtt.service
Wants=mosquitto.service zigbee2mqtt.service

[Service]
Type=simple
User=${RBR_USER}
WorkingDirectory=${RBR_DIR}
ExecStart=/usr/bin/python3 ${RBR_DIR}/zigbee-bridge.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable rbr-zigbee-bridge.service
echo "  → Created and enabled rbr-zigbee-bridge.service"

# ===========================================================================
# STEP 5 — Create controller credentials file (local broker)
# ===========================================================================
confirm "Step 5 — Creating controller credentials"

cat > "$RBR_DIR/credentials" << JSON
{
    "broker": "localhost",
    "port": 1883,
    "username": "${MQTT_USERNAME}",
    "password": "${MQTT_PASSWORD}",
    "mail_server": "smtp.example.com",
    "mail_login": "noreply@rbrheating.com",
    "mail_password": "",
    "mail_from": "noreply@rbrheating.com"
}
JSON
chown "$RBR_USER:$RBR_USER" "$RBR_DIR/credentials"
chmod 640 "$RBR_DIR/credentials"
echo "  → Created $RBR_DIR/credentials (broker: localhost, MAC: $MAC)"
echo "  Note: mail credentials are placeholders — update if you need email features."

# =========================================================================--
# STEP 6 — RBR updater (automatic code updates)
# =========================================================================--
confirm "Step 6 — Installing RBR updater (automatic updates)"

if [[ ! -f "$RBR_DIR/rbr-updater.py" ]]; then
    echo "  ⚠ rbr-updater.py not found in $RBR_DIR — skipping updater install"
    echo "    (copy it from the repo if you want automatic updates)"
else
    chown "$RBR_USER:$RBR_USER" "$RBR_DIR/rbr-updater.py"

    cat > /etc/systemd/system/rbr-updater.service << SERVICE
[Unit]
Description=RBR controller updater (one-shot)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
# Runs as root so it can restart the controller/bridge services after an
# update. Only replaces code files in ${RBR_DIR}; machine-specific data
# (credentials, .mac_override, map.json, ...) is never touched.
ExecStart=/usr/bin/python3 ${RBR_DIR}/rbr-updater.py
SERVICE

    cat > /etc/systemd/system/rbr-updater.timer << TIMER
[Unit]
Description=Run the RBR updater hourly

[Timer]
OnCalendar=hourly
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
TIMER

    systemctl daemon-reload
    systemctl enable rbr-updater.timer
    systemctl start rbr-updater.timer
    echo "  → rbr-updater.timer enabled (hourly check for rbr-controller.tar.gz)"
fi

# =========================================================================--
# STEP 7 — (optional) Local UI web server
# =========================================================================--
confirm "Step 7 — Local UI web server (optional)"

INSTALL_UI=""
read -r -p "  Install a local web server for the UI? (y/N): " INSTALL_UI
if [[ "${INSTALL_UI,,}" == "y" ]]; then
    UI_PORT="$(prompt_value "  Web server port" "ui_port" "8082")"

    cat > /etc/systemd/system/rbr-ui.service << SERVICE
[Unit]
Description=RBR Local UI Web Server
After=network.target mosquitto.service

[Service]
Type=simple
User=${RBR_USER}
WorkingDirectory=${RBR_DIR}
ExecStart=/usr/bin/python3 -m http.server ${UI_PORT}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

    systemctl daemon-reload
    systemctl enable rbr-ui.service
    systemctl restart rbr-ui.service
    echo "  → rbr-ui.service on port $UI_PORT — http://localhost:$UI_PORT/index.html"

    # Create credentials.json for the UI (same structure the UI expects)
    cat > "$RBR_DIR/credentials.json" << JSON
{
    "broker": "localhost",
    "port": ${WS_PORT},
    "username": "${MQTT_USERNAME}",
    "password": "${MQTT_PASSWORD}",
    "mac": "${MAC}"
}
JSON
    chown "$RBR_USER:$RBR_USER" "$RBR_DIR/credentials.json"
    chmod 640 "$RBR_DIR/credentials.json"
    # Also copy into new-ui/ so the relative URL /new-ui/credentials.json resolves
    cp "$RBR_DIR/credentials.json" "$RBR_DIR/new-ui/credentials.json"
    chown "$RBR_USER:$RBR_USER" "$RBR_DIR/new-ui/credentials.json"
    echo "  → Created $RBR_DIR/credentials.json for the UI (WebSocket on port $WS_PORT)"
fi

# =========================================================================--
# STEP 8 — (optional) Run the controller as a systemd service
# ===========================================================================
confirm "Step 8 — Controller systemd service (optional)"

INSTALL_CTRL=""
read -r -p "  Run the controller as a service (auto-restart after updates)? (y/N): " INSTALL_CTRL
if [[ "${INSTALL_CTRL,,}" == "y" ]]; then
    # Locate the allspeak binary. When run under sudo, root's PATH often
    # misses the user's ~/.local/bin where allspeak lives.
    ALLSPEAK_BIN="$(command -v allspeak 2>/dev/null || true)"
    if [[ -z "$ALLSPEAK_BIN" && -x "/home/$RBR_USER/.local/bin/allspeak" ]]; then
        ALLSPEAK_BIN="/home/$RBR_USER/.local/bin/allspeak"
    fi
    if [[ -z "$ALLSPEAK_BIN" ]]; then
        echo "  ⚠ Could not find the allspeak binary — skipping controller service"
    else
        cat > /etc/systemd/system/controller.service << SERVICE
[Unit]
Description=RBR Controller
After=network-online.target mosquitto.service rbr-zigbee-bridge.service
Wants=network-online.target

[Service]
Type=simple
User=${RBR_USER}
WorkingDirectory=${RBR_DIR}
ExecStart=${ALLSPEAK_BIN} controller.as
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

        systemctl daemon-reload
        systemctl enable controller.service
        systemctl start controller.service
        echo "  → controller.service running as $RBR_USER (restarts automatically after updates)"
    fi
fi

# ===========================================================================
# START EVERYTHING
# ===========================================================================
confirm "Starting services"

echo "  Starting zigbee2mqtt..."
systemctl start zigbee2mqtt.service 2>/dev/null || echo "  ⚠ zigbee2mqtt may need the dongle connected — check with: journalctl -u zigbee2mqtt -n 20"

echo "  Starting rbr-zigbee-bridge..."
systemctl start rbr-zigbee-bridge.service 2>/dev/null || echo "  ⚠ bridge may need zigbee2mqtt running first"

# Give them a moment
sleep 2

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Setup complete!"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "  Services:"
echo "    mosquitto          $(systemctl is-active mosquitto)"
echo "    zigbee2mqtt        $(systemctl is-active zigbee2mqtt)"
echo "    rbr-zigbee-bridge  $(systemctl is-active rbr-zigbee-bridge)"
if [[ -f /etc/systemd/system/rbr-ui.service ]]; then
    echo "    rbr-ui             $(systemctl is-active rbr-ui)"
fi
if [[ -f /etc/systemd/system/rbr-updater.timer ]]; then
    echo "    rbr-updater.timer  $(systemctl is-active rbr-updater.timer)"
fi
echo ""
echo "  Controller:"
echo "    Credentials: $RBR_DIR/credentials (broker localhost:1883)"
echo "    MAC:         $MAC"
echo ""
echo "  Zigbee:"
echo "    Dongle:      $RESOLVED_DONGLE"
echo "    Web UI:      http://127.0.0.1:8080  (after zigbee2mqtt starts)"
echo "    Bridge API:  http://127.0.0.1:8889/health"
echo ""
echo "  Pair new devices:"
echo "    cd $RBR_DIR && python3 zigbee-pair.py"
echo ""
echo "  Check logs:"
echo "    sudo journalctl -u zigbee2mqtt -f"
echo "    sudo journalctl -u rbr-zigbee-bridge -f"
echo ""
echo "  Run the controller:"
echo "    cd $RBR_DIR && allspeak controller.as"
echo ""
echo "  Re-run this script on another machine:"
echo "    sudo ./rbr-setup.sh"
echo ""
