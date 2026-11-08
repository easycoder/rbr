"""CLI entry point: python -m scenario_runner --scenario ... --repo ..."""

import argparse
import sys
import traceback
from pathlib import Path

from . import __version__
from .commands import CommandReader
from .engine import run_scenario
from .errors import ScenarioError
from .protocol import Events
from .validate import prepare


def main(argv=None):
    parser = argparse.ArgumentParser(prog="scenario_runner", description="Run an RBR UI scenario.")
    parser.add_argument("--scenario", required=True, help="path to the scenario JSON")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[3]),
                        help="RBR checkout to test (default: the repository containing this runner)")
    parser.add_argument("--headed", action="store_true", help="show the browser")
    parser.add_argument("--speed", type=float, default=0,
                        help="play the virtual clock at N scenario seconds per real second; 0 = as fast as possible")
    parser.add_argument("--collapse-polls", action="store_true",
                        help="summarise repeated refresh polls in the live event stream (full console stays in the run)")
    parser.add_argument("--step-pause-ms", type=int, default=0,
                        help="real pause after each passed step, for Show playback")
    parser.add_argument("--end-pause-ms", type=int, default=0,
                        help="real pause before the browser closes, for Show playback")
    parser.add_argument("--fold-to-marker", action="store_true",
                        help="fold controller steps before the marker into the base map and start at the marker")
    parser.add_argument("--pause-at-marker", action="store_true",
                        help="pause after the marker and wait for step/continue commands on stdin")
    parser.add_argument("--jsonl", action="store_true", help="emit PROTOCOL.md events on stdout")
    parser.add_argument("--validate-only", action="store_true", help="validate without launching a browser")
    parser.add_argument("--run-dir", default=None, help="write artefacts here instead of the user data directory")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    scenario = Path(args.scenario)
    events = Events(args.jsonl)

    try:
        if args.validate_only:
            prepared = prepare(scenario, repo)
            steps = len(prepared.scenario.get("steps", []))
            if args.jsonl:
                events.emit("run.finished", status="valid", passed=0, failed=0,
                            durationMs=0, message=f"{prepared.scenario.get('name')}: {steps} steps")
            else:
                print(f"ok  {prepared.scenario.get('name')}  ({steps} steps)")
            return 0

        if not (repo / "new-ui" / "index.html").exists():
            raise ScenarioError(f"{repo} does not look like an RBR checkout (no new-ui/index.html)")
        commands = CommandReader().start() if args.pause_at_marker else None
        return run_scenario(scenario, repo, headless=not args.headed,
                            jsonl=args.jsonl, events=events, run_dir=args.run_dir,
                            speed=args.speed, collapse_polls=args.collapse_polls,
                            step_pause_ms=args.step_pause_ms,
                            end_pause_ms=args.end_pause_ms,
                            fold_to_marker=args.fold_to_marker,
                            pause_at_marker=args.pause_at_marker,
                            commands=commands)
    except ScenarioError as exc:
        message = str(exc)
        for line in message.splitlines():
            print(f"error: {line}", file=sys.stderr)
        if args.jsonl:
            for line in message.splitlines():
                events.emit("validation.issue", severity="error", message=line)
            events.emit("run.finished", status="invalid", passed=0, failed=0, durationMs=0)
        return 2
    except KeyboardInterrupt:
        return 1
    except Exception:
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    sys.exit(main())
