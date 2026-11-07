"""Read and write RBR journal bundles for RBR Studio.

A bundle is the transport-neutral unit the importer produces and the scenario
generator consumes. It is either a directory or a gzipped tar archive with:

    manifest.json
    events/<YYYY>/<MM>/<YYYY-MM-DD>.jsonl
    maps/<sha256>.json
    reports/heatlog/<room>/<YYYY>/<MM>/<DD>.csv   (when heat logging is on)

The manifest records the source, the day, the system and profile, the event
count and hashes, the map snapshots the day refers to, and the heating CSVs
that carry the same day's outcomes for statistics. Keeping the format small
and explicit means the local, HTTPS and email transports can all produce
the same thing, and the converter never needs to know where it came from.
"""

from __future__ import annotations

import datetime as _datetime
import hashlib
import json
import pathlib
import shutil
import tarfile
import tempfile
from dataclasses import dataclass, field

BUNDLE_FORMAT = "rbr-journal-bundle"
BUNDLE_VERSION = 1


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_events(path: pathlib.Path):
    """Yield event dictionaries from a JSONL file, skipping unparseable lines."""
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                yield event


def read_events(path: pathlib.Path) -> list[dict]:
    return list(iter_events(path))


def collect_map_hashes(events) -> list[str]:
    """Map hashes referenced by session.start and plan.snapshot events, in first-seen order."""
    seen = []
    for event in events:
        data = event.get("data") or {}
        value = data.get("mapHash")
        if value and value not in seen:
            seen.append(value)
    return seen


def heatlog_files(root, day) -> dict[str, pathlib.Path]:
    """Map bundle-relative report paths to the day's heatlog CSVs.

    The controller writes `<heatlog-root>/<room>/<YYYY>/<MM>/<DD>.csv`; the
    bundle keeps that shape under `reports/heatlog/`, so a reader can tell the
    room and the day from the path alone. Missing root or no rows is not an
    error: heat logging is optional.
    """
    if not root:
        return {}
    root = pathlib.Path(root).expanduser()
    if not root.is_dir():
        return {}
    stamp = _datetime.date.fromisoformat(str(day))
    relative_day = f"{stamp.year:04d}/{stamp.month:02d}/{stamp.day:02d}.csv"
    reports = {}
    for room in sorted(root.iterdir()):
        if not room.is_dir():
            continue
        source = room / relative_day
        if source.is_file():
            reports[f"reports/heatlog/{room.name}/{relative_day}"] = source
    return reports


def report_rows(reports: dict[str, pathlib.Path]) -> list[dict]:
    """Manifest rows for report files, rejecting paths that could escape the bundle."""
    rows = []
    for relative, source in sorted(reports.items()):
        relative = pathlib.PurePosixPath(str(relative))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"report path must stay inside the bundle: {relative}")
        source = pathlib.Path(source)
        row = {
            "kind": "heatlog" if relative.parts[:2] == ("reports", "heatlog") else "file",
            "path": relative.as_posix(),
            "bytes": source.stat().st_size,
            "sha256": sha256_file(source),
        }
        if row["kind"] == "heatlog" and len(relative.parts) >= 3:
            row["room"] = relative.parts[2]
        rows.append(row)
    return rows


def manifest_for(day_path: pathlib.Path, maps: dict[str, pathlib.Path], source: str,
                 day: str | None = None, reports: list[dict] | None = None,
                 mac: str | None = None) -> dict:
    events = read_events(day_path)
    session = next((event for event in events if event.get("type") == "session.start"), {})
    session_data = session.get("data") or {}
    first = events[0] if events else {}
    last = events[-1] if events else {}
    payload = day_path.read_bytes()
    map_rows = []
    for digest, path in sorted(maps.items()):
        map_rows.append({
            "hash": digest,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return {
        "format": BUNDLE_FORMAT,
        "version": BUNDLE_VERSION,
        "createdAt": _datetime.datetime.now(_datetime.timezone.utc).isoformat(timespec="seconds"),
        "source": source,
        "day": day or day_path.stem,
        "mac": mac,
        "events": len(events),
        "eventsBytes": len(payload),
        "eventsSha256": sha256_bytes(payload),
        "firstSeq": first.get("seq"),
        "lastSeq": last.get("seq"),
        "firstTs": first.get("ts"),
        "lastTs": last.get("ts"),
        "system": session_data.get("system"),
        "profile": session_data.get("profile"),
        "profileIndex": session_data.get("profileIndex"),
        "baseMapHash": session_data.get("mapHash"),
        "tzOffsetMinutes": first.get("tzOffsetMinutes"),
        "maps": map_rows,
        "reports": reports or [],
    }


def write_bundle(dest: pathlib.Path, day_path: pathlib.Path, maps: dict[str, pathlib.Path],
                 source: str, archive: pathlib.Path | None = None,
                 reports: dict[str, pathlib.Path] | None = None,
                 mac: str | None = None) -> dict:
    """Write a bundle directory, optionally tar.gz it, and return the manifest."""
    dest = pathlib.Path(dest)
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError(f"bundle destination is not empty: {dest}")
    day = day_path.stem
    try:
        stamp = _datetime.date.fromisoformat(day)
    except ValueError:
        raise ValueError(f"journal day file must be YYYY-MM-DD.jsonl, got {day_path.name!r}")
    events_dir = dest / "events" / f"{stamp.year:04d}" / f"{stamp.month:02d}"
    maps_dir = dest / "maps"
    events_dir.mkdir(parents=True, exist_ok=True)
    maps_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(day_path, events_dir / day_path.name)
    for digest, path in maps.items():
        shutil.copyfile(path, maps_dir / f"{digest}.json")
    reports = reports or {}
    rows = report_rows(reports)
    for relative, source_path in reports.items():
        target = dest.joinpath(*pathlib.PurePosixPath(str(relative)).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, target)
    manifest = manifest_for(day_path, maps, source, day, rows, mac)
    manifest["eventsPath"] = str((events_dir / day_path.name).relative_to(dest)).replace("\\", "/")
    (dest / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if archive is not None:
        archive = pathlib.Path(archive)
        archive.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive, "w:gz") as tar:
            for name in ("manifest.json", "events", "maps"):
                tar.add(dest / name, arcname=name)
            if (dest / "reports").is_dir():
                tar.add(dest / "reports", arcname="reports")
    return manifest


@dataclass
class Bundle:
    root: pathlib.Path
    events_path: pathlib.Path | None
    maps_dir: pathlib.Path
    manifest: dict = field(default_factory=dict)
    _temporary: tempfile.TemporaryDirectory | None = None

    @property
    def reports_dir(self) -> pathlib.Path:
        return self.root / "reports"

    def close(self):
        if self._temporary is not None:
            self._temporary.cleanup()
            self._temporary = None

    def with_temporary(self, temporary: tempfile.TemporaryDirectory) -> "Bundle":
        self._temporary = temporary
        return self

    def map_path(self, digest: str) -> pathlib.Path:
        return self.maps_dir / f"{digest}.json"

    def load_map(self, digest: str) -> dict:
        path = self.map_path(digest)
        if not path.is_file():
            raise FileNotFoundError(f"bundle is missing map snapshot {digest}")
        return json.loads(path.read_text(encoding="utf-8"))


def _safe_extract(tar: tarfile.TarFile, dest: pathlib.Path):
    """Extract only regular files/directories whose paths stay inside dest."""
    dest = dest.resolve()
    for member in tar.getmembers():
        target = (dest / member.name).resolve()
        if target != dest and dest not in target.parents:
            raise ValueError(f"bundle contains an unsafe path: {member.name}")
        if member.issym() or member.islnk():
            raise ValueError(f"bundle contains a link: {member.name}")
    try:
        tar.extractall(dest, filter="data")
    except TypeError:  # Python < 3.12
        tar.extractall(dest)


def extract_bundle(archive: pathlib.Path, dest: pathlib.Path) -> pathlib.Path:
    """Extract a bundle archive into dest, refusing paths outside it."""
    dest = pathlib.Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:*") as tar:
        _safe_extract(tar, dest)
    return dest


def open_bundle(path: pathlib.Path) -> Bundle:
    """Open a bundle directory or .tar.gz and return its events, maps and manifest."""
    path = pathlib.Path(path)
    if path.is_dir():
        manifest_path = path / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
        events_path = None
        if manifest.get("eventsPath"):
            events_path = path / manifest["eventsPath"]
        else:
            candidates = sorted(path.glob("events/*/*/*.jsonl"))
            events_path = candidates[-1] if candidates else None
        return Bundle(root=path, events_path=events_path, maps_dir=path / "maps", manifest=manifest)

    if path.is_file():
        temporary = tempfile.TemporaryDirectory(prefix="rbr-journal-bundle-")
        extract_bundle(path, pathlib.Path(temporary.name))
        return open_bundle(pathlib.Path(temporary.name)).with_temporary(temporary)
    raise FileNotFoundError(f"no such journal bundle: {path}")
