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
# The Zigbee dongle is auto-detected (see detect_dongle below); this is
# only used as a last-resort default if detection finds nothing.
DONGLE_DEVICE=""

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

# ---------------------------------------------------------------------------
# Detect the Zigbee dongle. Preference order: the udev symlink this script
# creates on a previous run, then any /dev/ttyACM*, then /dev/ttyUSB*.
# ---------------------------------------------------------------------------
detect_dongle() {
    for dev in /dev/zigbee-dongle /dev/ttyACM* /dev/ttyUSB*; do
        [[ -e "$dev" ]] && { echo "$dev"; return; }
    done
}
# `|| true` matters: detect_dongle returns 1 when it finds nothing, and a
# bare assignment would inherit that status — with `set -e` that kills the
# script silently, before even the banner prints (and before Step 3's
# "no dongle detected" prompt, which is the path this is meant to reach).
DONGLE_DEVICE="$(detect_dongle || true)"

# AllSpeak is deliberately NOT installed by this script — it's a pip package
# that usually needs --break-system-packages, which is the operator's call.
# But we check for it so setup can warn early, and Step 8 reuses the result.
ALLSPEAK_BIN="$(command -v allspeak 2>/dev/null || true)"
if [[ -z "$ALLSPEAK_BIN" && -x "/home/$RBR_USER/.local/bin/allspeak" ]]; then
    ALLSPEAK_BIN="/home/$RBR_USER/.local/bin/allspeak"
fi
if [[ -z "$ALLSPEAK_BIN" ]]; then
    echo "  ⚠ AllSpeak is NOT installed — the controller cannot run without it."
    echo "    Install it as $RBR_USER:  pip install allspeak-ai"
    echo "    (add --break-system-packages if pip refuses)"
    echo ""
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  RBR Full Setup — $(date)"
echo "═══════════════════════════════════════════════════════"
echo "  Repo dir:     $RBR_DIR"
echo "  User:         $RBR_USER"
echo "  Dongle:       ${DONGLE_DEVICE:-not detected (prompted in Step 3)}"
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

# --- Zigbee dongle: prompt if not detected, create udev symlink -----------
if [[ -z "$DONGLE_DEVICE" ]]; then
    echo "  ⚠ No Zigbee dongle detected (/dev/ttyACM*, /dev/ttyUSB*)."
    DONGLE_DEVICE="$(prompt_value "  Enter dongle device path (or empty to skip)" "dongle" "")"
fi
if [[ -z "$DONGLE_DEVICE" ]]; then
    echo "  Skipping dongle configuration — Zigbee2MQTT won't start until you edit"
    echo "  the 'port:' line in $Z2M_DIR/data/configuration.yaml"
    RESOLVED_DONGLE="/dev/ttyACM0"
else
    # Stable /dev/zigbee-dongle symlink for the SONOFF Zigbee 3.0 dongle
    # (Silicon Labs CP210x), so a tty renumber after reboot can't break z2m.
    cat > /etc/udev/rules.d/99-zigbee-dongle.rules << 'UDEV'
# SONOFF Zigbee 3.0 USB Dongle Plus (Silicon Labs EFR32MG21)
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="zigbee-dongle", GROUP="dialout", MODE="0660"
UDEV
    udevadm control --reload-rules
    udevadm trigger
    [[ -e /dev/zigbee-dongle ]] && DONGLE_DEVICE="/dev/zigbee-dongle"
    RESOLVED_DONGLE="${DONGLE_DEVICE}"
    echo "  → Dongle: $RESOLVED_DONGLE"
fi

# Create configuration
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

# ===========================================================================
# STEP 5b — Heating-data log root (see doc/HEATING-DATA.md)
# ===========================================================================
# The controller writes room heating data (target/actual rows) under a root
# named by $RBR_DIR/heatlog-root. Prefer a dedicated partition mounted at
# /data/rbr-heating. Where none exists yet, a symlink at that path to a
# folder on the root disk keeps the configured path identical everywhere.
HEATLOG_ROOT="${HEATLOG_ROOT:-/data/rbr-heating}"
if [[ -f "$RBR_DIR/heatlog-root" ]]; then
    echo "  → heatlog-root already configured: $(cat "$RBR_DIR/heatlog-root")"
elif [[ -d "$HEATLOG_ROOT" ]]; then
    echo "$HEATLOG_ROOT" > "$RBR_DIR/heatlog-root"
    chown "$RBR_USER:$RBR_USER" "$RBR_DIR/heatlog-root"
    chown "$RBR_USER:$RBR_USER" "$HEATLOG_ROOT" 2>/dev/null || true
    echo "  → Created $RBR_DIR/heatlog-root → $HEATLOG_ROOT (existing dir/mount)"
else
    # No data partition yet: symlink to a folder in the controller user's
    # home so the configured path is identical on every machine. Swap the
    # symlink for a real partition mount later without code changes.
    REAL_HEATLOG="/home/$RBR_USER/heating-data"
    mkdir -p "$REAL_HEATLOG"
    chown "$RBR_USER:$RBR_USER" "$REAL_HEATLOG"
    mkdir -p "$(dirname "$HEATLOG_ROOT")"
    ln -s "$REAL_HEATLOG" "$HEATLOG_ROOT"
    echo "$HEATLOG_ROOT" > "$RBR_DIR/heatlog-root"
    chown "$RBR_USER:$RBR_USER" "$RBR_DIR/heatlog-root"
    echo "  → Created symlink $HEATLOG_ROOT → $REAL_HEATLOG"
    echo "    (no data partition found; see doc/HEATING-DATA.md to move it later)"
fi

# =========================================================================--
# STEP 6 — RBR updater (automatic code updates)
# ===========================================================================
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
# STEP 6b — RBR component watchdog (auto-restart down services)
# ===========================================================================
confirm "Step 6b — RBR component watchdog (hourly health check)"

if [[ ! -f "$RBR_DIR/rbr-watchdog.sh" ]]; then
    echo "  ⚠ rbr-watchdog.sh not found in $RBR_DIR — skipping watchdog install"
    echo "    (it ships in rbr-controller.zip; re-run after fetching the pack)"
else
    chown "$RBR_USER:$RBR_USER" "$RBR_DIR/rbr-watchdog.sh"
    chmod 0755 "$RBR_DIR/rbr-watchdog.sh"

    cat > /etc/systemd/system/rbr-watchdog.service << SERVICE
[Unit]
Description=RBR component health watchdog (restart any down core service)

[Service]
Type=oneshot
# Runs as root so it can restart mosquitto/zigbee2mqtt/bridge/controller.
# The script lives in ${RBR_DIR} so the hourly updater refreshes it when a
# new release ships (rbr-watchdog.sh is part of rbr-controller.tar.gz).
ExecStart=${RBR_DIR}/rbr-watchdog.sh
SyslogIdentifier=rbr-watchdog
SERVICE

    cat > /etc/systemd/system/rbr-watchdog.timer << TIMER
[Unit]
Description=Run the RBR component watchdog hourly

[Timer]
OnCalendar=hourly
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
TIMER

    systemctl daemon-reload
    systemctl enable rbr-watchdog.timer
    systemctl start rbr-watchdog.timer
    echo "  → rbr-watchdog.timer enabled (hourly; restarts any down service)"
fi

# =========================================================================--
# STEP 7 — (optional) Local UI web server
# ===========================================================================
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
# STEP 8b — (optional) Run the RBR desktop UI as a systemd service
# ===========================================================================
confirm "Step 8b — RBR desktop UI service (optional)"

INSTALL_UI=""
read -r -p "  Run the desktop UI (PySide6 app) as a service? (y/N): " INSTALL_UI
if [[ "${INSTALL_UI,,}" == "y" ]]; then
    if [[ -z "$ALLSPEAK_BIN" ]]; then
        echo "  ⚠ Could not find the allspeak binary — skipping desktop UI service"
    else
        echo "  Installing PySide6 for the graphics runtime..."
        if ! python3 -c "import PySide6" 2>/dev/null; then
            sudo -u "$RBR_USER" pip install --user pyside6 2>/dev/null \
                || pip install --user pyside6 2>/dev/null \
                || echo "  ⚠ PySide6 install failed — install it manually: pip install pyside6"
        else
            echo "  → PySide6 already present"
        fi
        cat > /etc/systemd/system/rbr-desktop.service << SERVICE
[Unit]
Description=RBR Desktop UI
After=network-online.target mosquitto.service
Wants=network-online.target

[Service]
Type=simple
User=${RBR_USER}
WorkingDirectory=${RBR_DIR}/desktop
Environment=QT_QPA_PLATFORM=xcb
ExecStart=${ALLSPEAK_BIN} rbr-desktop.as
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

        systemctl daemon-reload
        systemctl enable rbr-desktop.service
        systemctl start rbr-desktop.service
        echo "  → rbr-desktop.service running as $RBR_USER"
        echo "    Copy desktop/config.example.json to desktop/config.json to point it at a LAN broker."
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
if [[ -f /etc/systemd/system/rbr-watchdog.timer ]]; then
    echo "    rbr-watchdog.timer $(systemctl is-active rbr-watchdog.timer)"
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
