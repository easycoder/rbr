"""Shared SMTP settings and sending for the RBR controller scripts.

`rbr-backup.py` and `journal-export.py` both mail a file to the installation's
registered address. They have to agree about which copy of a setting wins and
what counts as "not configured": a cloud copy still carrying
`credentials.example.json`'s placeholders once overrode a working local SMTP
setup, and every backup reported that mail was not configured. The merge rule
that fixed that lives here so the two senders cannot drift apart.
"""

from __future__ import annotations

import email.message
import json
import mimetypes
import os
import pathlib
import smtplib
import ssl
import subprocess
import urllib.parse
import urllib.request

CREDENTIALS_URL = "https://rbrheating.com/credentials.php"
HTTP_TIMEOUT = 15


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def local_mac(rbr_dir):
    """The controller's topic identity: .mac_override, else the default NIC."""
    override = os.path.join(rbr_dir, ".mac_override")
    if os.path.isfile(override):
        with open(override, encoding="utf-8") as handle:
            mac = handle.read().strip()
        if mac:
            return mac.lower()
    try:
        route = subprocess.run(
            ["sh", "-c", "ip route show default | awk '{print $5}'"],
            capture_output=True, text=True, timeout=5)
        device = route.stdout.strip().splitlines()[0] if route.stdout.strip() else ""
        if device:
            link = subprocess.run(
                ["ip", "link", "show", device], capture_output=True, text=True, timeout=5)
            for token in link.stdout.split():
                if token.count(":") == 5:
                    return token.lower()
    except (OSError, IndexError, subprocess.SubprocessError):
        pass
    return ""


def fetch_cloud(rbr_dir, log=None):
    """What credentials.php says for this controller, or {} when it cannot say."""
    log = log or (lambda message: None)
    mac = local_mac(rbr_dir)
    token = ""
    token_file = os.path.join(rbr_dir, ".mqtt_token")
    if os.path.isfile(token_file):
        try:
            with open(token_file, encoding="utf-8") as handle:
                token = handle.read().strip()
        except OSError as exc:
            log(f"cannot read .mqtt_token ({exc}); using local settings")
    if not mac or not token:
        return {}
    url = "%s?mac=%s&token=%s" % (
        CREDENTIALS_URL, urllib.parse.quote(mac), urllib.parse.quote(token))
    try:
        with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as response:
            data = json.load(response)
        return data if isinstance(data, dict) else {}
    except Exception as exc:  # noqa: BLE001 - offline is an expected state
        log(f"cloud lookup failed ({exc}); using local settings")
        return {}


def load_local_credentials(rbr_dir, log=None):
    log = log or (lambda message: None)
    path = os.path.join(rbr_dir, "credentials")
    try:
        data = read_json(path)
        if isinstance(data, dict):
            return data
        log("local credentials is not a JSON object; ignoring it")
    except FileNotFoundError:
        log("no local credentials file; using the cloud's settings")
    except (OSError, ValueError) as exc:
        log(f"cannot read local credentials ({exc}); using the cloud's settings")
    return {}


def usable_mail_value(key, value):
    """True when a mail setting is present and is not the installer's placeholder."""
    if value is None:
        return False
    text = str(value).strip()
    if not text:
        return False
    low = text.lower()
    if "replace_with" in low:
        return False
    if key == "mail_server":
        if low == "smtp.example.com" or low.endswith(".example.com"):
            return False
    if key == "mail_port":
        try:
            int(text)
        except ValueError:
            return False
    return True


def mail_settings(local, cloud):
    """Mail settings, with a real local value winning over the cloud's copy.

    The controller's own `credentials` file is what the operator edits, and it
    used to be overwritten by re-running the installer. The cloud's host file
    may still carry the placeholder values from `credentials.example.json`; a
    naive merge let those override a working local SMTP configuration and made
    the backup report "mail settings are not configured" after the operator had
    just fixed them. So: use the local value when it is real, and let the cloud
    fill only what the local file has not configured.
    """
    settings = {}
    for key in ("mail_server", "mail_login", "mail_password",
                "mail_from", "mail_port", "mail_to"):
        local_value = local.get(key)
        cloud_value = cloud.get(key)
        if usable_mail_value(key, local_value):
            settings[key] = local_value
        elif usable_mail_value(key, cloud_value):
            settings[key] = cloud_value
    return settings


def mail_problem(settings):
    """Why the settings cannot send, or "" when they can."""
    server = str(settings.get("mail_server", "")).strip()
    login = str(settings.get("mail_login", "")).strip()
    password = str(settings.get("mail_password", ""))
    if not server:
        return "mail_server is empty"
    if not usable_mail_value("mail_server", server):
        return "mail_server is still the placeholder smtp.example.com"
    if not login:
        return "mail_login is empty"
    if not password:
        return "mail_password is empty"
    if not usable_mail_value("mail_password", password):
        return "mail_password is still a placeholder"
    return ""


def resolve_recipient(address, cloud, local):
    for value in (address, cloud.get("email"), local.get("mail_to")):
        if value and "@" in str(value):
            return str(value).strip()
    return ""


def send_files(settings, recipient, subject, body, attachments, log=None, timeout=60):
    """Email one or more files. Returns (sent, error_message).

    Port 587 uses STARTTLS; every other port uses implicit TLS, matching the
    providers the controller is installed against.
    """
    log = log or (lambda message: None)
    recipient = str(recipient or "").strip()
    if not recipient:
        return False, "no registered email address is known"
    problem = mail_problem(settings)
    if problem:
        return False, f"mail settings are not configured in `credentials`: {problem}"
    server = str(settings["mail_server"]).strip()
    port = int(settings.get("mail_port") or 465)
    sender = str(settings.get("mail_from") or settings["mail_login"]).strip()
    login = str(settings["mail_login"]).strip()
    password = str(settings["mail_password"])

    message = email.message.EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content(body)
    names = []
    for path in attachments:
        path = pathlib.Path(path)
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        maintype, _, subtype = content_type.partition("/")
        try:
            payload = path.read_bytes()
        except OSError as exc:
            return False, f"cannot read attachment {path.name}: {exc}"
        message.add_attachment(payload, maintype=maintype, subtype=subtype,
                               filename=path.name)
        names.append(path.name)

    try:
        if port == 587:
            with smtplib.SMTP(server, port, timeout=timeout) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                smtp.login(login, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP_SSL(server, port, timeout=timeout,
                                  context=ssl.create_default_context()) as smtp:
                smtp.login(login, password)
                smtp.send_message(message)
    except Exception as exc:  # noqa: BLE001 - report, do not lose the file
        return False, f"email failed: {exc}"
    log(f"emailed {', '.join(names)} to {recipient}")
    return True, ""
