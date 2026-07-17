#!/usr/bin/env python3
"""
rbr-dashboard.py — coloured terminal dashboard for RBR controller

Reads /tmp/rbr-dashboard.json (written by the AllSpeak controller each
cycle) and renders a fixed-position table to the terminal.

Usage:
    python3 rbr-dashboard.py [<state-file>]

Defaults to /tmp/rbr-dashboard.json.
"""

import json
import os
import sys
import shutil
from datetime import datetime

STATE_FILE = "/tmp/rbr-dashboard.json"

RBR_DIR = os.path.dirname(os.path.abspath(__file__))
TEXT_FILE = os.path.join(RBR_DIR, "dashboard.txt")

# ANSI codes
CYAN = "\033[1;36m"
RED = "\033[1;31m"
YELLOW = "\033[1;33m"
GREEN = "\033[1;32m"
RESET = "\033[0m"
GREY = "\033[2m"

# Widths
NAME_W = 18
RELAY_W = 6
TEMP_W = 7
HUM_W = 5
BATT_W = 5
REP_W = 5  # Minutes since last sensor report


def fmt_temp(centi):
    """Centidegrees (e.g. 2320) → " 23.2°" fixed 7 chars."""
    if centi == "" or centi is None:
        return "  --.-°"
    try:
        val = int(centi)
        return f"{val / 100:6.1f}°"
    except (ValueError, TypeError):
        return f"{str(centi):>7}"


def fmt_battery(batt):
    """Format battery to fixed width. Negative = unknown (no battery report)."""
    if batt == "" or batt is None:
        return "   --"
    try:
        val = round(float(batt))
        if val < 0:
            return "   --"
        return f"{val:>4}%"
    except (ValueError, TypeError):
        return "   --"


def fmt_humidity(hum):
    """Format humidity to fixed width. Negative = unknown."""
    if hum == "" or hum is None:
        return "   --"
    try:
        val = round(float(hum))
        if val < 0:
            return "   --"
        return f"{val:>4}%"
    except (ValueError, TypeError):
        return "   --"


def fmt_sensor_age(ms):
    """Milliseconds → minutes string, or '   --' if absent. Fixed 5 chars."""
    if ms == "" or ms is None:
        return "   --"
    try:
        mins = int(int(ms) / 60000)
        if mins > 9999:
            return ">9999"
        return f"{mins:>5}"
    except (ValueError, TypeError):
        return "   --"


def is_sensor_only_msg(msg):
    """True if the message is purely about sensor staleness."""
    return msg.startswith("Sensor:")


def fmt_relay(state):
    state = str(state).lower().strip()
    if state == "on":
        return f"{GREEN}ON    {RESET}"    # 2 + 4 spaces = 6 chars
    return f"{GREY}off   {RESET}"         # 3 + 3 spaces = 6 chars


def pad_to(line, width):
    """Pad with spaces to clear the rest of the line."""
    visible = strip_ansi(line)
    extra = width - len(visible)
    if extra > 0:
        return line + " " * extra
    return line


def strip_ansi(s):
    import re
    return re.sub(r'\033\[[0-9;]*m', '', s)


def render(data):
    cols, rows = shutil.get_terminal_size(fallback=(80, 40))
    line_width = cols

    # Build coloured terminal output + plain text lines side by side
    out = []        # coloured for terminal
    plain = []      # plain for text file

    # Header (now includes Rep column)
    header = f"{'Room':<{NAME_W}}  {'Relay':<{RELAY_W}}  {'Temp':<{TEMP_W}}  {'Hum':<{HUM_W}}  {'Batt':<{BATT_W}}  {'Rep':<{REP_W}}"
    out.append(f"\033[2J\033[H")
    out.append(f"{CYAN}{header}{RESET}")
    plain.append(header)
    ruler = "─" * (NAME_W + RELAY_W + TEMP_W + HUM_W + BATT_W + REP_W + 12)
    out.append(f"{GREY}{ruler}{RESET}")
    plain.append(ruler)

    rooms = data.get("rooms", [])
    for r in rooms:
        name = r.get("name", "?")
        relay = r.get("relay", "off")
        temp = fmt_temp(r.get("temperature", ""))

        # Row 1: data (with Rep column)
        raw_relay = "ON" if str(r.get("relay", "off")).lower().strip() == "on" else "off"
        hum_str = fmt_humidity(r.get("humidity", ""))
        batt_str = fmt_battery(r.get("battery", ""))
        rep = fmt_sensor_age(r.get("sensorAge", ""))
        line = (f"{CYAN}{name:<{NAME_W}}{RESET}  "
                f"{fmt_relay(relay)}  "
                f"{temp}  "
                f"{hum_str}  "
                f"{batt_str}  "
                f"{rep}")
        plain_line = f"{name:<{NAME_W}}  {raw_relay:<6}  {temp}  {hum_str}  {batt_str}  {rep}"
        out.append(pad_to(line, line_width))
        plain.append(plain_line)

        # Row 2: warning / blank (skip pure sensor-staleness messages)
        status = r.get("status", "")
        msg = r.get("statusMessage", "")
        warn = ""
        plain_warn = ""
        if msg and not is_sensor_only_msg(msg):
            if status == "warn":
                warn = f"{YELLOW}{msg}{RESET}"
                plain_warn = msg
            elif status == "fail":
                warn = f"{RED}✗ {msg}{RESET}"
                plain_warn = f"✗ {msg}"
        out.append(pad_to(warn, line_width))
        plain.append(plain_warn)

    # Request relay
    req = data.get("request", {})
    req_name = req.get("name", "")
    if req_name:
        ruler2 = "─" * line_width
        out.append(f"{GREY}{ruler2}{RESET}")
        plain.append(ruler2)
        req_relay = req.get("relay", "off")
        req_msg = req.get("statusMessage", "")
        raw_req_relay = "ON" if str(req_relay).lower().strip() == "on" else "off"
        line = (f"{CYAN}⏎ {req_name:<{NAME_W - 2}}{RESET}  "
                f"{fmt_relay(req_relay)}")
        plain_line = f"⏎ {req_name:<{NAME_W - 2}}  {raw_req_relay}"
        if req_msg:
            line += f"  {YELLOW}{req_msg}{RESET}"
            plain_line += f"  {req_msg}"
        out.append(pad_to(line, line_width))
        plain.append(plain_line)

    # Timestamp
    ts = str(data.get("timestamp", ""))
    try:
        ts_int = int(ts)
        readable = datetime.fromtimestamp(ts_int / 1000).strftime("%H:%M:%S")
    except (ValueError, OSError):
        readable = ts
    out.append(f"{GREY}─── {readable}{RESET}")
    plain.append(f"─── {readable}")

    # Terminal output
    sys.stdout.write("\n".join(out) + "\n")
    sys.stdout.flush()

    # Plain-text file (for asedit / service mode)
    try:
        with open(TEXT_FILE, "w") as f:
            f.write("\n".join(plain) + "\n")
    except OSError:
        pass


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else STATE_FILE
    if not os.path.exists(path):
        print(f"\033[2J\033[H{RED}Dashboard: no state file yet{RESET}")
        sys.exit(0)
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"\033[2J\033[H{RED}Dashboard: error reading state: {e}{RESET}")
        sys.exit(0)
    render(data)


if __name__ == "__main__":
    main()
