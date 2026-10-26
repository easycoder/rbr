#!/bin/bash
#
# controller-compile-check.sh — the whole controller must compile before it can
# be released.
#
# The unit tests extract routines and exercise them on their own; none of them
# compiles controller.allspeak as a whole, and the AllSpeak compiler is
# single-pass with a global symbol table. On 2026-10-26 the controller was
# released with a second declaration of an existing list name; every controller
# that took the update stopped at "Compile error ... Duplicate symbol name" and
# never connected to the broker. This check would have refused it.
#
# The controller is compiled in a throwaway directory with a local credentials
# file and a fake MAC, so it never reaches the live system or the real broker.
# It is expected to stall/error at the MQTT step — that happens after the
# compiler has accepted the file. Only compiler errors fail this check.
#
# Usage: tests/unit/controller-compile-check.sh
# Exit:  0 compiles, 1 compile error, 2 runtime/setup problem.

set -u

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ALLSPEAK_BIN="${ALLSPEAK:-allspeak}"

if ! command -v "${ALLSPEAK_BIN%% *}" >/dev/null 2>&1; then
    echo "Error: $ALLSPEAK_BIN not found — install AllSpeak (pip install allspeak-ai)."
    exit 2
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cp "$ROOT/controller.allspeak" "$ROOT/deviceControl.allspeak" "$ROOT/map.json" "$TMP/"
printf '02:00:00:00:00:01' > "$TMP/.mac_override"
cat > "$TMP/credentials" <<'JSON'
{"broker":"127.0.0.1","username":"check","password":"check","mail_server":"","mail_login":"","mail_password":"","mail_from":""}
JSON

OUT="$(cd "$TMP" && timeout 20 "$ALLSPEAK_BIN" controller.allspeak --no-dashboard 2>&1)"
STATUS=$?

if echo "$OUT" | grep -q "Compile error"; then
    echo "The controller does not compile:"
    echo "$OUT" | grep -A 3 "Compile error"
    exit 1
fi
if ! echo "$OUT" | grep -q "Compiled Controller"; then
    echo "The controller produced no compilation line (exit $STATUS):"
    echo "$OUT" | tail -20
    exit 2
fi

echo "The controller compiles."
exit 0
