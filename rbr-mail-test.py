#!/usr/bin/env python3
"""rbr-mail-test.py — send one test email using the controller's mail settings.

The settings are not typed into this file: they are read from the controller's
`credentials` and resolved by `rbr_mail`, the module the real senders use. A
usable value in the local file wins, and `credentials.php` fills only what is
missing or still a placeholder — the same rule `rbr-backup.py` and
`journal-export.py` follow — so a success here means those senders work. The
`--show` option prints every resolved setting and which file it came from.

The recipient follows the timers too: `--to`, then the address in
`backup-config.json`, then the one in `journal-export-config.json`, then the
address registered in the app (`credentials.php`), then `mail_to` in
`credentials`. When there is no `.mqtt_token` the cloud is never asked, and the
report says so instead of leaving an unexplained empty recipient.

The controller's own verification and recovery mail is stricter: it reads only
the local `credentials`. When it is `credentials.php` that supplies the mail
server, this script says so, because those mails will still fail.

    python3 rbr-mail-test.py                       # this script's directory
    python3 rbr-mail-test.py --dir ~/rbr           # a controller directory elsewhere
    python3 rbr-mail-test.py --show                # print the settings, send nothing
    python3 rbr-mail-test.py --to me@example.com   # override the recipient

`rbr_mail.py` has to sit beside this script; both ship with the controller. The
password is never printed, and nothing on disk is written.
"""

import argparse
import datetime
import email.message
import json
import os
import pathlib
import smtplib
import socket
import ssl
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent

MAIL_SUBJECT = "RBR test email"
MAIL_BODY = """If you are reading this, the SMTP settings work.

This message was sent by rbr-mail-test.py to check the mail setup used by
Room By Room."""
SMTP_TIMEOUT = 30                  # seconds to wait for the server


def fail(message):
    print(f"FAILED: {message}", file=sys.stderr)
    return 1


def load_rbr_mail():
    """The real senders' module, loaded from beside this script."""
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        import rbr_mail
    except ImportError:
        return None
    return rbr_mail


def setting_source(rbr_mail, key, local, cloud):
    """Which file supplied this setting: the local credentials, or the cloud."""
    if rbr_mail.usable_mail_value(key, local.get(key)):
        return "credentials"
    if rbr_mail.usable_mail_value(key, cloud.get(key)):
        return "credentials.php"
    return "default" if key == "mail_port" else "not set"


def configured_address(path):
    """The address a timer's own config file holds, or "".

    `rbr-backup.py` and `journal-export.py` each pass their config's `address`
    to resolve_recipient() ahead of the cloud and `mail_to`, so the test has to
    look there too — otherwise a system set up entirely from the app's Backups
    sheet reports "no recipient" while its monthly mail has one.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return ""
    if not isinstance(data, dict):
        return ""
    address = str(data.get("address") or "").strip()
    return address if "@" in address else ""


def recipient_and_source(rbr_mail, rbr_dir, override, local, cloud):
    """Who the message goes to, where that address came from, and any note.

    The order follows the senders: `--to`, then the monthly backup's config,
    then the journal export's, then the address registered in the app (the
    cloud), then `mail_to` in the local credentials.
    """
    if override:
        addresses = [address.strip() for address in override.split(",") if address.strip()]
        return addresses, "--to", ""

    backup = configured_address(os.path.join(rbr_dir, "backup-config.json"))
    journal = configured_address(os.path.join(rbr_dir, "journal-export-config.json"))
    note = ""
    if backup:
        if journal and journal != backup:
            note = (f"journal-export-config.json mails {journal}; "
                    "the monthly backup's address is shown")
        return [backup], "backup-config.json", note
    if journal:
        return [journal], "journal-export-config.json", ""

    address = rbr_mail.resolve_recipient("", cloud, local)
    if not address:
        return [], "", ""
    for value, source in ((cloud.get("email"), "credentials.php"),
                          (local.get("mail_to"), "credentials")):
        if value and "@" in str(value):
            return [address], source, ""
    return [address], "", ""


def show_settings(rbr_mail, path, settings, local, cloud, recipients, recipient_source,
                  problem, local_problem, notes=()):
    print(f"RBR mail test — settings from {path}")
    sender = str(settings.get("mail_from") or settings.get("mail_login", "")).strip()
    from_source = setting_source(rbr_mail, "mail_from", local, cloud)
    if from_source == "not set" and sender:
        from_source = "the login"
    rows = [
        ("server", str(settings.get("mail_server", "")) or "—",
         setting_source(rbr_mail, "mail_server", local, cloud)),
        ("port", str(settings.get("mail_port") or 465),
         setting_source(rbr_mail, "mail_port", local, cloud)),
        ("username", str(settings.get("mail_login", "")) or "—",
         setting_source(rbr_mail, "mail_login", local, cloud)),
        ("password", "set" if settings.get("mail_password") else "missing",
         setting_source(rbr_mail, "mail_password", local, cloud)),
        ("from", sender or "—", from_source),
        ("to", ", ".join(recipients) if recipients else "—", recipient_source or "not set"),
    ]
    width = max(len(label) for label, _, _ in rows)
    for label, value, origin in rows:
        print(f"  {label:<{width}} : {value:<30} ({origin})")
    port = int(settings.get("mail_port") or 465)
    print(f"  {'transport':<{width}} : {'STARTTLS' if port == 587 else 'implicit TLS'}")
    for note in notes:
        print(f"  note: {note}")
    if local_problem:
        print(f"  note: the controller's own verification mail will not send: {local_problem}")
        print("        (it reads only the local credentials file, not credentials.php)")
    if problem:
        print(f"  {'problem':<{width}} : {problem}")


def build_message(sender, recipients):
    message = email.message.EmailMessage()
    message["Subject"] = MAIL_SUBJECT
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    message.set_content(MAIL_BODY.rstrip() + f"\n\nSent by rbr-mail-test.py at {stamp}.")
    return message


def send(settings, sender, recipients):
    """Send one message. Returns 0 on success, 1 with the reason on failure.

    Port 587 uses STARTTLS; every other port uses implicit TLS, matching
    rbr_mail.send_files, so a success means RBR's own sender will connect too.
    """
    server = str(settings["mail_server"]).strip()
    port = int(settings.get("mail_port") or 465)
    login = str(settings["mail_login"]).strip()
    password = str(settings["mail_password"])
    message = build_message(sender, recipients)
    try:
        if port == 587:
            with smtplib.SMTP(server, port, timeout=SMTP_TIMEOUT) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                smtp.login(login, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP_SSL(server, port, timeout=SMTP_TIMEOUT,
                                  context=ssl.create_default_context()) as smtp:
                smtp.login(login, password)
                smtp.send_message(message)
    except smtplib.SMTPAuthenticationError:
        return fail(
            "the server rejected the username or password. Many providers "
            "(Gmail, Outlook, Fastmail) need an app password rather than the "
            "normal account password, and some need SMTP enabled first.")
    except smtplib.SMTPSenderRefused as exc:
        return fail(
            f"the server rejected the sender {sender!r}. Some providers only "
            f"allow a From address that matches the login — set mail_from in "
            f"credentials to {login!r}, or clear it so the login is used. "
            f"Server said: {exc}")
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
        return fail(f"cannot find the server {server!r}: {exc}")
    except (ConnectionRefusedError, TimeoutError) as exc:
        return fail(
            f"could not connect to {server}:{port}: {exc}. Check the "
            "server name, the port, and whether the network allows it.")
    except smtplib.SMTPException as exc:
        return fail(f"the server rejected the message: {exc}")
    except OSError as exc:
        return fail(f"network error: {exc}")

    print(f"sent to {', '.join(recipients)}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Send one test email using the controller's credentials.")
    parser.add_argument(
        "--dir", default=str(SCRIPT_DIR),
        help="controller directory holding credentials and .mqtt_token "
             "(default: this script's directory)")
    parser.add_argument("--to", help="recipient address; overrides the registered one")
    parser.add_argument(
        "--no-cloud", action="store_true",
        help="ignore credentials.php and use the local credentials alone")
    parser.add_argument(
        "--show", action="store_true",
        help="print the resolved settings and exit without sending")
    args = parser.parse_args()

    rbr_mail = load_rbr_mail()
    if rbr_mail is None:
        return fail(
            "rbr_mail.py is not beside this script. It is the module the real "
            "senders use, and it ships with the controller — copy it next to "
            "rbr-mail-test.py, or put this script in the controller directory.")

    rbr_dir = os.path.abspath(os.path.expanduser(args.dir))
    path = os.path.join(rbr_dir, "credentials")
    local = rbr_mail.load_local_credentials(rbr_dir, log=print)
    cloud = {} if args.no_cloud else rbr_mail.fetch_cloud(rbr_dir, log=print)
    settings = rbr_mail.mail_settings(local, cloud)
    problem = rbr_mail.mail_problem(settings)
    local_problem = rbr_mail.mail_problem(local)
    recipients, recipient_source, recipient_note = recipient_and_source(
        rbr_mail, rbr_dir, args.to, local, cloud)

    notes = []
    if args.no_cloud:
        notes.append("credentials.php not asked (--no-cloud); a registered address is ignored")
    elif not os.path.isfile(os.path.join(rbr_dir, ".mqtt_token")):
        notes.append(f"no .mqtt_token in {rbr_dir} — credentials.php was not asked, "
                     "so an address registered in the app cannot be used")
    if recipient_note:
        notes.append(recipient_note)

    if not settings and not local and not cloud:
        return fail(
            f"no settings found: {path} does not exist and there is no "
            ".mqtt_token to ask credentials.php with. "
            "Pass --dir <controller directory>.")

    sender = str(settings.get("mail_from") or settings.get("mail_login", "")).strip()
    show_settings(rbr_mail, path, settings, local, cloud, recipients, recipient_source,
                  problem, local_problem, notes)
    sys.stdout.flush()

    if args.show:
        if problem:
            return 1
        print("not sending (--show)")
        return 0
    if problem:
        return fail(f"cannot send: {problem}")
    if not recipients:
        return fail(
            "no recipient: pass --to, or set mail_to in credentials, or "
            "register an address in the app")

    print("sending…", flush=True)
    return send(settings, sender, recipients)


if __name__ == "__main__":
    raise SystemExit(main())
