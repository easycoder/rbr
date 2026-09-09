#!/bin/bash
#
# Run the AllSpeak unit tests in this directory (tests/unit/*.as) using the
# new testing vocabulary (`check`, `test ... end test`, `allspeak --test`).
#
# Requires an AllSpeak runtime that implements the vocabulary — version
# 2608201436 or newer. Older runtimes treat `--test` as a script name and
# fail with a traceback; this runner detects that and says so.
#
# Usage:
#   ./tests/unit/run-unit-tests.sh
#
# The ALLSPEAK env var overrides the binary (e.g. to run a dev build:
#   ALLSPEAK="python3 -c '...'" — better: point PYTHONPATH at the runtime
#   repo and call allspeak through it).
#
# Exit codes: 0 all green, 1 tests failed, 2 wrong runtime / broken setup.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ALLSPEAK_BIN="${ALLSPEAK:-allspeak}"

if ! command -v "${ALLSPEAK_BIN%% *}" >/dev/null 2>&1 && [ -z "${ALLSPEAK:-}" ]; then
    echo "Error: $ALLSPEAK_BIN not found — install AllSpeak (pip install allspeak-ai)."
    exit 2
fi

OUT="$("$ALLSPEAK_BIN" --test "$SCRIPT_DIR" 2>&1)"
AS_STATUS=$?

if echo "$OUT" | grep -q "Test suite:"; then
    echo "$OUT"
else
    echo "This AllSpeak runtime does not support the testing vocabulary (--test)."
    echo "It printed no 'Test suite:' summary. Need version >= 2608201436."
    echo "Update with: pip install -U allspeak-ai  (add --break-system-packages if pip refuses)"
    echo "Installed runtime reports:"
    "$ALLSPEAK_BIN" --version 2>&1 | head -1
    exit 2
fi

# Python unit tests for the heating-data CSV writer (heatlog.py).
echo ""
echo "Running writer tests (tests/unit/heatlog_test.py)..."
PY_OUT="$(cd "$SCRIPT_DIR" && python3 -m unittest heatlog_test 2>&1)"
PY_STATUS=$?
echo "$PY_OUT"

if [ $AS_STATUS -eq 0 ] && [ $PY_STATUS -eq 0 ]; then
    echo ""
    echo "All unit tests passed."
    exit 0
fi
exit 1
