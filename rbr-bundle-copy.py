#!/usr/bin/env python3
"""rbr-bundle-copy.py — keep a yearly archive of the journal bundles arriving by email.

The controller emails one compact journal bundle per day
(`journal-export.py`), and a mail filter can leave those messages in a folder,
an mbox or a Maildir. This service reads the configured mail folder once a day,
extracts each valid RBR journal attachment, and copies it to
`<save_path>/<installation>/<YYYY>/<original filename>`. A file that is already
present is left alone, so running the service again is harmless and a mailbox
can be rescanned at any time.

The installation folder is named after the mail folder the bundle arrived in:
an mbox file or Maildir's own name (`QED6`, for example). For a bundle already
saved as a file, the manifest's `system` (then `mac`) is used instead. Point
`email_path` at one installation's mail folder, or at a parent folder holding
one mail folder or mbox per installation — for example Thunderbird's
`Bundles.sbd`, containing `QED6`, `OTHER` and so on. Keep those names
consistent; each installation's mail filter should deliver into a folder of
that name.

The service is self-scheduling: the time to run at lives in the config, so
there is no systemd timer. It also runs one catch-up pass at startup when the
service starts after the configured time, which covers a reboot or a restart
during the day. `--once` performs one pass immediately and exits.

Configuration
-------------
`/etc/rbr-bundle-copy.conf` (override with `--config`):

    [bundle-copy]
    email_path = /home/graham/Mail/RBR-journal
    save_path = /home/graham/RBR-journal-archive
    run_at = 03:30

`email_path` may be a single mbox, a Maildir, a folder of mboxes searched
recursively (including a Thunderbird profile), a folder of already-saved
`.tar.gz` attachments, or one such bundle. A folder source may be the parent of
several installation mail folders; each mbox's name becomes its installation
folder under `save_path`. In a Thunderbird profile only mbox files whose names
match RBR or journal are read unless `scan_all_mailboxes = true` is set.
`run_at` is 24-hour local time. `save_path` is created as needed.

Usage
-----
    python3 rbr-bundle-copy.py
    python3 rbr-bundle-copy.py --once
    python3 rbr-bundle-copy.py --once --dry-run
    python3 rbr-bundle-copy.py --config /etc/rbr-bundle-copy.conf --once

Every run logs a one-line summary. `--quiet` suppresses per-file lines but
keeps the summary and warnings.
"""

import argparse
import configparser
import datetime
import io
import json
import mailbox
import os
import pathlib
import re
import sys
import tarfile
import tempfile
import time
from email.header import decode_header, make_header

CONFIG_PATH = "/etc/rbr-bundle-copy.conf"
SECTION = "bundle-copy"
BUNDLE_FORMAT = "rbr-journal-bundle"
ARCHIVE_SUFFIXES = (".tar.gz", ".tgz")
MAC_RE = re.compile(r"RBR\s+journal\s+([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})", re.I)
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MBOX_SKIP_SUFFIXES = {
    ".msf", ".sqlite", ".sqlite-wal", ".sqlite-shm", ".db", ".json", ".js",
    ".ini", ".log", ".html", ".htm", ".xml", ".txt", ".bak", ".tmp",
}


def log(message, file=None):
    """Write one timestamped line, as systemd's journal will keep it."""
    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    print("%s rbr-bundle-copy: %s" % (stamp, message), file=file or sys.stdout,
          flush=True)


def warn(message):
    log(message, file=sys.stderr)


def load_config(path):
    """Read the service config and return the three settings it must carry."""
    parser = configparser.ConfigParser(interpolation=None)
    try:
        read = parser.read(str(path))
    except OSError as exc:
        raise SystemExit("rbr-bundle-copy.py: cannot read %s: %s" % (path, exc))
    except configparser.Error as exc:
        raise SystemExit("rbr-bundle-copy.py: bad config %s: %s" % (path, exc))
    if not read:
        raise SystemExit("rbr-bundle-copy.py: no config file at %s" % path)
    if not parser.has_section(SECTION):
        raise SystemExit("rbr-bundle-copy.py: %s has no [%s] section"
                         % (path, SECTION))
    try:
        email_path = parser.get(SECTION, "email_path").strip()
        save_path = parser.get(SECTION, "save_path").strip()
        run_at = parse_run_at(parser.get(SECTION, "run_at"))
        scan_all = parser.getboolean(SECTION, "scan_all_mailboxes", fallback=False)
    except configparser.Error as exc:
        raise SystemExit("rbr-bundle-copy.py: %s: %s" % (path, exc))
    if not email_path:
        raise SystemExit("rbr-bundle-copy.py: %s: email_path is empty" % path)
    if not save_path:
        raise SystemExit("rbr-bundle-copy.py: %s: save_path is empty" % path)
    return {
        "email_path": pathlib.Path(email_path).expanduser(),
        "save_path": pathlib.Path(save_path).expanduser(),
        "run_at": run_at,
        "scan_all_mailboxes": scan_all,
    }


def parse_run_at(value):
    """Parse HH:MM (or H:MM) into a time; raise a readable config error."""
    text = str(value).strip()
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", text)
    if not match:
        raise ValueError("run_at must be HH:MM, got %r" % text)
    hour, minute = int(match.group(1)), int(match.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("run_at is out of range: %s" % text)
    return datetime.time(hour, minute)


def _subject(message):
    raw = message.get("Subject", "")
    if not raw:
        return ""
    try:
        return str(make_header(decode_header(raw)))
    except (LookupError, UnicodeDecodeError):
        return str(raw)


def _subject_mac(subject):
    match = MAC_RE.search(subject)
    return match.group(1).lower() if match else ""


def _manifest(payload):
    """The bundle manifest, or None when the attachment is not an RBR bundle."""
    try:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:*") as tar:
            member = tar.extractfile("manifest.json")
            if member is None:
                return None
            data = json.load(member)
    except (tarfile.TarError, OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("format") != BUNDLE_FORMAT:
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


def _safe_name(name, mac, manifest):
    """A filename that cannot escape the year folder and still names a bundle."""
    if name:
        name = pathlib.Path(name.replace("\\", "/")).name
        name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")
    if not name or not name.lower().endswith(ARCHIVE_SUFFIXES):
        host = mac.replace(":", "-") or "rbr"
        name = "%s-%s.tar.gz" % (host, manifest.get("day"))
    return name


def _safe_folder(name):
    """A safe single path component for an installation folder."""
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", str(name or "").strip()).strip("-.")
    return "" if text in ("", ".", "..") else text


def _manifest_installation(manifest):
    """The installation named by a bundle manifest, for a source with no folder name."""
    for key in ("system", "mac"):
        value = str(manifest.get(key) or "").strip()
        if value:
            return _safe_folder(value)
    return "rbr"


def _year(manifest):
    """The journal day's year, so a late-arriving bundle lands in its own year."""
    day = str(manifest.get("day") or "")
    if DAY_RE.match(day):
        return day[:4]
    return str(datetime.date.today().year)


def _store(payload, directory, name, dry_run, say, label_root=None):
    """Copy one bundle unless the target already exists; return an outcome."""
    target = directory / name
    label = target.relative_to(label_root or directory.parent)
    if target.exists():
        say("already present %s" % label)
        return "existing"
    if dry_run:
        say("would copy %s" % label)
        return "would-copy"
    directory.mkdir(parents=True, exist_ok=True)
    temporary = ""
    try:
        handle = tempfile.NamedTemporaryFile(
            mode="wb", prefix=".rbr-bundle-", suffix=".part",
            dir=str(directory), delete=False)
        temporary = handle.name
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if target.exists():
            say("already present %s" % label)
            return "existing"
        os.replace(temporary, target)
        temporary = ""
        say("copied %s" % label)
        return "copied"
    finally:
        if temporary:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def _process_attachment(name, payload, mac_from_subject, source, save_path,
                        dry_run, stats, say, installation=""):
    stats["attachments"] += 1
    manifest = _manifest(payload)
    if manifest is None:
        stats["invalid"] += 1
        say("not a journal bundle: %s (%s)" % (name or "unnamed attachment", source))
        return
    mac = mac_from_subject or str(manifest.get("mac") or "").strip().lower()
    filename = _safe_name(name, mac, manifest)
    folder = _safe_folder(installation) or _manifest_installation(manifest)
    directory = save_path / folder / _year(manifest)
    outcome = _store(payload, directory, filename, dry_run, say, save_path)
    stats[outcome] += 1


def _process_message(message, source, save_path, dry_run, stats, say, installation=""):
    stats["messages"] += 1
    subject = _subject(message)
    mac = _subject_mac(subject)
    for name, payload in _attachments(message):
        _process_attachment(name, payload, mac, source, save_path, dry_run,
                            stats, say, installation=installation)


def _looks_like_mbox(path):
    try:
        with path.open("rb") as handle:
            return handle.read(5) == b"From "
    except OSError:
        return False


def _is_maildir(path):
    return (path.is_dir() and (path / "cur").is_dir()
            and (path / "new").is_dir() and (path / "tmp").is_dir())


def _inside_maildir(path):
    """True for a message file inside a Maildir, which must not be read as mbox."""
    parent = path.parent
    return (parent.name in ("cur", "new", "tmp")
            and (parent.parent / "cur").is_dir()
            and (parent.parent / "new").is_dir()
            and (parent.parent / "tmp").is_dir())


def _read_mbox(path, save_path, dry_run, stats, say, installation=None):
    installation = path.name if installation is None else installation
    box = mailbox.mbox(str(path), create=False)
    try:
        for key in box.iterkeys():
            try:
                _process_message(box.get_message(key), path.name, save_path,
                                 dry_run, stats, say, installation=installation)
            except (mailbox.Error, OSError, ValueError) as exc:
                stats["errors"] += 1
                warn("cannot read message in %s: %s" % (path, exc))
    finally:
        box.close()


def _read_maildir(path, save_path, dry_run, stats, say, installation=None):
    installation = path.name if installation is None else installation
    box = mailbox.Maildir(str(path), create=False)
    try:
        for key in box.iterkeys():
            try:
                _process_message(box.get_message(key), str(path), save_path,
                                 dry_run, stats, say, installation=installation)
            except (mailbox.Error, OSError, ValueError) as exc:
                stats["errors"] += 1
                warn("cannot read message in %s: %s" % (path, exc))
    finally:
        box.close()


def _read_bare_archive(path, save_path, dry_run, stats, say):
    try:
        payload = path.read_bytes()
    except OSError as exc:
        stats["errors"] += 1
        warn("cannot read %s: %s" % (path, exc))
        return
    _process_attachment(path.name, payload, "", str(path), save_path,
                        dry_run, stats, say)


def _scan_folder(path, save_path, dry_run, stats, say, scan_all):
    """Read mbox files and bare bundle files under a configured folder."""
    profile = ((path / "prefs.js").is_file() or (path / "ImapMail").is_dir()
               or (path / "Mail").is_dir())
    found = []
    for candidate in sorted(path.rglob("*")):
        if not candidate.is_file() or candidate.name.startswith("."):
            continue
        if _inside_maildir(candidate):
            continue
        if candidate.name.lower().endswith(ARCHIVE_SUFFIXES):
            found.append(("archive", candidate))
            continue
        if candidate.suffix.lower() in MBOX_SKIP_SUFFIXES:
            continue
        if not _looks_like_mbox(candidate):
            continue
        if profile and not scan_all and not re.search(r"rbr|journal", candidate.name, re.I):
            continue
        found.append(("mbox", candidate))
    if not found:
        warn("no mbox or journal bundle found under %s" % path)
        return
    for kind, candidate in found:
        if kind == "archive":
            _read_bare_archive(candidate, save_path, dry_run, stats, say)
        else:
            say("reading %s (installation %s)" % (candidate, candidate.name))
            try:
                _read_mbox(candidate, save_path, dry_run, stats, say,
                           installation=candidate.name)
            except (mailbox.Error, OSError) as exc:
                stats["errors"] += 1
                warn("cannot read %s: %s" % (candidate, exc))


def run_once(email_path, save_path, dry_run=False, scan_all=False, quiet=False):
    """Read the configured mail source once and copy every new bundle."""
    stats = {"messages": 0, "attachments": 0, "copied": 0, "would-copy": 0,
             "existing": 0, "invalid": 0, "errors": 0}
    say = (lambda message: None) if quiet else log

    if not email_path.exists():
        raise FileNotFoundError("mail path does not exist: %s" % email_path)
    if _is_maildir(email_path):
        say("reading Maildir %s (installation %s)" % (email_path, email_path.name))
        _read_maildir(email_path, save_path, dry_run, stats, say,
                      installation=email_path.name)
    elif email_path.is_dir():
        _scan_folder(email_path, save_path, dry_run, stats, say, scan_all)
    elif email_path.is_file() and email_path.name.lower().endswith(ARCHIVE_SUFFIXES):
        say("reading bundle %s" % email_path)
        _read_bare_archive(email_path, save_path, dry_run, stats, say)
    elif email_path.is_file() and _looks_like_mbox(email_path):
        say("reading mbox %s (installation %s)" % (email_path, email_path.name))
        _read_mbox(email_path, save_path, dry_run, stats, say,
                   installation=email_path.name)
    else:
        raise ValueError("not an mbox, Maildir, folder or journal bundle: %s"
                         % email_path)
    return stats


def summary(stats, dry_run=False):
    parts = ["%d message(s)" % stats["messages"]]
    if dry_run:
        parts.append("%d would be copied" % stats["would-copy"])
    else:
        parts.append("%d copied" % stats["copied"])
    parts.append("%d already present" % stats["existing"])
    parts.append("%d not a journal bundle" % stats["invalid"])
    if stats["errors"]:
        parts.append("%d error(s)" % stats["errors"])
    return ", ".join(parts)


def _run_and_log(settings, dry_run, quiet):
    try:
        stats = run_once(settings["email_path"], settings["save_path"],
                         dry_run=dry_run,
                         scan_all=settings["scan_all_mailboxes"],
                         quiet=quiet)
        log(summary(stats, dry_run))
        return stats
    except Exception as exc:  # a transient mail or disk fault must not stop the service
        warn("run failed: %s" % exc)
        return None


def _next_run(now, run_at):
    target = datetime.datetime.combine(now.date(), run_at)
    if target <= now:
        target += datetime.timedelta(days=1)
    return target


def _sleep_until(target):
    """Sleep in short steps so a clock jump or suspend cannot overrun the target."""
    while True:
        remaining = (target - datetime.datetime.now()).total_seconds()
        if remaining <= 0:
            return
        time.sleep(min(60.0, remaining))


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="rbr-bundle-copy.py",
        description="Copy RBR journal bundles from incoming email into yearly folders")
    parser.add_argument("--config", default=CONFIG_PATH,
                        help="service config (default: %s)" % CONFIG_PATH)
    parser.add_argument("--once", action="store_true",
                        help="run one pass now and exit instead of staying resident")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would be copied; change nothing")
    parser.add_argument("--quiet", action="store_true",
                        help="suppress per-file lines, but keep the run summary")
    args = parser.parse_args(argv)

    try:
        settings = load_config(args.config)
    except ValueError as exc:
        warn(str(exc))
        return 2

    if args.once:
        stats = _run_and_log(settings, args.dry_run, args.quiet)
        return 1 if stats is None or stats["errors"] else 0

    if not settings["email_path"].exists():
        warn("mail path does not exist: %s" % settings["email_path"])
        return 2
    log("watching %s; copying to %s/<YYYY>; daily at %s"
        % (settings["email_path"], settings["save_path"],
           settings["run_at"].strftime("%H:%M")))

    now = datetime.datetime.now()
    if now.time() >= settings["run_at"]:
        log("started after today's run time; running a catch-up pass")
        _run_and_log(settings, args.dry_run, args.quiet)
    while True:
        target = _next_run(datetime.datetime.now(), settings["run_at"])
        log("next run %s" % target.strftime("%Y-%m-%d %H:%M"))
        _sleep_until(target)
        _run_and_log(settings, args.dry_run, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
