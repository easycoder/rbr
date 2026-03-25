"""
RBR Heating REST API — Passenger WSGI application for Dreamhost.

Endpoints:
    GET  /credentials              — Return MQTT broker credentials
    POST /register                 — Register: {mac, email} → emails 6-digit password
    POST /verify                   — Login: {mac, password} → {ok, config, ...}
    POST /pair                     — Controller pairing: {mac} → {ok}
    POST /config                   — Save config: {mac, password, config} → {ok}
    POST /recover                  — Password recovery: {mac, email} → emails new password

Systems are stored in a JSON file (systems.json) alongside this script.
"""

import sys
import os

# ---------------------------------------------------------------------------
# Interpreter shim — use the virtualenv Python if available
# ---------------------------------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(APP_DIR, 'venv', 'bin', 'python')
if os.path.isfile(VENV_PYTHON) and sys.executable != VENV_PYTHON:
    os.execl(VENV_PYTHON, VENV_PYTHON, *sys.argv)

import fcntl
import json
import random
import smtplib
from datetime import datetime
from email.mime.text import MIMEText

SYSTEMS_FILE = os.path.join(APP_DIR, 'systems.json')
SMTP_CONFIG_FILE = os.path.join(APP_DIR, 'smtp.json')


# ---------------------------------------------------------------------------
# File-based systems store
# ---------------------------------------------------------------------------

def _load_systems():
    """Load the systems dict from disk. Returns {} if file doesn't exist."""
    try:
        with open(SYSTEMS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_systems(systems):
    """Atomically write the systems dict to disk with file locking."""
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
    """Load SMTP settings from smtp.json.

    Expected format:
    {
        "host": "mail.example.com",
        "port": 587,
        "user": "noreply@example.com",
        "password": "...",
        "from": "RBR Heating <noreply@example.com>"
    }
    """
    with open(SMTP_CONFIG_FILE) as f:
        return json.load(f)


def _send_email(to_addr, subject, body):
    """Send a plain-text email via SMTP."""
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

def _json_response(start_response, data, status='200 OK'):
    body = json.dumps(data).encode()
    start_response(status, [
        ('Content-Type', 'application/json'),
        ('Content-Length', str(len(body))),
    ])
    return [body]


def _read_body(environ):
    """Read and parse a JSON request body."""
    try:
        length = int(environ.get('CONTENT_LENGTH', 0))
    except ValueError:
        length = 0
    raw = environ['wsgi.input'].read(length) if length else b''
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {}


def _generate_password():
    return str(random.randint(100000, 999999))


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

def handle_credentials(environ, start_response):
    """Return MQTT broker credentials from the site properties file."""
    host = environ.get('HTTP_HOST', '').split(':')[0]
    path = os.path.join(APP_DIR, '..', host + '.txt')
    try:
        with open(path) as f:
            content = f.read().strip()
        # Try JSON first.
        try:
            data = json.loads(content)
            return _json_response(start_response, data)
        except json.JSONDecodeError:
            pass
        # Fall back to key=value pairs.
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
        return _json_response(start_response, creds)
    except FileNotFoundError:
        return _json_response(start_response,
                              {'error': 'Credentials not found'}, '404 Not Found')


def handle_register(environ, start_response):
    """Register a new system. Expects JSON body: {mac, email}.

    If the MAC is already registered, returns an error (use /recover instead).
    Generates a 6-digit password and emails it to the user.
    """
    data = _read_body(environ)
    mac = data.get('mac', '').strip()
    email = data.get('email', '').strip()

    if not mac or not email:
        return _json_response(start_response,
                              {'error': 'mac and email are required'},
                              '400 Bad Request')

    systems = _load_systems()
    if mac in systems:
        return _json_response(start_response,
                              {'error': 'System already registered'},
                              '409 Conflict')

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
        # Roll back — don't leave a system the user can't access
        del systems[mac]
        _save_systems(systems)
        return _json_response(start_response,
                              {'error': f'Failed to send email: {e}'},
                              '500 Internal Server Error')

    return _json_response(start_response, {'ok': True})


def handle_verify(environ, start_response):
    """Verify MAC + password. Expects JSON body: {mac, password}.

    On success returns {ok: true} plus any stored config.
    """
    data = _read_body(environ)
    mac = data.get('mac', '').strip()
    password = data.get('password', '').strip()

    systems = _load_systems()
    entry = systems.get(mac)
    if entry is None or entry.get('password') != password:
        return _json_response(start_response, {'ok': False})

    result = {
        'ok': True,
        'controller_paired': entry.get('controller_paired', False),
        'config': entry.get('config'),
    }
    return _json_response(start_response, result)


def handle_pair(environ, start_response):
    """Controller pairing. Expects JSON body: {mac}.

    Called by the controller on startup. Marks the system as paired
    only if it has already been registered by the user.
    """
    data = _read_body(environ)
    mac = data.get('mac', '').strip()

    if not mac:
        return _json_response(start_response,
                              {'error': 'mac is required'},
                              '400 Bad Request')

    systems = _load_systems()
    if mac not in systems:
        # Not yet registered by a user — silently ignore
        return _json_response(start_response, {'ok': False})

    systems[mac]['controller_paired'] = True
    _save_systems(systems)
    return _json_response(start_response, {'ok': True})


def handle_config(environ, start_response):
    """Save system configuration. Expects JSON body: {mac, password, config}.

    Config is the room/relay/thermometer setup for this system.
    """
    data = _read_body(environ)
    mac = data.get('mac', '').strip()
    password = data.get('password', '').strip()
    config = data.get('config')

    if not mac or not password or config is None:
        return _json_response(start_response,
                              {'error': 'mac, password, and config are required'},
                              '400 Bad Request')

    systems = _load_systems()
    entry = systems.get(mac)
    if entry is None or entry.get('password') != password:
        return _json_response(start_response,
                              {'error': 'Invalid MAC or password'},
                              '403 Forbidden')

    entry['config'] = config
    _save_systems(systems)
    return _json_response(start_response, {'ok': True})


def handle_recover(environ, start_response):
    """Password recovery. Expects JSON body: {mac, email}.

    If MAC and email match, generates a new password and emails it.
    """
    data = _read_body(environ)
    mac = data.get('mac', '').strip()
    email = data.get('email', '').strip()

    if not mac or not email:
        return _json_response(start_response,
                              {'error': 'mac and email are required'},
                              '400 Bad Request')

    systems = _load_systems()
    entry = systems.get(mac)

    # Don't reveal whether the MAC exists — same response either way
    if entry is None or entry.get('email') != email:
        return _json_response(start_response, {'ok': True})

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
        return _json_response(start_response,
                              {'error': f'Failed to send email: {e}'},
                              '500 Internal Server Error')

    return _json_response(start_response, {'ok': True})


# ---------------------------------------------------------------------------
# WSGI application
# ---------------------------------------------------------------------------

def application(environ, start_response):
    method = environ.get('REQUEST_METHOD', 'GET')
    path = environ.get('PATH_INFO', '/').strip('/')

    if method == 'GET' and path == 'credentials':
        return handle_credentials(environ, start_response)

    if method == 'POST':
        if path == 'register':
            return handle_register(environ, start_response)
        if path == 'verify':
            return handle_verify(environ, start_response)
        if path == 'pair':
            return handle_pair(environ, start_response)
        if path == 'config':
            return handle_config(environ, start_response)
        if path == 'recover':
            return handle_recover(environ, start_response)

    return _json_response(start_response,
                          {'error': 'Not found'}, '404 Not Found')
