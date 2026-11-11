#!/usr/bin/env python3
"""rbr-mail-test.py — send one test email using a given SMTP setup.

A stand-alone diagnostic for the mail settings Room By Room uses: fill in the
constants below, run it, and the message that comes out says what to fix. It
needs nothing from this repository and can be copied to the machine that has
the problem.

    python3 rbr-mail-test.py

Transport follows `rbr_mail.send_files`, the sender the controller scripts use:
port 587 uses STARTTLS, every other port uses implicit TLS (SSL on connect).
Keeping that rule here means a success means RBR's own sender will work too.

Do not commit a copy with real credentials in it — fill them in on the machine
that needs testing, or pass the file around privately.
"""

import datetime
import email.message
import smtplib
import socket
import ssl
import sys

# ---- manifest: fill these in -------------------------------------------------
SMTP_SERVER = "smtp.example.com"   # e.g. smtp.gmail.com, smtp.fastmail.com
SMTP_PORT = 465                    # 465 = implicit TLS, 587 = STARTTLS
SMTP_USERNAME = ""                 # usually the full email address
SMTP_PASSWORD = ""                 # an app password if the provider requires one
MAIL_FROM = ""                     # sender; blank uses SMTP_USERNAME
MAIL_TO = ""                       # recipient; comma-separate for several
MAIL_SUBJECT = "RBR test email"
MAIL_BODY = """If you are reading this, the SMTP settings work.

This message was sent by rbr-mail-test.py to check the mail setup used by
Room By Room."""
SMTP_TIMEOUT = 30                  # seconds to wait for the server
# ------------------------------------------------------------------------------


def settings_problem():
    """Why the constants cannot send yet, or "" when they can."""
    server = SMTP_SERVER.strip()
    if not server:
        return "SMTP_SERVER is empty"
    if server.lower() == "smtp.example.com" or server.lower().endswith(".example.com"):
        return "SMTP_SERVER is still the placeholder smtp.example.com"
    if not SMTP_USERNAME.strip():
        return "SMTP_USERNAME is empty"
    if not SMTP_PASSWORD:
        return "SMTP_PASSWORD is empty"
    if not MAIL_TO.strip():
        return "MAIL_TO is empty"
    if "@" not in MAIL_TO:
        return "MAIL_TO does not look like an email address"
    return ""


def build_message(recipients):
    message = email.message.EmailMessage()
    message["Subject"] = MAIL_SUBJECT
    message["From"] = MAIL_FROM.strip() or SMTP_USERNAME.strip()
    message["To"] = ", ".join(recipients)
    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    message.set_content(MAIL_BODY.rstrip() + f"\n\nSent by rbr-mail-test.py at {stamp}.")
    return message


def fail(message):
    print(f"FAILED: {message}", file=sys.stderr)
    return 1


def main():
    problem = settings_problem()
    if problem:
        return fail(f"{problem}. Edit the constants at the top of this file.")

    recipients = [address.strip() for address in MAIL_TO.split(",") if address.strip()]
    sender = MAIL_FROM.strip() or SMTP_USERNAME.strip()
    starttls = SMTP_PORT == 587
    print("RBR mail test")
    print(f"  server   : {SMTP_SERVER}")
    print(f"  port     : {SMTP_PORT} ({'STARTTLS' if starttls else 'implicit TLS'})")
    print(f"  username : {SMTP_USERNAME}")
    print(f"  from     : {sender}")
    print(f"  to       : {', '.join(recipients)}")
    print(f"  subject  : {MAIL_SUBJECT}")
    print("sending…")

    message = build_message(recipients)
    try:
        if starttls:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=SMTP_TIMEOUT) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
                smtp.send_message(message)
        else:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=SMTP_TIMEOUT,
                                  context=ssl.create_default_context()) as smtp:
                smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
                smtp.send_message(message)
    except smtplib.SMTPAuthenticationError:
        return fail(
            "the server rejected the username or password. Many providers "
            "(Gmail, Outlook, Fastmail) need an app password rather than the "
            "normal account password, and some need SMTP enabled first.")
    except smtplib.SMTPSenderRefused as exc:
        return fail(
            f"the server rejected the sender {sender!r}. Some providers only "
            f"allow a From address that matches the login. Server said: {exc}")
    except smtplib.SMTPRecipientsRefused as exc:
        return fail(f"the server rejected every recipient: {exc}")
    except smtplib.SMTPNotSupportedError as exc:
        return fail(
            f"the server does not support this transport: {exc}. "
            "Port 587 uses STARTTLS; 465 uses implicit TLS.")
    except ssl.SSLError as exc:
        return fail(
            f"TLS handshake failed: {exc}. Check the port: 465 is implicit TLS, "
            "587 is STARTTLS. A certificate or clock problem can also do this.")
    except socket.gaierror as exc:
        return fail(f"cannot find the server {SMTP_SERVER!r}: {exc}")
    except (ConnectionRefusedError, TimeoutError) as exc:
        return fail(
            f"could not connect to {SMTP_SERVER}:{SMTP_PORT}: {exc}. Check the "
            "server name, the port, and whether the network allows it.")
    except smtplib.SMTPException as exc:
        return fail(f"the server rejected the message: {exc}")
    except OSError as exc:
        return fail(f"network error: {exc}")

    print(f"sent to {', '.join(recipients)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
