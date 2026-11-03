#!/usr/bin/env python3
"""heatwatch.py — bounce the heating stack when a scheduled room does not warm.

The controller records each room's target, actual temperature and mode in the
heating log (`<heatlog-root>/<room>/YYYY/MM/DD.csv`, see doc/HEATING-DATA.md).
A room whose plan calls for heat — Timed, On or Boost — with a relay or TRV, a
fresh thermometer, and a target at least 0.5 C above the room's current reading
should warm. If it has not warmed by at least 0.2 C over 60 minutes, the
software may be wedged: the controller can be running without driving the
relays, or the Zigbee bridge can have stopped forwarding commands. This check
restarts the four core services once that is true, with a three-hour cooldown so
a persistent fault cannot become a restart loop, and at most three restarts in
any 24 hours before it leaves the fault for a person.

Evidence, in order:

1. the heating log, when `heatlog-root` is configured — it carries the start of
   the current demand run and the actual temperature through it;
2. a per-room state file, when the log is off — the first sighting records the
   baseline, and later runs measure from it.

Only rooms that can actually heat are considered: linked rooms with a relay or
TRV, a fresh thermometer reading (the controller's own 45-minute staleness
gate), and a target gap of at least 0.5 C. A room that is merely near its
target is left alone, because a tenth of a degree is not evidence of a fault.

The state file lives in the volatile directory when `volatile-root` names one,
so a reboot clears the baselines and the cooldown with the rest of the
regenerable runtime state. Running with `--dry-run` reports what it would do
and changes nothing.

Usage:
    python3 heatwatch.py [--rbr-dir DIR] [--dry-run]
"""

import argparse
import csv
import datetime
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

SERVICES = ("mosquitto", "zigbee2mqtt", "rbr-zigbee-bridge", "controller")
MODE_LETTERS = {"off": "o", "on": "c", "timed": "p", "boost": "b"}
DEMAND_GAP_C = 0.5
WINDOW_MIN = 60
RISE_C = 0.2
COOLDOWN_MIN = 180
MAX_RESTARTS_PER_DAY = 3
SENSOR_STALE_MS = 45 * 60 * 1000


def log(message):
    """Write one line for the systemd journal (SyslogIdentifier=rbr-watchdog)."""
    print("heatwatch: " + message, flush=True)


def read_one_line(path):
    """Return the first non-empty line of `path`, or None."""
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    return line
    except OSError:
        pass
    return None


def load_json(path):
    """Return parsed JSON from `path`, or None when absent/unreadable."""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def to_float(value):
    """Convert a number or numeric string to float, or None."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def active_profile(map_data, weekday):
    """Return the profile the controller is using today, or None.

    The calendar is authoritative when it is on and names a profile that still
    exists. Otherwise the selected profile index is used, exactly as the
    controller does when the calendar entry is missing or stale.
    """
    profiles = map_data.get("profiles") or []
    if not isinstance(profiles, list) or not profiles:
        return None
    if map_data.get("calendar") == "on":
        calendar_data = map_data.get("calendar-data") or []
        if isinstance(calendar_data, list) and 0 <= weekday < len(calendar_data):
            day = calendar_data[weekday]
            if isinstance(day, dict):
                name = day.get(f"day{weekday}-profile")
                if name:
                    for profile in profiles:
                        if isinstance(profile, dict) and profile.get("name") == name:
                            return profile
                    log(f"calendar names profile '{name}', which is not in the profile list")
    index = map_data.get("profile", 0)
    try:
        index = int(index)
    except (TypeError, ValueError):
        index = 0
    if index < 0 or index >= len(profiles):
        index = 0
    profile = profiles[index]
    return profile if isinstance(profile, dict) else None


def profile_rooms(profile):
    """Return a room-name-keyed dict for a profile, accepting the old list form."""
    rooms = profile.get("rooms") if isinstance(profile, dict) else None
    if isinstance(rooms, dict):
        return rooms
    if isinstance(rooms, list):
        return {room.get("name"): room for room in rooms if isinstance(room, dict)}
    return {}


def period_contains(now_min, on_min, off_min):
    """True when a wall-clock minute is inside an on/off period (wrap handled)."""
    if on_min == off_min:
        return True
    if on_min < off_min:
        return on_min <= now_min < off_min
    return now_min >= on_min or now_min < off_min


def parse_minutes(text):
    """Parse 'HH:MM' to minutes since midnight, or None."""
    try:
        hour, minute = str(text).split(":", 1)
        return int(hour) * 60 + int(minute)
    except (TypeError, ValueError):
        return None


def natural_target(periods, now):
    """Return the natural schedule's target at `now`, or None.

    This is the period containment rule the controller uses. It is only used
    when the controller has not recorded an active period, because an Advance
    or a one-off override can deliberately make the effective schedule differ
    from the natural one.
    """
    now_min = now.hour * 60 + now.minute
    for period in periods:
        on_min = parse_minutes(period.get("on"))
        off_min = parse_minutes(period.get("off"))
        if on_min is not None and off_min is not None and period_contains(now_min, on_min, off_min):
            return to_float(period.get("temp"))
    return None


def scheduled_target(profile_room, now, override_active=False):
    """Return the room's effective target in Celsius, or None if not scheduled on.

    `period` is the controller's active-period index and is the authoritative
    signal for Timed mode: -1 means the schedule is in background, and an index
    into the effective (enabled-only) period list otherwise. When the map says
    background but the natural schedule says a period is running, the controller
    may have wedged at the boundary without processing it — so the natural
    target is used as the demand signal, unless an Advance or one-off override
    explains the difference. The period list is only used to resolve the target;
    the caller prefers the heating log when it has one.
    """
    if not isinstance(profile_room, dict):
        return None
    mode = profile_room.get("mode", "off")
    if mode == "off":
        return None
    if mode in ("on", "boost"):
        if mode == "boost":
            until = to_float(profile_room.get("until"))
            if until is not None and until <= now.timestamp() * 1000:
                return None
        return to_float(profile_room.get("target"))
    if mode != "timed":
        return None

    periods = [
        period
        for period in (profile_room.get("periods") or [])
        if isinstance(period, dict) and period.get("enabled", True) is not False
    ]
    period_index = profile_room.get("period")
    if isinstance(period_index, int) and not isinstance(period_index, bool):
        if period_index >= 0:
            if period_index >= len(periods):
                return None
            return to_float(periods[period_index].get("temp"))
        # Background according to the controller. An Advance from a period
        # deliberately turns the heat off, and a one-off override can drop the
        # period; otherwise the natural schedule is the honest answer.
        if override_active or profile_room.get("advance") == "A":
            return None
        return natural_target(periods, now)

    # A map from before `period` was persisted: fall back to containment, but
    # only when there is no advance/override that could have shifted the target.
    if override_active or profile_room.get("advance") == "A":
        return None
    return natural_target(periods, now)


def has_actuator(identity):
    """True when the room has something that can release heat."""
    if not isinstance(identity, dict):
        return False
    if identity.get("trv"):
        return True
    relays = identity.get("relays")
    return isinstance(relays, list) and len(relays) > 0


def thermometer_temp(thermometers, sensor, now_ms):
    """Return the room temperature in Celsius, or None when absent or stale.

    The 45-minute threshold matches the controller's own staleness gate in
    ProcessRoom: beyond it the controller treats the reading as missing and
    forces the relay off, so there is no demand to check.
    """
    if not sensor or not isinstance(thermometers, dict):
        return None
    entry = thermometers.get(sensor)
    if not isinstance(entry, dict):
        return None
    temperature = to_float(entry.get("temp"))
    timestamp = to_float(entry.get("ts"))
    if temperature is None or timestamp is None:
        return None
    if now_ms - timestamp > SENSOR_STALE_MS:
        return None
    return temperature / 100.0


def resolve_volatile_dir(rbr_dir):
    """Return the volatile directory named by `volatile-root`, else the RBR dir."""
    value = read_one_line(rbr_dir / "volatile-root")
    base = Path(value).expanduser() if value else rbr_dir
    if not base.is_absolute():
        base = rbr_dir / base
    return base


def thermometers_path(rbr_dir):
    """Return the thermometers.json path, preferring a file that exists."""
    volatile = resolve_volatile_dir(rbr_dir)
    for candidate in (volatile / "thermometers.json", rbr_dir / "thermometers.json"):
        if candidate.is_file():
            return candidate
    return volatile / "thermometers.json"


def load_thermometers(rbr_dir):
    """Load the controller's readings, falling back to the bridge's own file.

    `thermometers.json` is written by the controller once a minute, so it goes
    stale when the controller is wedged — exactly the failure this check exists
    to catch. The bridge writes `zigbee-temperatures.json` from every report, so
    its entries are merged in and the fresher copy wins per sensor.
    """
    readings = load_json(thermometers_path(rbr_dir))
    merged = dict(readings) if isinstance(readings, dict) else {}
    bridge = load_json(resolve_volatile_dir(rbr_dir) / "zigbee-temperatures.json")
    if isinstance(bridge, dict):
        for sensor, entry in bridge.items():
            if not isinstance(entry, dict):
                continue
            current = merged.get(sensor)
            if not isinstance(current, dict):
                merged[sensor] = entry
                continue
            entry_ts = to_float(entry.get("ts"))
            current_ts = to_float(current.get("ts")) or 0
            if entry_ts is not None and entry_ts > current_ts:
                merged[sensor] = entry
    return merged


def heatlog_root(rbr_dir):
    """Return the heating-data root named by `heatlog-root`, or None."""
    value = read_one_line(rbr_dir / "heatlog-root")
    if not value:
        return None
    root = Path(value).expanduser()
    if not root.is_absolute():
        root = rbr_dir / root
    return root


def state_path(rbr_dir):
    """Return the state file path, in the volatile directory when one is named."""
    return resolve_volatile_dir(rbr_dir) / "heat-watch-state.json"


def load_state(path):
    """Load the state file into a dict with a `rooms` mapping."""
    data = load_json(path)
    if not isinstance(data, dict):
        data = {}
    if not isinstance(data.get("rooms"), dict):
        data["rooms"] = {}
    return data


def save_state(path, state):
    """Atomically write the state file; failure is logged, never fatal.

    The parent directory is not created here: on a controller it is the tmpfs
    that `rbr-setup.sh` installs with the controller user's ownership, and a
    root-owned directory created by this check would lock the controller out.
    A missing directory therefore costs the state file, not the heating.
    """
    try:
        temporary = path.with_name(path.name + ".tmp")
        with open(temporary, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(temporary, path)
    except OSError as exc:
        log(f"could not save state to {path}: {exc}")


def sanitise_room(name):
    """Make a room name safe as a single path component, matching heatlog.py."""
    cleaned = []
    for character in str(name):
        if character in ("/", "\\", "\x00"):
            cleaned.append("-")
        elif ord(character) < 32:
            continue
        else:
            cleaned.append(character)
    folder = "".join(cleaned).strip()
    return "unnamed" if folder in ("", ".", "..") else folder


def heatlog_day_path(root, room, day):
    """Return `<root>/<room>/<YYYY>/<MM>/<DD>.csv` for a date."""
    return root / sanitise_room(room) / f"{day.year:04d}" / f"{day.month:02d}" / f"{day.day:02d}.csv"


def read_heatlog_rows(root, room, now):
    """Read yesterday's and today's rows for one room, oldest first.

    Rows are `epochMinutes,targetTenths,actualTenths,mode`. Rows are appended on
    change only, so a steady room logs very little; forward-filling is implicit
    in the run scan at the end of this module.
    """
    rows = []
    for days_ago in (1, 0):
        path = heatlog_day_path(root, room, now.date() - datetime.timedelta(days=days_ago))
        try:
            with open(path, newline="", encoding="utf-8") as fh:
                for line in csv.reader(fh):
                    if len(line) != 4:
                        continue
                    try:
                        minute = int(line[0])
                        target = int(line[1])
                        actual = int(line[2])
                    except ValueError:
                        continue
                    mode = line[3].strip().lower()
                    rows.append((minute, target, actual, mode))
        except OSError:
            continue
    rows.sort(key=lambda row: row[0])
    return rows[-2000:]


def demand_row(row):
    """True when a heating-log row implies the relay was calling for heat."""
    _, target, actual, mode = row
    return mode in ("c", "p", "b") and target > actual


@dataclass
class HeatlogRun:
    """The current uninterrupted demand run taken from the heating log."""

    start_min: int
    baseline_tenths: int
    max_tenths: int
    target_tenths: int
    mode: str


def heatlog_run(rows, now_min):
    """Return the current demand run, or None when the log does not show one."""
    rows = [row for row in rows if row[0] <= now_min]
    if not rows or not demand_row(rows[-1]):
        return None
    start = len(rows) - 1
    while start > 0 and demand_row(rows[start - 1]):
        start -= 1
    run = rows[start:]
    return HeatlogRun(
        start_min=run[0][0],
        baseline_tenths=run[0][2],
        max_tenths=max(row[2] for row in run),
        target_tenths=run[-1][1],
        mode=run[-1][3],
    )


@dataclass
class RoomFailure:
    """A room that has been calling for heat without warming."""

    name: str
    target_c: float
    actual_c: float
    elapsed_min: float
    rise_c: float

    def describe(self):
        return (
            f"{self.name}: target {self.target_c:.1f} °C, actual {self.actual_c:.1f} °C, "
            f"rise {self.rise_c:.1f} °C in {self.elapsed_min:.0f} min"
        )


@dataclass
class Outcome:
    """What a run found and did."""

    failures: list = field(default_factory=list)
    restarted: bool = False
    suppressed: bool = False
    restart_failed: list = field(default_factory=list)
    dry_run: bool = False

    def exit_code(self):
        return 1 if self.restart_failed else 0


def restart_services(services=SERVICES):
    """Restart each core service, skipping units that are not installed.

    Returns the names of services whose restart failed. A missing unit is not a
    failure: the controller is optional on a machine that runs it by hand.
    """
    failed = []
    for service in services:
        try:
            loaded = subprocess.run(
                ["systemctl", "show", "--property=LoadState", "--value", service],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if (loaded.stdout or "").strip() == "not-found":
                log(f"{service}: unit not installed — skipped")
                continue
            result = subprocess.run(
                ["systemctl", "restart", service],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            log(f"{service}: restart failed ({exc})")
            failed.append(service)
            continue
        if result.returncode == 0:
            log(f"{service}: restarted")
        else:
            detail = (result.stderr or "").strip()
            log(f"{service}: restart failed (exit {result.returncode}{': ' + detail if detail else ''})")
            failed.append(service)
    return failed


def run(rbr_dir, now=None, window_min=WINDOW_MIN, rise_c=RISE_C,
        gap_c=DEMAND_GAP_C, cooldown_min=COOLDOWN_MIN, dry_run=False,
        restart=restart_services):
    """Evaluate every scheduled room and restart the stack when one is cold.

    Pure apart from the restart callback and the state file, so the unit tests
    can drive it with a fixed clock and a temporary RBR directory.
    """
    rbr_dir = Path(rbr_dir)
    now = time.time() if now is None else float(now)
    now_dt = datetime.datetime.fromtimestamp(now)
    now_ms = int(now * 1000)
    now_min = int(now // 60)
    outcome = Outcome(dry_run=dry_run)

    map_data = load_json(rbr_dir / "map.json")
    if not isinstance(map_data, dict) or not isinstance(map_data.get("profiles"), list):
        log("no readable map.json — skipping the heating check")
        return outcome

    profile = active_profile(map_data, now_dt.weekday())
    if profile is None:
        log("no active profile in map.json — skipping the heating check")
        return outcome

    identities = {}
    identity_rooms = map_data.get("rooms") or []
    if isinstance(identity_rooms, dict):
        identity_rooms = list(identity_rooms.values())
    if isinstance(identity_rooms, list):
        for room in identity_rooms:
            if isinstance(room, dict) and room.get("name"):
                identities[room["name"]] = room

    thermometers = load_thermometers(rbr_dir)

    heatlog = heatlog_root(rbr_dir)
    state_file = state_path(rbr_dir)
    state = load_state(state_file)
    previous_rooms = state.get("rooms", {})
    new_rooms = {}

    overrides = map_data.get("overrides") if isinstance(map_data.get("overrides"), dict) else {}
    today_key = now_dt.strftime("%Y-%m-%d")

    for name, profile_room in profile_rooms(profile).items():
        identity = identities.get(name)
        if not isinstance(profile_room, dict) or identity is None:
            continue
        if identity.get("linked", "yes") == "no" or not has_actuator(identity):
            continue

        actual_c = thermometer_temp(thermometers, identity.get("sensor"), now_ms)
        if actual_c is None:
            continue

        override_active = False
        override = overrides.get(name)
        if isinstance(override, dict) and override.get("date") == today_key:
            override_active = True

        target_c = scheduled_target(profile_room, now_dt, override_active)

        rows = read_heatlog_rows(heatlog, name, now_dt) if heatlog else []
        run_data = heatlog_run(rows, now_min) if rows else None
        mode_letter = MODE_LETTERS.get(profile_room.get("mode", "off"))
        if run_data is not None and run_data.mode != mode_letter:
            run_data = None
        # A one-off override edits the effective period list, so the map's
        # `period` index no longer lines up with the stored `periods`. The
        # heating log carries the target the controller actually used; without
        # it, leave the room alone rather than guess at the wrong period.
        if override_active and run_data is None:
            continue
        # The log is the controller's own record of the effective target, so it
        # is better than the map when an override or advance is in play.
        if run_data is not None:
            target_c = run_data.target_tenths / 10.0

        if target_c is None or target_c - actual_c < gap_c - 1e-9:
            continue

        previous = previous_rooms.get(name)
        if not isinstance(previous, dict):
            previous = {}
        since = to_float(previous.get("since"))
        baseline = to_float(previous.get("baseline"))
        maximum = to_float(previous.get("max"))
        if since is None or baseline is None or maximum is None:
            since = now
            baseline = actual_c
            maximum = actual_c
        maximum = max(maximum, actual_c)

        # The heating log knows the real start of the run, including a run that
        # began before the watchdog first sampled it, so it supersedes the
        # state file whenever the log shows a live demand run.
        if run_data is not None:
            since = run_data.start_min * 60
            baseline = run_data.baseline_tenths / 10.0
            maximum = max(run_data.max_tenths / 10.0, actual_c)

        new_rooms[name] = {
            "since": since,
            "baseline": baseline,
            "max": maximum,
            "target": target_c,
        }

        elapsed_min = (now - since) / 60.0
        rise = maximum - baseline
        if elapsed_min >= window_min and rise < rise_c - 1e-9:
            outcome.failures.append(
                RoomFailure(name, target_c, actual_c, elapsed_min, rise)
            )

    state["rooms"] = new_rooms

    def persist():
        if not dry_run:
            save_state(state_file, state)

    if not outcome.failures:
        persist()
        return outcome

    detail = "; ".join(failure.describe() for failure in outcome.failures)
    last_restart = to_float(state.get("last_restart")) or 0.0
    raw_history = state.get("restarts")
    if not isinstance(raw_history, list):
        raw_history = []
    history = [
        restart_time
        for restart_time in raw_history
        if to_float(restart_time) is not None and now - float(restart_time) < 86400
    ]
    state["restarts"] = history
    if len(history) >= MAX_RESTARTS_PER_DAY:
        log(f"{detail} — restart suppressed, {MAX_RESTARTS_PER_DAY} restarts in 24 h; needs attention")
        outcome.suppressed = True
        persist()
        return outcome
    if last_restart and now - last_restart < cooldown_min * 60:
        remaining = int((cooldown_min * 60 - (now - last_restart)) / 60) + 1
        log(f"{detail} — restart suppressed, {remaining} min of cooldown left")
        outcome.suppressed = True
        persist()
        return outcome

    if dry_run:
        log(f"{detail} — dry-run: would restart {' '.join(SERVICES)}")
        return outcome

    log(f"{detail} — restarting {' '.join(SERVICES)}")
    outcome.restarted = True
    outcome.restart_failed = restart()
    history.append(now)
    state["restarts"] = history
    state["last_restart"] = now
    state["rooms"] = {}
    save_state(state_file, state)
    if outcome.restart_failed:
        log(f"restart failed for: {', '.join(outcome.restart_failed)}")
    return outcome


def parse_args(argv=None):
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        prog="heatwatch.py",
        description="Restart the heating stack when a scheduled room does not warm.",
    )
    parser.add_argument(
        "--rbr-dir",
        default=os.path.dirname(os.path.abspath(__file__)),
        help="controller directory holding map.json (default: this script's directory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would happen; do not restart anything",
    )
    parser.add_argument("--window-min", type=float, default=WINDOW_MIN)
    parser.add_argument("--rise-c", type=float, default=RISE_C)
    parser.add_argument("--gap-c", type=float, default=DEMAND_GAP_C)
    parser.add_argument("--cooldown-min", type=float, default=COOLDOWN_MIN)
    return parser.parse_args(argv)


def main(argv=None):
    """Run one check and return a process exit code."""
    args = parse_args(argv)
    outcome = run(
        args.rbr_dir,
        window_min=args.window_min,
        rise_c=args.rise_c,
        gap_c=args.gap_c,
        cooldown_min=args.cooldown_min,
        dry_run=args.dry_run,
    )
    return outcome.exit_code()


if __name__ == "__main__":
    sys.exit(main())
