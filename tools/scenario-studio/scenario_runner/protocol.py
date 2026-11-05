"""JSON Lines event sink for the studio app.

stdout is either pure JSONL (`--jsonl`) or human-readable progress. Nothing
else may write to stdout in JSONL mode; diagnostics go to stderr.
"""

import json
import sys


class Events:
    def __init__(self, jsonl=False):
        self.jsonl = jsonl

    def emit(self, event, **fields):
        if not self.jsonl:
            return
        payload = {"v": 1, "event": event}
        payload.update(fields)
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    def log(self, message, step_id=None, level="info", source="runner"):
        self.emit("log", stepId=step_id, level=level, source=source, message=message)
