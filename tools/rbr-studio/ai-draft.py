#!/usr/bin/env python3
"""Draft a scenario from a natural-language brief.

The AI is a bounded JSON author: it receives the schema, the target vocabulary,
a privacy-reduced summary of the local map, two worked examples and the brief;
it returns one scenario object. This helper then normalises the map/profile,
validates it with the runner's own `prepare`, and adds it to the local library.

Providers (set in ai-config.json or with --provider):

    prompt      write a complete prompt file; hand it to Reasonix Studio or any
                chat AI; save its reply and check it with --check
    claude      run the installed `claude -p` in plan mode (no edit tools)
    reasonix    run the command in providers.reasonix.command
    command     run an arbitrary command; the prompt is on stdin, the reply on stdout

The local map is `fixtures/local/home.json` (run snapshot-map.py first). Room
names and profile names go to the provider; sensor/relay ids, credentials and
the full map do not.

For the Reasonix Studio workflow, the default `prompt` provider writes
`fixtures/local/drafts/<stamp>.prompt.md` and stops. Save the AI's JSON reply
somewhere and run:

    python3 ai-draft.py --check fixtures/local/drafts/reply.json --name "My scenario"
"""

import argparse
import difflib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

import scenario_library  # noqa: E402
from scenario_runner.errors import ScenarioError  # noqa: E402
from scenario_runner.validate import prepare  # noqa: E402

LOCAL = HERE / "fixtures" / "local"
HOME_MAP = LOCAL / "home.json"
DRAFTS = LOCAL / "drafts"
LAST = DRAFTS / "last.json"
SCENARIOS = scenario_library.SCENARIOS
CONFIG = HERE / "ai-config.json"
SCHEMA = HERE / "docs" / "scenario.schema.json"

DEFAULT_COMMANDS = {
    "claude": ["claude", "-p", "--output-format", "json", "--permission-mode", "plan"],
    "reasonix": [],
}
DEFAULT_TIMEOUT = 240


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}")


def config():
    data = read_json(CONFIG, {}) or {}
    data.setdefault("provider", "prompt")
    data.setdefault("providers", {})
    return data


def current_map_path(scenario_path):
    """The map a selected scenario actually uses, or None."""
    if not scenario_path:
        return None
    path = Path(scenario_path).resolve()
    data = read_json(path, {})
    if not isinstance(data, dict):
        return None
    home = data.get("home")
    if not isinstance(home, dict) or not isinstance(home.get("map"), str):
        return None
    map_path = (path.parent / home["map"]).resolve()
    return map_path if map_path.exists() else None


def map_summary(path=None):
    path = Path(path) if path else HOME_MAP
    if not path.exists():
        raise SystemExit(
            f"{path} is missing; put the live map at tools/rbr-studio/map.json "
            "and run python3 snapshot-map.py first")
    base = read_json(path)
    profiles = base.get("profiles", [])
    idx = base.get("profile", 0)
    if not isinstance(idx, int) or not (0 <= idx < len(profiles)):
        idx = 0
    active = profiles[idx].get("name") if profiles else ""
    profile = profiles[idx] if profiles else {}
    rooms = []
    for room in base.get("rooms", []):
        state = (profile.get("rooms") or {}).get(room.get("name"), {})
        rooms.append({
            "name": room.get("name"),
            "has_relay": bool(room.get("relays")),
            "has_trv": bool(room.get("trv") or room.get("trvs")),
            "mode": state.get("mode"),
            "target": state.get("target"),
        })
    return {
        "system": base.get("name", ""),
        "active_profile": active,
        "profiles": [item.get("name") for item in profiles],
        "calendar": base.get("calendar", "off"),
        "rooms": rooms,
    }


def target_catalogue():
    from scenario_runner import targets
    room_elements = ", ".join(targets.ROOM_ELEMENTS)
    summary = ", ".join(targets.SUMMARY)
    sheets = ", ".join(targets.SCHEETS)
    menu = ", ".join(targets.MENU)
    return "\n".join([
        f"room.<alias>.<element> — elements: {room_elements}",
        f"summary.<field> — {summary}",
        f"sheet.<field> — {sheets}",
        f"menu.<field> — {menu}",
        "schedule.save, schedule.cancel, schedule.add, schedule.profile, schedule.sheet",
        "schedule.period.<i>.start|stop|temp|enabled|delete",
        "profiles.save|cancel|add|sheet; profiles.row.<name>.label|rename|delete|body",
        "devices.save|cancel|add|sheet|room-pill; devices.room.<name>.name|edit|delete|up|down",
        "boot.warning; css:<selector> (last resort)",
        "",
        "Actions:",
        "  controller.room + set {temperature (tenths), relay, advance},",
        "  controller.room + state {mode, target, advance} (or controller.state for the system)",
        "  ui.tap {target}; ui.select {target, value}; ui.fill {target, value}; ui.scroll {target, dx, dy}",
        "  expect {target, contains|text|notContains|visible|hidden|value|count}",
        "  expectWire {request, match}; waitFor {target, text|...}; connection {action: drop|reconnect|error}",
        "  delay {seconds} (real time; Show only, normal runs skip it)",
    ])


def instructions(summary, editing):
    lines = [
        "You are writing one RBR Studio scenario.",
        "Return only a single JSON object. No prose, no markdown fence, no code.",
        "Use exactly schemaVersion 1 and the field names in the schema.",
        "The scenario is data, not a Playwright script. Do not invent target names.",
        "Use only rooms and profiles in the map summary.",
        "Prefer a rooms alias map (for example {\"main\": \"Bedroom 1\"}) and use",
        "room.main.<element> targets, because real room names may contain spaces.",
        "The runner will set home.map and home.profile, but keep them in the JSON:",
        "home.map = \"../home.json\", home.profile = " + json.dumps(summary["active_profile"]) + ".",
        "Use HH:MM step times in ascending order and stable step ids (s1, s2, ...).",
        "A delay step holds the current state for real seconds in a paced Show and is skipped in normal runs; use it only to make the Show readable.",
        "Every controller event that should be observed needs an explicit expect",
        "or expectWire after it. The controller is a map, not a brain: if a",
        "schedule boundary or advance expiry changes the UI, that must be an",
        "explicit controller step with its own expectation, not something the",
        "runner infers.",
        "Keep the scenario small: the shortest sequence that demonstrates the",
        "requested behaviour, with one clear assertion per visible effect.",
        "Put assumptions in the scenario's note field.",
    ]
    if editing:
        lines.append("This is an EDIT. Return the complete revised scenario; keep")
        lines.append("unchanged step ids where possible. Do not rename unless asked.")
    return "\n".join(lines)


def build_prompt(request, current, summary, current_brief=None):
    editing = current is not None
    parts = [
        instructions(summary, editing),
        "",
        "## Map summary",
        "```json",
        json.dumps(summary, indent=2, ensure_ascii=False),
        "```",
        "",
        "## Target catalogue",
        "```text",
        target_catalogue(),
        "```",
        "",
        "## Scenario schema",
        "```json",
        json.dumps(read_json(SCHEMA), indent=2, ensure_ascii=False),
        "```",
        "",
        "## Worked examples",
    ]
    for name in ("advance.json", "temperature.json", "delay.json"):
        path = HERE / "docs" / "examples" / name
        parts += ["### " + name, "```json", path.read_text(encoding="utf-8").strip(), "```", ""]
    if current is not None:
        parts += [
            "## Current scenario (edit this)",
            "```json",
            json.dumps(current, indent=2, ensure_ascii=False),
            "```",
            "",
        ]
    if current_brief:
        parts += [
            "## Current brief",
            "```text",
            current_brief.strip(),
            "```",
            "",
        ]
    parts += [
        "## Request",
        request.strip() or "(no request text)",
        "",
        "Return the scenario JSON now.",
    ]
    return "\n".join(parts)


def extract_json(text):
    text = str(text).strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    decoder = json.JSONDecoder()
    start = text.find("{")
    while start != -1:
        try:
            value, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            start = text.find("{", start + 1)
            continue
        if isinstance(value, dict) and isinstance(value.get("steps"), list):
            return value
        start = text.find("{", start + 1)
    raise SystemExit("the provider did not return a scenario object")


def run_provider(provider, prompt, args, cfg):
    if provider == "prompt":
        DRAFTS.mkdir(parents=True, exist_ok=True)
        stamp = date.today().isoformat()
        path = DRAFTS / f"{stamp}-brief.prompt.md"
        n = 2
        while path.exists():
            path = DRAFTS / f"{stamp}-brief-{n}.prompt.md"
            n += 1
        path.write_text(prompt, encoding="utf-8")
        return "prompt", path, None

    if provider == "claude":
        command = (cfg.get("providers", {}).get("claude", {}).get("command")
                   or DEFAULT_COMMANDS["claude"])
    elif provider == "reasonix":
        command = cfg.get("providers", {}).get("reasonix", {}).get("command")
        if not command:
            raise SystemExit(
                "the Reasonix command line is not configured; add its command to "
                "ai-config.json under providers.reasonix.command, or use "
                "--provider command --command \"...\"")
    elif provider == "command":
        command = args.command or cfg.get("providers", {}).get("command", {}).get("command")
        if isinstance(command, str):
            command = shlex.split(command)
        if not command:
            raise SystemExit("--provider command needs --command or providers.command.command")
    else:
        raise SystemExit(f"unknown provider {provider!r}; use prompt, claude, reasonix or command")

    if isinstance(command, str):
        command = shlex.split(command)
    if not command:
        raise SystemExit(f"no command configured for provider {provider!r}")
    executable = command[0]
    if os.path.sep not in executable and not shutil.which(executable):
        raise SystemExit(
            f"{executable!r} is not on PATH; install it or set the command in ai-config.json")
    timeout = int(cfg.get("providers", {}).get(provider, {}).get("timeout", DEFAULT_TIMEOUT))
    with tempfile.TemporaryDirectory(prefix="rbr-draft-") as work:
        try:
            result = subprocess.run(
                command,
                input=prompt,
                text=True,
                capture_output=True,
                cwd=work,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise SystemExit(f"the {provider} provider timed out after {timeout}s")
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise SystemExit(f"the {provider} provider failed ({result.returncode}): {detail[:1200]}")
    output = result.stdout.strip()
    if not output:
        raise SystemExit(f"the {provider} provider returned nothing")
    # Claude's --output-format json wraps the answer in a result envelope.
    try:
        envelope = json.loads(output)
        if isinstance(envelope, dict) and isinstance(envelope.get("result"), str):
            if envelope.get("is_error"):
                raise SystemExit(f"the {provider} provider reported an error: {envelope['result'][:1200]}")
            output = envelope["result"]
    except json.JSONDecodeError:
        pass
    return "generated", None, output


def slugify(name):
    return scenario_library.slug(name)


def load_brief(scenario_path):
    """The brief stored beside a library scenario, or its description."""
    if not scenario_path:
        return None
    path = Path(scenario_path).resolve()
    if SCENARIOS in path.parents:
        rel = path.relative_to(SCENARIOS).as_posix()
        entry = next((item for item in scenario_library.load_index()["scenarios"]
                      if item.get("path") == rel), None)
        if entry and entry.get("brief"):
            brief_path = SCENARIOS / entry["brief"]
            if brief_path.exists():
                return brief_path.read_text(encoding="utf-8")
    data = read_json(path, {})
    if isinstance(data, dict) and isinstance(data.get("description"), str):
        return data["description"]
    return None


def install(scenario, name, current=None, cfg=None, brief_text=None, group=None):
    """Write, validate and add a scenario to the library. Returns the result dict."""
    DRAFTS.mkdir(parents=True, exist_ok=True)
    SCENARIOS.mkdir(parents=True, exist_ok=True)
    if not isinstance(scenario, dict):
        raise SystemExit("the provider did not return a JSON object")
    scenario.setdefault("schemaVersion", 1)
    scenario["name"] = name or scenario.get("name") or "AI draft"
    scenario.setdefault("clock", {"start": "2026-11-05T08:00:00Z", "timeZone": "Europe/London"})
    scenario.setdefault("defaults", {"stepTimeoutMs": 5000, "screenshots": "failure"})
    home = scenario.setdefault("home", {})
    current_map = current_map_path(current)
    if current_map is not None:
        home["map"] = os.path.relpath(current_map, DRAFTS)
    else:
        home["map"] = "../home.json"
    if not home.get("profile"):
        home["profile"] = map_summary(current_map)["active_profile"]

    stem = slugify(scenario["name"])
    stem = scenario_library.unique_stem(DRAFTS, stem)
    draft = DRAFTS / f"{stem}.json"
    draft.write_text(json.dumps(scenario, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    try:
        prepare(draft, REPO)
    except ScenarioError as exc:
        result = {
            "status": "error",
            "message": str(exc),
            "draft": str(draft.relative_to(HERE)),
        }
        LAST.parent.mkdir(parents=True, exist_ok=True)
        LAST.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return result

    entry = scenario_library.add(draft, name=scenario["name"],
                                 group=group or scenario_library.UNSORTED,
                                 brief=brief_text if brief_text is not None else scenario.get("description"))
    target = SCENARIOS / entry["path"]
    try:
        prepare(target, REPO)
    except ScenarioError as exc:
        scenario_library.remove(target)
        result = {
            "status": "error",
            "message": str(exc),
            "draft": str(draft.relative_to(HERE)),
        }
        LAST.parent.mkdir(parents=True, exist_ok=True)
        LAST.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return result
    result = {
        "status": "ok",
        "path": str(target.relative_to(HERE)),
        "name": entry["name"],
        "group": entry.get("group"),
        "brief": entry.get("brief"),
        "steps": len(scenario.get("steps", [])),
    }
    if current is not None:
        old_path = Path(current)
        if old_path.exists():
            old = old_path.read_text(encoding="utf-8").splitlines()
            new = target.read_text(encoding="utf-8").splitlines()
            diff = list(difflib.unified_diff(old, new, fromfile=str(old_path), tofile=str(target), lineterm=""))
            if diff:
                diff_path = DRAFTS / f"{stem}.diff"
                diff_path.write_text("\n".join(diff) + "\n", encoding="utf-8")
                result["diff"] = str(diff_path.relative_to(HERE))
    LAST.parent.mkdir(parents=True, exist_ok=True)
    LAST.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def read_request(args):
    if args.request:
        return args.request
    if args.request_file:
        return Path(args.request_file).read_text(encoding="utf-8")
    lines = []
    for line in sys.stdin:
        if line.rstrip("\r\n") == "__END__":
            break
        lines.append(line)
    return "".join(lines).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", help="the brief (otherwise read stdin, ending with __END__)")
    parser.add_argument("--request-file")
    parser.add_argument("--scenario", help="current scenario for an edit")
    parser.add_argument("--name", help="name for the generated scenario")
    parser.add_argument("--provider", help="prompt, claude, reasonix or command")
    parser.add_argument("--command", help="command for --provider command")
    parser.add_argument("--check", help="validate and install an existing scenario JSON; no AI call")
    parser.add_argument("--group", default=scenario_library.UNSORTED,
                        help="library group (folder) for the scenario")
    parser.add_argument("--brief", help="brief text to store beside the scenario")
    parser.add_argument("--brief-file", help="file holding the brief to store")
    args = parser.parse_args()

    cfg = config()
    if args.check:
        source = Path(args.check)
        scenario = read_json(source)
        if scenario is None:
            raise SystemExit(f"{source}: no such scenario")
        brief = args.brief
        if args.brief_file:
            brief = Path(args.brief_file).read_text(encoding="utf-8")
        result = install(scenario, args.name or scenario.get("name") or source.stem,
                         current=args.scenario, cfg=cfg, brief_text=brief,
                         group=args.group)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("status") == "ok" else 1

    if not HOME_MAP.exists():
        raise SystemExit("fixtures/local/home.json is missing; run snapshot-map.py first")
    request = read_request(args)
    if not request.strip():
        raise SystemExit("no request text; use --request, --request-file, or stdin ending with __END__")
    current = read_json(Path(args.scenario)) if args.scenario else None
    if args.scenario and current is None:
        raise SystemExit(f"{args.scenario}: no such scenario")
    summary = map_summary(current_map_path(args.scenario))
    prior_brief = load_brief(args.scenario)
    prompt = build_prompt(request, current, summary, prior_brief)
    LAST.parent.mkdir(parents=True, exist_ok=True)
    LAST.write_text(json.dumps({"status": "running"}) + "\n", encoding="utf-8")
    provider = args.provider or cfg.get("provider") or "prompt"

    kind, prompt_path, output = run_provider(provider, prompt, args, cfg)
    if kind == "prompt":
        result = {
            "status": "prompt",
            "prompt": str(prompt_path.relative_to(HERE)),
            "message": "Give this prompt to Reasonix Studio or another AI, save the reply, then use --check.",
        }
        LAST.parent.mkdir(parents=True, exist_ok=True)
        LAST.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    scenario = extract_json(output)
    result = install(scenario, args.name or scenario.get("name"), current=args.scenario,
                     cfg=cfg, brief_text=request, group=args.group)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
