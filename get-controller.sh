#!/bin/sh
#
# get-controller.sh — fetch and unpack the RBR controller install pack.
#
# Run this on a new controller machine, in the directory where the
# controller files should live:
#
#     mkdir rbr && cd rbr
#     wget https://rbrheating.com/get-controller.sh
#     sh get-controller.sh
#
# It downloads rbr-controller.zip (built by deploy.sh), unpacks it over
# the current directory (existing files are overwritten; machine-specific
# files not in the pack — credentials, .mac_override, map.json, ... — are
# left untouched), records the pack's version in .version, and prints the
# next steps.
#
# POSIX sh only — runs under dash/bash/busybox.
# Override the download base with RBR_BASE, e.g.:
#     RBR_BASE=http://127.0.0.1:8080 sh get-controller.sh   # local test
#
set -eu

BASE="${RBR_BASE:-https://rbrheating.com}"
ZIP="rbr-controller.zip"

echo "Fetching ${BASE}/${ZIP} ..."
if command -v wget >/dev/null 2>&1; then
    wget -q "${BASE}/${ZIP}" -O "$ZIP"
else
    curl -fsSL -o "$ZIP" "${BASE}/${ZIP}"
fi

echo "Unpacking into $(pwd) ..."
if command -v unzip >/dev/null 2>&1; then
    unzip -o "$ZIP"
else
    python3 -m zipfile -e "$ZIP" .
fi

# Record the installed version so rbr-updater.py knows the system is
# current (matches what the updater writes after applying an update).
if [ -f VERSION ]; then
    mv -f VERSION .version
    echo "Installed version $(cat .version)"
fi

# Make sure the scripts are runnable (zip modes can be lost in transit).
chmod +x rbr-setup.sh rbr-updater.py 2>/dev/null || true

echo ""
echo "Done. Next steps:"
echo "  1. Install AllSpeak (the controller runtime):"
echo "       pip install allspeak-ai     # add --break-system-packages if pip refuses"
echo "  2. Install the system services (mosquitto, zigbee2mqtt, bridge, updater):"
echo "       sudo ./rbr-setup.sh"
echo "  3. Run the controller:"
echo "       allspeak controller.as"
echo ""
echo "  Upgrading an EXISTING controller? The files are now updated on disk,"
echo "  but running processes keep their old code until restarted:"
echo "       sudo systemctl restart rbr-zigbee-bridge.service controller.service"
echo "  (or stop the controller and run 'allspeak controller.as' again)"
