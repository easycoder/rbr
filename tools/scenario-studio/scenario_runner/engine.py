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
    preferred = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "rbr-scenario-studio" / "runs"
    # A sandboxed home is often read-only. Fall back to a local, git-ignored
    # directory and, failing that, the temp directory; the run path is printed.
    candidates = [preferred, Path.cwd() / ".runs", Path(tempfile.gettempdir()) / "rbr-scenario-studio" / "runs"]
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


def run_scenario(scenario_path, repo, headless=True, jsonl=False, events=None, run_dir=None,
                 speed=0, collapse_polls=False, step_pause_ms=0):
    """Run one scenario. Returns a process exit code (0 pass, 1 fail)."""
    from .protocol import Events
    events = events or Events(jsonl)

    prepared = prepare(scenario_path, repo)
    directory = _run_dir(prepared, run_dir)
    started = time.time()
    environment = _environment(prepared, repo, headless)
    run_id = directory.name

    _write(directory / "scenario.json", json.dumps(prepared.scenario, indent=2, ensure_ascii=False) + "\n")
    _write(directory / "base-map.json", json.dumps(prepared.base_map, indent=2, ensure_ascii=False) + "\n")
    _write(directory / "environment.json", json.dumps(environment, indent=2) + "\n")

    events.emit("run.started", runId=run_id,
                scenario={"name": prepared.scenario.get("name"), "path": str(prepared.path)},
                environment=environment)

    poll_count = 0

    def on_console(entry):
        nonlocal poll_count
        text = entry["text"]
        # A demo run would otherwise fill the log with one line per 10 s poll.
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
    failure = None
    duration_ms = 0

    try:
        driver.start()
        refresh = prepared.defaults.get("refreshReply", "empty")
        if refresh in ("empty", "full", "none"):
            driver.page.evaluate("v => { window.__rbr.refreshReply = v; }", refresh)

        steps = prepared.scenario.get("steps", [])
        for index, step in enumerate(steps):
            step_id = step.get("id", f"step-{index + 1}")
            actor = ACTOR.get(next(key for key in ACTOR if key in step), "other")
            driver.current_step = step_id
            events.emit("step.started", stepId=step_id, index=index + 1,
                        at=step.get("at"), actor=actor)
            step_started = time.time()
            step_failure = None
            try:
                driver.advance_to(prepared.step_times[index])
                _execute(driver, prepared, step, speed)
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
                    print(f"  ✓ {step_id:<4} {step.get('at', ''):<6} {_summary(step, speed)}")
                if step_pause_ms > 0:
                    time.sleep(step_pause_ms / 1000.0)

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
        try:
            messages = driver.messages()
        except Exception:
            messages = []
        console_lines = list(driver.console_lines)
        trace_path = directory / "trace.zip"
        driver.stop(failure=failure, trace_path=trace_path)
        _write(directory / "result.json", json.dumps({
            "status": "failed" if failed else "passed",
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

    status = "failed" if failed else "passed"
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
    return 0 if not failed else 1


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
                suffix = "" if speed and speed > 0 else " (Demo only, skipped)"
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


def _controller(driver, prepared, controller):
    base_map = prepared.base_map
    room_name = controller.get("room")
    room_name = prepared.aliases.get(room_name, room_name)

    if "raw" in controller and "set" not in controller and "state" not in controller:
        driver.push_raw(controller["raw"])
        return

    if "set" in controller:
        index = targets.identity_index(base_map, room_name)
        for key, value in controller["set"].items():
            base_map["rooms"][index][key] = value

    if "state" in controller:
        state = controller["state"]
        profile = state.get("profile", prepared.profile_idx)
        if isinstance(profile, str):
            profile = targets.profile_index(base_map, profile)
        profile_record = base_map["profiles"][profile]
        room_state = profile_record.setdefault("rooms", {}).setdefault(room_name, {})
        for key, value in state.get("set", {}).items():
            room_state[key] = value

    if controller.get("push", True):
        driver.push_map(base_map)
