#!/usr/bin/env python3
"""
RBR Heating REST API — CGI script for Dreamhost.

Endpoints:
    GET  /api.cgi/credentials      — Return MQTT broker credentials
    POST /api.cgi/register         — Register: {mac, email} → emails 6-digit password
    POST /api.cgi/verify           — Login: {mac, password} → {ok, config, ...}
    POST /api.cgi/pair             — Controller pairing: {mac} → {ok}
    POST /api.cgi/config           — Save config: {mac, password, config} → {ok}
    POST /api.cgi/recover          — Password recovery: {mac, email} → emails new password

Systems are stored in a JSON file (systems.json) in the home directory.
"""

import cgi
import cgitb
import fcntl
import json
import os
import random
import smtplib
import sys
from datetime import datetime
from email.mime.text import MIMEText

cgitb.enable()

HOME_DIR = os.path.expanduser('~')
SYSTEMS_FILE = os.path.join(HOME_DIR, 'systems.json')
SMTP_CONFIG_FILE = os.path.join(HOME_DIR, 'smtp.json')


# ---------------------------------------------------------------------------
# File-based systems store
# ---------------------------------------------------------------------------

def _load_systems():
    try:
        with open(SYSTEMS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_systems(systems):
    tmp = SYSTEMS_FILE + '.tmp'
    with open(tmp, 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(systems, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
        fcntl.flock(f, fcntl.LOCK_UN)
    os.replace(tmp, SYSTEMS_FILE)


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

def _load_smtp_config():
    with open(SMTP_CONFIG_FILE) as f:
        return json.load(f)


def _send_email(to_addr, subject, body):
    cfg = _load_smtp_config()
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = cfg['from']
    msg['To'] = to_addr

    with smtplib.SMTP(cfg['host'], cfg['port']) as server:
        server.starttls()
        server.login(cfg['user'], cfg['password'])
        server.send_message(msg)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _respond(data, status='200 OK'):
    body = json.dumps(data)
    # Always return 200 so EasyCoder can read the response body.
    # Error info is in the JSON itself (e.g. {"error": "..."}).
    print('Status: 200 OK')
    print('Content-Type: application/json')
    print(f'Content-Length: {len(body.encode())}')
    print()
    print(body)
    sys.exit(0)


def _read_body():
    try:
        length = int(os.environ.get('CONTENT_LENGTH', 0))
    except ValueError:
        length = 0
    raw = sys.stdin.read(length) if length else ''
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {}


def _generate_password():
    return str(random.randint(100000, 999999))


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

def handle_credentials():
    host = os.environ.get('HTTP_HOST', '').split(':')[0]
    path = os.path.join(HOME_DIR, host + '.txt')
    try:
        with open(path) as f:
            content = f.read().strip()
        try:
            data = json.loads(content)
            _respond(data)
        except json.JSONDecodeError:
            pass
        props = {}
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                props[k] = v
        creds = {}
        for key in ('broker', 'username', 'password', 'serverID'):
            if key in props:
                creds[key] = props[key]
        _respond(creds)
    except FileNotFoundError:
        _respond({'error': 'Credentials not found'}, '404 Not Found')


def handle_register():
    data = _read_body()
    mac = data.get('mac', '').strip()
    email = data.get('email', '').strip()

    if not mac or not email:
        _respond({'error': 'mac and email are required'}, '400 Bad Request')

    systems = _load_systems()
    if mac in systems:
        _respond({'error': 'System already registered'}, '409 Conflict')

    password = _generate_password()
    systems[mac] = {
        'password': password,
        'email': email,
        'registered': datetime.utcnow().isoformat(),
        'controller_paired': False,
        'config': None,
    }
    _save_systems(systems)

    try:
        _send_email(
            email,
            'RBR Heating — Your registration code',
            f'Your RBR Heating registration code is: {password}\n\n'
            f'System MAC: {mac}\n\n'
            'Enter this code in the RBR app to complete registration.\n'
            'Keep it safe — you will need it to log in on new devices.\n',
        )
    except Exception as e:
        del systems[mac]
        _save_systems(systems)
        _respond({'error': f'Failed to send email: {e}'}, '500 Internal Server Error')

    _respond({'ok': True})


def handle_verify():
    data = _read_body()
    mac = data.get('mac', '').strip()
    password = data.get('password', '').strip()

    systems = _load_systems()
    entry = systems.get(mac)
    if entry is None or entry.get('password') != password:
        _respond({'ok': False})

    result = {
        'ok': True,
        'controller_paired': entry.get('controller_paired', False),
        'config': entry.get('config'),
    }
    _respond(result)


def handle_pair_get(mac):
    """Controller pairing via GET /pair/<mac>."""
    mac = mac.strip()
    if not mac:
        _respond({'ok': False})

    systems = _load_systems()
    if mac not in systems:
        _respond({'ok': False})

    systems[mac]['controller_paired'] = True
    _save_systems(systems)
    _respond({'ok': True})


def handle_pair():
    data = _read_body()
    mac = data.get('mac', '').strip()

    if not mac:
        _respond({'error': 'mac is required'}, '400 Bad Request')

    systems = _load_systems()
    if mac not in systems:
        _respond({'ok': False})

    systems[mac]['controller_paired'] = True
    _save_systems(systems)
    _respond({'ok': True})


def handle_config():
    data = _read_body()
    mac = data.get('mac', '').strip()
    password = data.get('password', '').strip()
    config = data.get('config')

    if not mac or not password or config is None:
        _respond({'error': 'mac, password, and config are required'}, '400 Bad Request')

    systems = _load_systems()
    entry = systems.get(mac)
    if entry is None or entry.get('password') != password:
        _respond({'error': 'Invalid MAC or password'}, '403 Forbidden')

    entry['config'] = config
    _save_systems(systems)
    _respond({'ok': True})


def handle_recover():
    data = _read_body()
    mac = data.get('mac', '').strip()
    email = data.get('email', '').strip()

    if not mac or not email:
        _respond({'error': 'mac and email are required'}, '400 Bad Request')

    systems = _load_systems()
    entry = systems.get(mac)

    if entry is None or entry.get('email') != email:
        _respond({'ok': True})

    password = _generate_password()
    entry['password'] = password
    _save_systems(systems)

    try:
        _send_email(
            email,
            'RBR Heating — Your new password',
            f'Your new RBR Heating password is: {password}\n\n'
            f'System MAC: {mac}\n\n'
            'This replaces your previous password.\n',
        )
    except Exception as e:
        _respond({'error': f'Failed to send email: {e}'}, '500 Internal Server Error')

    _respond({'ok': True})


# ---------------------------------------------------------------------------
# Main dispatch
# ---------------------------------------------------------------------------

path_info = os.environ.get('PATH_INFO', '/').strip('/')
method = os.environ.get('REQUEST_METHOD', 'GET')

parts = path_info.split('/')

if method == 'GET' and path_info == 'credentials':
    handle_credentials()
elif method == 'GET' and len(parts) == 2 and parts[0] == 'pair':
    handle_pair_get(parts[1])
elif method == 'POST':
    if path_info == 'register':
        handle_register()
    elif path_info == 'verify':
        handle_verify()
    elif path_info == 'pair':
        handle_pair()
    elif path_info == 'config':
        handle_config()
    elif path_info == 'recover':
        handle_recover()

_respond({'error': 'Not found'}, '404 Not Found')
