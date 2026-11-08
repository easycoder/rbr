"""Execute a prepared scenario, write artefacts and report step by step."""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from . import __version__, targets
from .errors import ScenarioError
from .page import PageDriver
from .validate import prepare

ACTOR = {
    "controller": "controller",
    "ui": "ui",
    "expect": "expect",
    "expectWire": "wire",
    "waitFor": "expect",
    "connection": "connection",
    "delay": "delay",
}


def _slug(name):
    value = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return value[:48] or "scenario"


def _data_root():
    preferred = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "rbr-studio" / "runs"
    # A sandboxed home is often read-only. Fall back to a local, git-ignored
    # directory and, failing that, the temp directory; the run path is printed.
    candidates = [preferred, Path.cwd() / ".runs", Path(tempfile.gettempdir()) / "rbr-studio" / "runs"]
    for root in candidates:
        try:
            root.mkdir(parents=True, exist_ok=True)
            probe = root / ".write-probe"
            probe.write_text("x", encoding="utf-8")
            probe.unlink()
            return root
        except OSError:
            continue
    raise ScenarioError("no writable directory for run artefacts; pass --run-dir")


def _run_dir(prepared, requested=None):
    if requested:
        directory = Path(requested).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        return directory
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    directory = _data_root() / f"{stamp}-{_slug(prepared.scenario.get('name', 'scenario'))}"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _environment(prepared, repo, headless):
    commit = ""
    try:
        commit = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        pass
    try:
        pw_version = version("playwright")
    except PackageNotFoundError:
        pw_version = "unknown"
    return {
        "runner": __version__,
        "playwright": pw_version,
        "python": sys.version.split()[0],
        "repo": str(repo),
        "commit": commit,
        "viewport": {"width": 390, "height": 844},
        "timeZone": prepared.scenario.get("clock", {}).get("timeZone") or "UTC",
        "headless": headless,
    }


def _error_detail(driver, step):
    """The best available actual value, for the failure report."""
    try:
        if "expect" in step:
            selector = driver.selector(step["expect"]["target"])
            locator = driver.page.locator(selector)
            if locator.count() == 0:
                return f"no element for {step['expect']['target']!r} ({selector})"
            return locator.first.text_content(timeout=1000)
        if "expectWire" in step:
            messages = driver.messages()[-3:]
            parsed = []
            for item in messages:
                outer = driver._outer(item)
                if isinstance(outer, dict):
                    parsed.append(outer)
            return parsed
    except Exception:
        pass
    return None


def _write(path, text):
    path.write_text(text, encoding="utf-8")


def _append_description(scenario, note):
    description = scenario.get("description")
    if isinstance(description, str) and description.strip():
        scenario["description"] = description.rstrip() + " " + note
    else:
        scenario["description"] = note


def _fold_to_marker(prepared, steps, marker):
    """Apply the controller steps before `marker` to the base map.

    Returns `(start_index, folded, warning)`. This is the safe start for a
    breakpoint: the map the browser receives is the state just before the
    marker, without replaying a day of events through the page. A step that
    cannot be folded (a raw payload that is not a map, or a bad room/profile)
    becomes the start so it still runs in the browser.
    """
    folded = 0
    for index in range(marker):
        controller = steps[index].get("controller")
        if not isinstance(controller, dict):
            continue  # UI and expectation steps do not change the map
        try:
            raw = _apply_controller(prepared.base_map, prepared.aliases,
                                    prepared.profile_idx, controller)
        except Exception as exc:  # noqa: BLE001 - report the start, do not crash
            return index, folded, (
                f"cannot fold {steps[index].get('id')} ({exc}); starting there")
        if raw is not None:
            try:
                payload = json.loads(raw)
            except (TypeError, ValueError):
                return index, folded, (
                    f"cannot fold the raw payload at {steps[index].get('id')}; starting there")
            if not isinstance(payload, dict) or not ("rooms" in payload or "profiles" in payload):
                return index, folded, (
                    f"cannot fold the raw payload at {steps[index].get('id')}; starting there")
            prepared.base_map.clear()
            prepared.base_map.update(payload)
        folded += 1
    return marker, folded, None


def _await_command(commands):
    """Block for one of the playback commands, ignoring unknown lines."""
    if commands is None:
        return "continue"
    while True:
        command = commands.next()
        if not isinstance(command, dict):
            continue
        name = command.get("command")
        if name in ("step", "continue", "cancel", "eof"):
            return name


def run_scenario(scenario_path, repo, headless=True, jsonl=False, events=None, run_dir=None,
                 speed=0, collapse_polls=False, step_pause_ms=0, end_pause_ms=0,
                 fold_to_marker=False, pause_at_marker=False, commands=None):
    """Run one scenario. Returns a process exit code (0 pass, 1 fail)."""
    from .protocol import Events
    events = events or Events(jsonl)

    prepared = prepare(scenario_path, repo)
    steps = prepared.scenario.get("steps", [])
    marker = next((i for i, step in enumerate(steps) if step.get("marker")), None)
    trim = None
    trim_warning = None
    if fold_to_marker and marker is not None:
        start_index, folded, trim_warning = _fold_to_marker(prepared, steps, marker)
        trimmed_steps = steps[start_index:]
        trimmed_times = prepared.step_times[start_index:]
        if trimmed_steps and trimmed_times:
            prepared.start = trimmed_times[0]
            prepared.step_times = trimmed_times
            prepared.scenario["steps"] = trimmed_steps
            prepared.scenario.setdefault("home", {})["map"] = prepared.base_map
            prepared.scenario.setdefault("clock", {})["start"] = prepared.start.isoformat(timespec="seconds")
            _append_description(
                prepared.scenario,
                f"Show: folded {folded} controller step(s) and skipped {start_index} "
                f"pre-breakpoint step(s); started at {trimmed_steps[0].get('id')} "
                f"({trimmed_steps[0].get('at')}).")
            trim = {
                "folded": folded,
                "skipped": start_index,
                "startIndex": start_index + 1,
                "startStepId": trimmed_steps[0].get("id"),
                "markerStepId": steps[marker].get("id"),
            }
            marker = marker - start_index
            steps = trimmed_steps

    directory = _run_dir(prepared, run_dir)
    started = time.time()
    environment = _environment(prepared, repo, headless)
    run_id = directory.name

    _write(directory / "scenario.json", json.dumps(prepared.scenario, indent=2, ensure_ascii=False) + "\n")
    _write(directory / "base-map.json", json.dumps(prepared.base_map, indent=2, ensure_ascii=False) + "\n")
    _write(directory / "environment.json", json.dumps(environment, indent=2) + "\n")

    started_fields = {
        "runId": run_id,
        "scenario": {"name": prepared.scenario.get("name"), "path": str(prepared.path)},
        "environment": environment,
    }
    if trim is not None:
        started_fields["trim"] = trim
    events.emit("run.started", **started_fields)
    if trim is not None:
        events.emit("log", stepId=trim["startStepId"], level="info", source="runner",
                    message=(f"Show start: folded {trim['folded']} controller step(s) "
                             f"and skipped {trim['skipped']} pre-breakpoint step(s); "
                             f"starting at {trim['startStepId']}"))
    if trim_warning:
        events.emit("log", stepId=None, level="warn", source="runner", message=trim_warning)

    poll_count = 0

    def on_console(entry):
        nonlocal poll_count
        text = entry["text"]
        # A Show run would otherwise fill the log with one line per 10 s poll.
        # The full console is still written to the run's console.log.
        if collapse_polls and "Requesting map: refresh" in text:
            poll_count += 1
            if poll_count % 50 == 0:
                events.emit("log", stepId=entry["step"], level="info", source="console",
                            message=f"refresh ×{poll_count} (collapsed)")
            return
        events.emit(
            "log", stepId=entry["step"], level="error" if entry["type"] == "error" else
            "warn" if entry["type"] in ("warning", "warn") else "info",
            source="console", message=text)

    driver = PageDriver(
        prepared, repo, headless,
        on_console=on_console, speed=speed)
    results = []
    failed = False
    cancelled = False
    failure = None
    duration_ms = 0

    try:
        driver.start()
        refresh = prepared.defaults.get("refreshReply", "empty")
        if refresh in ("empty", "full", "none"):
            driver.page.evaluate("v => { window.__rbr.refreshReply = v; }", refresh)

        if marker is not None:
            if pause_at_marker:
                message = (f"breakpoint at {steps[marker].get('id')}: "
                           "Show pauses after this step; Step advances one step")
            else:
                message = (f"marker at {steps[marker].get('id')}: "
                           "earlier steps run at maximum speed")
            events.emit("log", stepId=steps[marker].get("id"), level="info",
                        source="runner", message=message)
        auto = True
        for index, step in enumerate(steps):
            if commands is not None:
                pending = commands.poll()
                while pending is not None:
                    if pending.get("command") == "cancel":
                        cancelled = True
                    pending = commands.poll()
                if cancelled:
                    break
            step_id = step.get("id", f"step-{index + 1}")
            actor = ACTOR.get(next(key for key in ACTOR if key in step), "other")
            fast = marker is not None and index < marker
            manual = pause_at_marker and marker is not None and not auto
            step_speed = 0 if fast or manual else speed
            driver.current_step = step_id
            events.emit("step.started", stepId=step_id, index=index + 1,
                        at=step.get("at"), actor=actor)
            step_started = time.time()
            step_failure = None
            try:
                driver.advance_to(prepared.step_times[index], speed=step_speed)
                _execute(driver, prepared, step, step_speed)
            except Exception as exc:  # noqa: BLE001 - this is the failure boundary
                failed = True
                detail = str(exc)
                screenshot = directory / "screenshots" / f"{step_id}.png"
                screenshot.parent.mkdir(parents=True, exist_ok=True)
                try:
                    driver.screenshot(screenshot)
                    events.emit("artifact", stepId=step_id, kind="screenshot", path=str(screenshot))
                except Exception:
                    pass
                step_failure = {
                    "message": detail,
                    "expected": _expected(step),
                    "actual": _error_detail(driver, step),
                }
                failure = failure or step_failure
                if jsonl:
                    print(f"{step_id} failed: {detail}", file=sys.stderr)
                else:
                    print(f"  ✗ {step_id:<4} {step.get('at', ''):<6} {detail}")

            duration = int((time.time() - step_started) * 1000)
            results.append({
                "id": step_id, "at": step.get("at"), "actor": actor,
                "status": "failed" if step_failure else "passed",
                "durationMs": duration,
                **({"failure": step_failure} if step_failure else {}),
            })
            if step_failure:
                events.emit("step.finished", stepId=step_id, status="failed",
                            durationMs=duration, failure=step_failure)
                if not prepared.continue_on_failure:
                    break
            else:
                events.emit("step.finished", stepId=step_id, status="passed", durationMs=duration)
                if not jsonl:
                    print(f"  ✓ {step_id:<4} {step.get('at', ''):<6} {_summary(step, step_speed)}")
                if step_pause_ms > 0 and not fast:
                    time.sleep(step_pause_ms / 1000.0)

            if pause_at_marker and marker is not None and index >= marker:
                if index == marker:
                    auto = False
                if not auto and index + 1 < len(steps):
                    next_step = steps[index + 1]
                    events.emit("run.paused", stepId=step_id, index=index + 1,
                                nextStepId=next_step.get("id"),
                                reason="marker" if index == marker else "step")
                    action = _await_command(commands)
                    if action in ("continue", "eof"):
                        auto = True
                    elif action == "cancel":
                        cancelled = True
                        break

        if collapse_polls and poll_count:
            events.emit("log", stepId=None, level="info", source="console",
                        message=f"refresh polls: {poll_count} (collapsed)")

        if driver.page_errors and prepared.defaults.get("failOnPageError", True):
            failed = True
            failure = failure or {
                "message": "the page reported an error",
                "actual": driver.page_errors,
            }
        duration_ms = int((time.time() - started) * 1000)
    except Exception as exc:  # start-up failures (browser, runtime fetch, page boot)
        failed = True
        failure = {"message": f"the run could not start: {exc}"}
        duration_ms = int((time.time() - started) * 1000)
    finally:
        # A Show run can leave the final state on screen for a moment before the
        # headed browser window disappears. Normal runs leave this at zero.
        if end_pause_ms > 0 and driver.browser is not None:
            time.sleep(end_pause_ms / 1000.0)
        try:
            messages = driver.messages()
        except Exception:
            messages = []
        console_lines = list(driver.console_lines)
        trace_path = directory / "trace.zip"
        driver.stop(failure=failure, trace_path=trace_path)
        _write(directory / "result.json", json.dumps({
            "status": "cancelled" if cancelled else ("failed" if failed else "passed"),
            "scenario": prepared.scenario.get("name"),
            "runId": run_id,
            "durationMs": duration_ms,
            "steps": results,
            "pageErrors": driver.page_errors,
        }, indent=2, ensure_ascii=False) + "\n")
        _write(directory / "wire.jsonl", "\n".join(messages) + ("\n" if messages else ""))
        _write(directory / "console.log", "\n".join(
            f"[{entry['step'] or '-'}] {entry['type']}: {entry['text']}" for entry in console_lines) + "\n")
        if trace_path.exists():
            events.emit("artifact", kind="trace", path=str(trace_path))

    status = "cancelled" if cancelled else ("failed" if failed else "passed")
    events.emit("run.finished", status=status, passed=sum(1 for item in results if item["status"] == "passed"),
                failed=sum(1 for item in results if item["status"] == "failed"),
                durationMs=duration_ms,
                artifacts={"dir": str(directory), "result": str(directory / "result.json"),
                           "wire": str(directory / "wire.jsonl"), "console": str(directory / "console.log"),
                           **({"trace": str(directory / "trace.zip")} if (directory / "trace.zip").exists() else {})})

    if not jsonl:
        print()
        print(f"{status.upper()}  {prepared.scenario.get('name')}  ({duration_ms} ms)")
        print(f"artefacts: {directory}")
        if failure:
            print(f"failure: {failure.get('message')}")
    return 0 if status == "passed" else 1


def _expected(step):
    for key in ("expect", "expectWire", "waitFor", "connection", "ui", "controller"):
        if key in step:
            return step[key]
    return None


def _summary(step, speed=0):
    for key in ("controller", "ui", "expect", "expectWire", "waitFor", "connection", "delay"):
        if key in step:
            if key == "controller":
                controller = step[key]
                if "raw" in controller:
                    return "raw push"
                parts = []
                if "set" in controller:
                    parts.append("identity " + ", ".join(f"{k} = {v}" for k, v in controller["set"].items()))
                if "state" in controller:
                    parts.append("state " + ", ".join(f"{k} = {v}" for k, v in controller["state"].get("set", {}).items()))
                return "; ".join(parts) or "push"
            if key == "ui":
                action, value = next(iter(step[key].items()))
                if isinstance(value, str):
                    return f"{action} {value}"
                return f"{action} {value.get('target')} = {value.get('value', '')}"
            if key == "expect":
                value = step[key]
                return f"{value.get('target')} {next((k + ' ' + str(v) for k, v in value.items() if k != 'target'), '')}"
            if key == "expectWire":
                value = step[key]
                return f"{value.get('request')} {value.get('match', '')}"
            if key == "waitFor":
                return f"{step[key].get('target')} {step[key].get('state', 'visible')}"
            if key == "connection":
                return step[key].get("action", "connection")
            if key == "delay":
                suffix = "" if speed and speed > 0 else " (Show only, skipped)"
                return f"wait {step[key]} s{suffix}"
    return ""


def _execute(driver, prepared, step, speed=0):
    controller = step.get("controller")
    if controller is not None:
        _controller(driver, prepared, controller)
        return

    ui = step.get("ui")
    if ui is not None:
        timeout = prepared.step_timeout_ms(step)
        if "tap" in ui:
            driver.tap(ui["tap"], timeout)
        elif "select" in ui:
            driver.select(ui["select"]["target"], ui["select"]["value"], timeout)
        elif "fill" in ui:
            driver.fill(ui["fill"]["target"], ui["fill"]["value"], timeout)
        elif "scroll" in ui:
            driver.scroll(ui["scroll"]["target"], ui["scroll"].get("deltaY", 0), timeout)
        return

    expect = step.get("expect")
    if expect is not None:
        driver.assert_expect(expect, prepared.step_timeout_ms(step))
        return

    wire = step.get("expectWire")
    if wire is not None:
        timeout = int(wire.get("withinMs") or prepared.step_timeout_ms(step))
        driver.wait_wire(wire["request"], wire.get("match") or {}, wire.get("notMatch") or {}, timeout)
        return

    wait = step.get("waitFor")
    if wait is not None:
        driver.wait_for(wait, prepared.step_timeout_ms(step))
        return

    delay = step.get("delay")
    if delay is not None:
        if speed and speed > 0:
            time.sleep(float(delay))
        return

    connection = step.get("connection")
    if connection is not None:
        driver.connection(connection["action"], connection.get("message"))
        return

    raise ScenarioError("step has no executable action")


def _apply_controller(base_map, aliases, profile_idx, controller):
    """Apply one controller step to the map; return a raw payload when it is raw."""
    room_name = controller.get("room")
    room_name = aliases.get(room_name, room_name)

    if "raw" in controller and "set" not in controller and "state" not in controller:
        return controller["raw"]

    if "set" in controller:
        index = targets.identity_index(base_map, room_name)
        for key, value in controller["set"].items():
            base_map["rooms"][index][key] = value

    if "state" in controller:
        state = controller["state"]
        profile = state.get("profile", profile_idx)
        if isinstance(profile, str):
            profile = targets.profile_index(base_map, profile)
        profile_record = base_map["profiles"][profile]
        room_state = profile_record.setdefault("rooms", {}).setdefault(room_name, {})
        for key, value in state.get("set", {}).items():
            room_state[key] = value
    return None


def _controller(driver, prepared, controller):
    raw = _apply_controller(prepared.base_map, prepared.aliases,
                            prepared.profile_idx, controller)
    if raw is not None:
        driver.push_raw(raw)
        return
    if controller.get("push", True):
        driver.push_map(prepared.base_map)
