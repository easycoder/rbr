#!/usr/bin/env python3
"""Extract RBR journal attachments from an mbox mailbox into the Studio inbox.

The controller emails a bundle with a subject of `RBR journal <MAC> <date>`.
A mail client can keep those messages in an mbox folder; this tool reads that
file, finds valid RBR journal `.tar.gz` attachments, and writes each one into
`<root>/<MAC>/`, ready for RBR Studio's startup scan.

    python3 journal_mbox.py --mbox ~/Mail/RBR-journal --dry-run
    python3 journal_mbox.py --mbox ~/Mail/RBR-journal
    python3 journal_mbox.py --mbox ~/Mail/RBR-journal --remove
    python3 journal_mbox.py --system 00:e0:27:5b:31:40 --list --limit 5

The default root is the same one `journal_inbox.py` uses: the `journalInbox`
in `studio-config.json`, the one-line `fixtures/local/journal-inbox` file, or
`~/RBR-journal`. `--system` selects one controller and, without `--mbox`, reads
its path from the `mailboxes` map in `studio-config.json`; `--list` prints the
newest journals as `JOURNAL <file>` for the Studio's available-journals list.
A mailbox path may be a file, a folder of mboxes, or a Thunderbird profile;
a Thunderbird profile is searched for mbox files whose names contain `RBR` or
`journal` unless `--all-mailboxes` is given, while a plain folder of mboxes is
scanned as it is. `--remove` rewrites the mbox without the messages whose
attachments were all handled; without it the mailbox is left untouched and the
attachments are copied. A filename that already exists with different content
gets a `-2`, `-3` suffix; identical content is skipped.
"""

from __future__ import annotations

import argparse
import io
import json
import mailbox
import pathlib
import re
import sys
import tarfile
from email.header import decode_header, make_header

import journal_bundle
import journal_inbox

MAC_RE = re.compile(r"RBR\s+journal\s+([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})", re.I)
ARCHIVE_SUFFIXES = (".tar.gz", ".tgz")
MBOX_SKIP_SUFFIXES = {
    ".msf", ".sqlite", ".sqlite-wal", ".sqlite-shm", ".db", ".json", ".js",
    ".ini", ".log", ".html", ".htm", ".xml", ".txt", ".bak", ".tmp",
}


def _subject(message) -> str:
    raw = message.get("Subject", "")
    if not raw:
        return ""
    try:
        return str(make_header(decode_header(raw)))
    except (LookupError, UnicodeDecodeError):
        return str(raw)


def _subject_mac(subject: str) -> str:
    match = MAC_RE.search(subject)
    return match.group(1).lower() if match else ""


def _manifest(payload: bytes) -> dict | None:
    """The bundle manifest, or None when the attachment is not an RBR bundle."""
    try:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:*") as tar:
            member = tar.extractfile("manifest.json")
            if member is None:
                return None
            data = json.load(member)
    except (tarfile.TarError, OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("format") != journal_bundle.BUNDLE_FORMAT:
        return None
    if not data.get("day"):
        return None
    return data


def _attachments(message):
    """Yield (filename, bytes) for tar.gz-looking message parts."""
    for part in message.walk():
        if part.is_multipart():
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        name = part.get_filename() or ""
        if name:
            try:
                name = str(make_header(decode_header(name)))
            except (LookupError, UnicodeDecodeError):
                pass
        if name and not name.lower().endswith(ARCHIVE_SUFFIXES):
            continue
        content_type = part.get_content_type().lower()
        if not name and content_type not in ("application/gzip", "application/x-gzip",
                                             "application/x-tar"):
            continue
        yield name, payload


def _safe_name(name: str, mac: str, manifest: dict) -> str:
    if name:
        name = pathlib.Path(name.replace("\\", "/")).name
        name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")
    if not name or not name.lower().endswith(ARCHIVE_SUFFIXES):
        host = mac.replace(":", "-") or "rbr"
        name = f"{host}-{manifest.get('day')}.tar.gz"
    return name


def _target(directory: pathlib.Path, name: str, payload: bytes):
    """A free path, or None when an identical file is already there."""
    candidate = directory / name
    if not candidate.exists():
        return candidate
    if candidate.read_bytes() == payload:
        return None
    if name.lower().endswith(".tar.gz"):
        stem, suffix = name[:-7], ".tar.gz"
    else:
        stem, suffix = name[:-4], ".tgz"
    for index in range(2, 1000):
        candidate = directory / f"{stem}-{index}{suffix}"
        if not candidate.exists():
            return candidate
        if candidate.read_bytes() == payload:
            return None
    raise RuntimeError(f"too many versions of {name}")


def _configured_mailbox(mac: str, config=None) -> str:
    data = journal_inbox.config_data(config)
    mailboxes = data.get("mailboxes")
    if not isinstance(mailboxes, dict):
        return ""
    for key, value in mailboxes.items():
        if str(key).strip().lower() == mac:
            return str(value).strip()
    return ""


def _list_journals(root: pathlib.Path, mac: str, limit: int):
    directory = root / mac
    if not directory.is_dir():
        return []
    found = [path for path in directory.iterdir()
             if path.is_file() and path.name.lower().endswith(ARCHIVE_SUFFIXES)]
    found.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return found[:max(0, limit)]


def _mbox_paths(path, all_mailboxes=False) -> list[pathlib.Path]:
    """A file, or mbox-looking files under a folder (RBR/Journal names by default)."""
    path = pathlib.Path(path).expanduser()
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise SystemExit(f"journal_mbox.py: no such mbox or folder: {path}")
    # A Thunderbird profile is full of unrelated mail; look for the folder the
    # filter made. A plain folder of mboxes is scanned as it is.
    profile = ((path / "prefs.js").is_file() or (path / "ImapMail").is_dir()
               or (path / "Mail").is_dir())
    found = []
    for candidate in sorted(path.rglob("*")):
        if not candidate.is_file() or candidate.name.startswith("."):
            continue
        if candidate.suffix.lower() in MBOX_SKIP_SUFFIXES:
            continue
        if profile and not all_mailboxes and not re.search(r"rbr|journal", candidate.name, re.I):
            continue
        try:
            with candidate.open("rb") as handle:
                head = handle.read(5)
        except OSError:
            continue
        if head == b"From ":
            found.append(candidate)
    if not found:
        hint = "" if all_mailboxes else "; names are filtered to RBR/journal, use --all-mailboxes to scan all"
        raise SystemExit(f"journal_mbox.py: no mbox files under {path}{hint}")
    return found


def extract(mbox_path, root, remove=False, dry_run=False, quiet=False,
            system="") -> dict:
    mbox_path = pathlib.Path(mbox_path).expanduser()
    root = pathlib.Path(root).expanduser()
    if not mbox_path.is_file():
        raise FileNotFoundError(f"journal_mbox.py: no such mbox: {mbox_path}")
    say = (lambda message: None) if quiet else (lambda message: print(message, flush=True))
    stats = {"messages": 0, "saved": 0, "duplicates": 0, "skipped": 0, "errors": 0,
             "removed": 0}

    box = mailbox.mbox(str(mbox_path), create=False)
    locked = False
    if remove and not dry_run:
        try:
            box.lock()
            locked = True
        except OSError as exc:
            box.close()
            raise RuntimeError(f"cannot lock {mbox_path} for --remove: {exc}") from exc
    remove_keys = []
    try:
        for key in list(box.keys()):
            message = box.get_message(key)
            stats["messages"] += 1
            subject = _subject(message)
            mac_from_subject = _subject_mac(subject)
            accepted = 0
            message_error = False
            for name, payload in _attachments(message):
                manifest = _manifest(payload)
                if manifest is None:
                    stats["skipped"] += 1
                    message_error = True
                    continue
                mac = mac_from_subject or str(manifest.get("mac") or "").strip().lower()
                if not mac:
                    stats["skipped"] += 1
                    message_error = True
                    say(f"journal_mbox.py: {mbox_path.name}: attachment has no MAC "
                        f"(subject: {subject or 'none'})")
                    continue
                if system and mac != system:
                    stats["skipped"] += 1
                    message_error = True
                    continue
                directory = root / mac
                filename = _safe_name(name, mac, manifest)
                if dry_run:
                    candidate = directory / filename
                    if candidate.is_file() and candidate.read_bytes() == payload:
                        stats["duplicates"] += 1
                        accepted += 1
                        say(f"journal_mbox.py: already present {mac}/{filename}")
                    else:
                        stats["saved"] += 1
                        accepted += 1
                        say(f"journal_mbox.py: would save {mac}/{filename}")
                    continue
                directory.mkdir(parents=True, exist_ok=True)
                target = _target(directory, filename, payload)
                if target is None:
                    stats["duplicates"] += 1
                    accepted += 1
                    say(f"journal_mbox.py: already present {mac}/{filename}")
                    continue
                target.write_bytes(payload)
                stats["saved"] += 1
                accepted += 1
                say(f"journal_mbox.py: saved {target}")
            if accepted and not message_error:
                remove_keys.append(key)
            elif not accepted:
                continue

        if remove and not dry_run and remove_keys:
            for key in remove_keys:
                box.remove(key)
            box.flush()
            stats["removed"] = len(remove_keys)
    finally:
        if locked:
            box.unlock()
        box.close()

    if not quiet:
        print(f"journal_mbox.py: {stats['messages']} message(s), {stats['saved']} saved, "
              f"{stats['duplicates']} duplicate(s), {stats['skipped']} skipped, "
              f"{stats['removed']} removed")
    return stats


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="journal_mbox.py",
        description="Extract RBR journal attachments from an mbox into the Studio inbox")
    parser.add_argument("--mbox", help="mbox file to read (default: the selected system's "
                                     "`mailboxes` path in studio-config.json)")
    parser.add_argument("--system", help="system MAC to extract and list")
    parser.add_argument("--list", action="store_true",
                        help="after extracting, print the newest journals as `JOURNAL <file>`")
    parser.add_argument("--limit", type=int, default=5,
                        help="how many journals --list prints (default: 5)")
    parser.add_argument("--all-mailboxes", action="store_true",
                        help="when --mbox is a folder, scan every mbox, not only RBR/Journal names")
    parser.add_argument("--root", help="destination root (default: the Studio inbox, "
                                     "then ~/RBR-journal)")
    parser.add_argument("--config", help="studio-config.json used for the default root and mailbox")
    parser.add_argument("--remove", action="store_true",
                        help="remove messages whose attachments were all handled")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would be extracted; change nothing")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    system = str(args.system or "").strip().lower()
    if args.list and not system:
        parser.error("--list needs --system")
    mailbox_path = args.mbox
    if not mailbox_path:
        if not system:
            parser.error("give --mbox, or --system with a configured mailbox")
        mailbox_path = _configured_mailbox(system, args.config)
        if not mailbox_path:
            raise SystemExit(f"journal_mbox.py: no mailbox configured for {system} "
                             "in studio-config.json")
    root = (pathlib.Path(args.root).expanduser() if args.root
            else journal_inbox.resolve_inbox(config=args.config))
    try:
        paths = _mbox_paths(mailbox_path, args.all_mailboxes)
        for path in paths:
            if len(paths) > 1 and not args.quiet:
                print(f"journal_mbox.py: reading {path}", flush=True)
            extract(path, root, remove=args.remove, dry_run=args.dry_run,
                    quiet=args.quiet, system=system)
    except (OSError, RuntimeError, mailbox.Error) as exc:
        print(f"journal_mbox.py: {exc}", file=sys.stderr)
        return 2
    if args.list:
        for path in _list_journals(root, system, args.limit):
            print(f"JOURNAL {path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
