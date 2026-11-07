#!/usr/bin/env bash
# Start RBR Studio from a copied package or from the development checkout.
#
#   ./run-studio.sh                 # first run prompts for the journal inbox
#   ./run-studio.sh --inbox DIR     # set the inbox and start
#   ./run-studio.sh --setup-only    # install and configure, do not open the window
#   ./run-studio.sh --no-install    # use the existing .venv; do not pip install
#
# The launcher creates a local .venv on first use, installs the Studio and
# runner requirements, installs Playwright's Chromium, and records the folder
# the mail filter writes daily bundles into. The Studio itself scans that
# folder at startup, so no SSH access to the controller is needed.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

INBOX=""
SETUP_ONLY=0
INSTALL=1
while [[ $# -gt 0 ]]; do
    case "$1" in
        --inbox)
            [[ $# -ge 2 ]] || { echo "run-studio.sh: --inbox needs a folder" >&2; exit 2; }
            INBOX="$2"
            shift 2
            ;;
        --setup-only) SETUP_ONLY=1; shift ;;
        --no-install) INSTALL=0; shift ;;
        -h|--help)
            sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "run-studio.sh: unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
    echo "run-studio.sh: $PY not found; install Python 3 first." >&2
    exit 1
fi

VENV_HOME=".venv/.studio-home"
venv_current() {
    [[ -x .venv/bin/python ]] || return 1
    if [[ -f "$VENV_HOME" ]]; then
        [[ "$(cat "$VENV_HOME")" == "$HERE" ]] && return 0
        return 1
    fi
    # A venv from before the marker existed is current when its console
    # scripts still name this directory. A moved venv cannot run its pip.
    head -n 1 .venv/bin/pip 2>/dev/null | grep -Fq "#!$HERE/.venv/bin/python"
}

if (( INSTALL )); then
    if ! venv_current; then
        if [[ -e .venv ]]; then
            echo "Replacing the .venv: it was created in another directory."
            rm -rf .venv
        fi
        echo "Creating .venv and installing the Studio requirements (first run)..."
        "$PY" -m venv .venv
        .venv/bin/python -m pip install --upgrade pip
        printf '%s\n' "$HERE" > "$VENV_HOME"
    fi
    if [[ ! -f .venv/.studio-ready ]]; then
        .venv/bin/python -m pip install -r requirements-studio.txt
        touch .venv/.studio-ready
    fi
    if [[ ! -f .venv/.chromium-ready ]]; then
        if .venv/bin/python -m playwright install chromium; then
            touch .venv/.chromium-ready
        else
            echo "run-studio.sh: Chromium install failed; Run/Demo will need it." >&2
        fi
    fi
fi

if ! venv_current; then
    echo "run-studio.sh: .venv is missing or stale; run without --no-install first." >&2
    exit 1
fi

if [[ -n "$INBOX" ]]; then
    .venv/bin/python configure-studio.py --inbox "$INBOX"
elif [[ -f studio-config.json ]]; then
    .venv/bin/python configure-studio.py --ensure --no-prompt
else
    .venv/bin/python configure-studio.py --ensure
fi

if (( SETUP_ONLY )); then
    echo "Setup complete. Start with ./run-studio.sh"
    exit 0
fi

if [[ -x .venv/bin/allspeak ]]; then
    exec .venv/bin/allspeak studio.allspeak
fi
if command -v allspeak >/dev/null 2>&1; then
    exec allspeak studio.allspeak
fi
echo "run-studio.sh: no allspeak runtime found. Install it with:" >&2
echo "    .venv/bin/python -m pip install allspeak-ai" >&2
exit 1
