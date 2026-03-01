#!/usr/bin/env bash
set -euo pipefail

export EASYCODER_SRC="${EASYCODER_SRC:-$HOME/dev/easycoder/easycoder-py}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if pgrep -f "$SCRIPT_DIR/Controller/controller.py" >/dev/null; then
	echo "Controller is already running. Stop it before starting another instance."
	exit 1
fi

exec python3 "$SCRIPT_DIR/Controller/controller.py" "$@"
