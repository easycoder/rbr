"""Read playback commands from the Studio over stdin.

The Studio writes one JSON object per line: `{"command":"step"}`,
`{"command":"continue"}` or `{"command":"cancel"}`. A background reader keeps
the engine free to run the page; the engine polls it between steps and blocks
on `next()` while a breakpoint holds the run.
"""

import json
import queue
import sys
import threading


class CommandReader:
    def __init__(self, stream=None):
        self.stream = stream if stream is not None else sys.stdin
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self._read, name="scenario-commands",
                                       daemon=True)

    def start(self):
        self.thread.start()
        return self

    def _read(self):
        try:
            for line in self.stream:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except (TypeError, ValueError):
                    continue
                if isinstance(payload, dict):
                    self.queue.put(payload)
        finally:
            # A closed pipe must not leave a paused run waiting for ever.
            self.queue.put({"command": "eof"})

    def poll(self):
        try:
            return self.queue.get_nowait()
        except queue.Empty:
            return None

    def next(self):
        return self.queue.get()
