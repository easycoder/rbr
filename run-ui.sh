#!/usr/bin/env bash
set -euo pipefail

export EASYCODER_SRC="${EASYCODER_SRC:-$HOME/dev/easycoder/easycoder-py}"

exec python3 "$(dirname "$0")/UI/Python/ui.py" "$@"
