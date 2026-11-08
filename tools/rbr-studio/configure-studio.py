#!/usr/bin/env python3
"""Set up a Studio copy: where incoming journal bundles arrive and where local data lives.

Run once after unpacking, or later to change the folder:

    python3 configure-studio.py --inbox ~/RBR-journal
    python3 configure-studio.py --system 00:e0:27:5b:31:40=Home
    python3 configure-studio.py --show

`run-studio.sh` calls `--ensure`, which keeps an existing choice and prompts
only when there is no configuration yet. The folder is the one the mail filter
writes the controller's daily `.tar.gz` attachments into; the Studio scans it
and its per-system subfolders at startup. The `systems` map gives a MAC a
useful name; it is used for the Journal scenario name and the per-system
folder, and the mail filter can sort on the MAC in the subject. All other
machine-local data stays under `fixtures/local/`, beside the scripts, unless
`--local-dir` says otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "studio-config.json"
DEFAULT_LOCAL = HERE / "fixtures" / "local"
DEFAULT_INBOX = pathlib.Path.home() / "RBR-journal"


def load_config(path):
    try:
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_config(path, data):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    os.replace(temporary, path)


def parse_system(value):
    """Parse MAC=Name and normalise the MAC to lower-case colon form."""
    if "=" not in value:
        raise SystemExit(f"configure-studio.py: --system expects MAC=Name, got {value!r}")
    mac, name = value.split("=", 1)
    mac = mac.strip().lower().replace("-", ":")
    name = name.strip()
    if not mac or not name:
        raise SystemExit(f"configure-studio.py: --system expects MAC=Name, got {value!r}")
    return mac, name


def parse_mailbox(value):
    """Parse MAC=PATH and normalise the MAC to lower-case colon form."""
    if "=" not in value:
        raise SystemExit(f"configure-studio.py: --mailbox expects MAC=PATH, got {value!r}")
    mac, path = value.split("=", 1)
    mac = mac.strip().lower().replace("-", ":")
    path = path.strip()
    if not mac or not path:
        raise SystemExit(f"configure-studio.py: --mailbox expects MAC=PATH, got {value!r}")
    return mac, str(pathlib.Path(path).expanduser().absolute())


def ensure(args):
    config_path = pathlib.Path(args.config).expanduser()
    local = pathlib.Path(args.local_dir).expanduser()
    data = load_config(config_path)
    systems = data.get("systems")
    if not isinstance(systems, dict):
        systems = {}
    for value in args.system or []:
        mac, name = parse_system(value)
        systems[mac] = name
    if systems:
        data["systems"] = systems
    mailboxes = data.get("mailboxes")
    if not isinstance(mailboxes, dict):
        mailboxes = {}
    for value in args.mailbox or []:
        mac, path = parse_mailbox(value)
        mailboxes[mac] = path
    if mailboxes:
        data["mailboxes"] = mailboxes

    current = str(data.get("journalInbox") or "").strip()
    if args.inbox:
        inbox = pathlib.Path(args.inbox).expanduser()
    elif current:
        inbox = pathlib.Path(current).expanduser()
    elif sys.stdin.isatty() and not args.no_prompt:
        answer = input(f"Folder for incoming journal bundles [{DEFAULT_INBOX}]: ").strip()
        inbox = pathlib.Path(answer).expanduser() if answer else DEFAULT_INBOX
    else:
        inbox = DEFAULT_INBOX
    data["journalInbox"] = str(inbox.absolute())

    save_config(config_path, data)
    for name in ("journal", "drafts", "scenarios"):
        (local / name).mkdir(parents=True, exist_ok=True)
    try:
        inbox.mkdir(parents=True, exist_ok=True)
        for mac in systems:
            (inbox / mac).mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"configure-studio.py: cannot create {inbox}: {exc}", file=sys.stderr)
    print(f"Inbox: {inbox}")
    print(f"Data:  {local}")
    for mac, name in sorted(systems.items()):
        print(f"System: {mac} = {name}")
    for mac, path in sorted(mailboxes.items()):
        print(f"Mailbox: {mac} = {path}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="configure-studio.py",
        description="Configure the journal inbox and local data folder for RBR Studio")
    parser.add_argument("--inbox", help="folder holding the emailed .tar.gz journal bundles "
                                       "(default: ~/RBR-journal)")
    parser.add_argument("--system", action="append", metavar="MAC=NAME",
                        help="name a system by its MAC; repeatable, creates its inbox subfolder")
    parser.add_argument("--mailbox", action="append", metavar="MAC=PATH",
                        help="mbox file for a system; repeatable")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG),
                        help=f"config file (default: {DEFAULT_CONFIG})")
    parser.add_argument("--local-dir", default=str(DEFAULT_LOCAL),
                        help=f"Studio data folder (default: {DEFAULT_LOCAL})")
    parser.add_argument("--ensure", action="store_true",
                        help="create missing folders and keep an existing inbox choice (the launcher's mode)")
    parser.add_argument("--no-prompt", action="store_true",
                        help="do not ask for an inbox; use the existing one or the default")
    parser.add_argument("--show", action="store_true", help="print the current config and exit")
    args = parser.parse_args(argv)
    if args.show:
        print(json.dumps(load_config(args.config), indent=2, ensure_ascii=False))
        return 0
    return ensure(args)


if __name__ == "__main__":
    sys.exit(main())
