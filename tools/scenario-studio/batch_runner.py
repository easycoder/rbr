#!/usr/bin/env python3
"""Run a list of scenarios in sequence and report one batch result.

    .venv/bin/python batch_runner.py \
        --scenario docs/examples/temperature.json \
        --scenario docs/examples/delay.json

Each scenario is a normal `scenario_runner` run, so it starts its own browser
and writes its own artefacts. The batch record is written under
`fixtures/local/batches/`; the directory is ignored.
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOCAL = HERE / "fixtures" / "local"
BATCHES = LOCAL / "batches"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", action="append", required=True,
                        help="a scenario to run; repeat for a batch")
    parser.add_argument("--repo", help="repository passed to scenario_runner")
    args = parser.parse_args()

    if not args.scenario:
        print("no scenarios in the batch", file=sys.stderr)
        return 2

    started = time.time()
    results = []
    for index, scenario in enumerate(args.scenario, start=1):
        print(f"== {index}/{len(args.scenario)} {scenario}", flush=True)
        command = [sys.executable, "-m", "scenario_runner", "--scenario", scenario]
        if args.repo:
            command += ["--repo", args.repo]
        step_started = time.time()
        proc = subprocess.run(command, cwd=HERE)
        duration = int((time.time() - step_started) * 1000)
        passed = proc.returncode == 0
        results.append({
            "scenario": scenario,
            "status": "passed" if passed else "failed",
            "durationMs": duration,
            "exitCode": proc.returncode,
        })
        print(f"{'PASSED' if passed else 'FAILED'} {scenario} ({duration} ms)", flush=True)

    BATCHES.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    record = BATCHES / f"{stamp}-batch.json"
    passed = sum(1 for item in results if item["status"] == "passed")
    record.write_text(json.dumps({
        "started": datetime.fromtimestamp(started).isoformat(timespec="seconds"),
        "durationMs": int((time.time() - started) * 1000),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"BATCH {passed}/{len(results)} passed", flush=True)
    print(f"batch record: {record}", flush=True)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
