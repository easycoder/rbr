"""Check the runner's frame stream for the Studio's view pane.

Two parts:

1. The local endpoint: 204 until the first frame, then the exact JPEG bytes
   with `image/jpeg`. This needs no browser.
2. A live `--view` run: the runner must emit a `view` event with the frame URL
   and keep serving a JPEG while it runs. This launches Chromium, so it needs
   the runner venv and Playwright's browser.

    cd tools/rbr-studio
    .venv/bin/python tests/view_check.py
"""

import json
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

STUDIO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDIO))

from scenario_runner.page import FrameStore, start_server  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"ok  {message}")


def endpoint_check():
    frames = FrameStore()
    server, port = start_server(STUDIO, frames)
    url = f"http://127.0.0.1:{port}/__studio/frame.jpg"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            check(response.status == 204, "the endpoint answers 204 before the first frame")
        payload = b"\xff\xd8\xff\xe0probe-jpeg"
        frames.set(payload)
        with urllib.request.urlopen(url, timeout=5) as response:
            body = response.read()
            check(response.status == 200, "the endpoint answers 200 once a frame exists")
            check(response.headers.get("Content-Type") == "image/jpeg",
                  "the frame is served as image/jpeg")
            check(response.headers.get("X-Frame-Seq") == "1",
                  "the frame carries its sequence number")
            check(body == payload, "the endpoint serves the frame bytes unchanged")
    finally:
        server.shutdown()
        server.server_close()


def read_events(stream, events):
    for line in stream:
        line = line.strip()
        if not line:
            continue
        try:
            events.put(json.loads(line))
        except json.JSONDecodeError:
            pass
    events.put(None)


def live_check():
    run_dir = Path(tempfile.mkdtemp(prefix="rbr-view-check-"))
    command = [
        sys.executable, "-m", "scenario_runner",
        "--scenario", "docs/examples/advance.json",
        "--jsonl", "--view", "--speed", "300",
        "--run-dir", str(run_dir),
    ]
    process = subprocess.Popen(command, cwd=STUDIO, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, stdin=subprocess.PIPE,
                               text=True)
    events = queue.Queue()
    threading.Thread(target=read_events, args=(process.stdout, events), daemon=True).start()
    url = None
    try:
        deadline = time.time() + 60
        while time.time() < deadline:
            try:
                event = events.get(timeout=deadline - time.time())
            except queue.Empty:
                break
            if event is None:
                break
            if event.get("event") == "view":
                url = event.get("url")
                break
        check(bool(url), "a --view run emits the frame URL")

        frame = None
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        frame = response.read()
                        break
            except Exception:
                pass
            time.sleep(0.2)
        check(frame is not None, "the live run serves a frame")
        check(frame[:2] == b"\xff\xd8", "the live frame is a JPEG")

        # Stop the way the Studio does: ask for a cancel, do not kill the
        # process under Playwright's Node driver.
        try:
            if process.poll() is None:
                process.stdin.write('{"command":"cancel"}\n')
                process.stdin.flush()
        except (BrokenPipeError, OSError):
            pass
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
            raise AssertionError("the runner did not stop after a cancel")
        stderr = process.stderr.read() if process.stderr is not None else ""
        check("EPIPE" not in stderr and "node:events" not in stderr,
              "stopping does not break Playwright's Node driver")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        shutil.rmtree(run_dir, ignore_errors=True)


def main():
    endpoint_check()
    live_check()
    print("view check passed")


if __name__ == "__main__":
    main()
