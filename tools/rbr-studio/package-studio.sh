#!/usr/bin/env bash
# Build a portable RBR Studio package.
#
#   ./package-studio.sh                 # dist/rbr-studio-<YYMMDDHHMM>.tar.gz
#   ./package-studio.sh --dir /tmp/out  # put it somewhere else
#
# The package carries the Studio, the scenario runner, the journal tools and
# the public examples. It deliberately does not carry fixtures/local, a real
# map.json, ai-config.json or a .venv: those belong to the machine, and the
# launcher creates the first two on demand. Unpack it anywhere and run
# ./run-studio.sh; the first run asks for the folder the controller's daily
# journal bundles arrive in.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
OUT_DIR="$HERE/dist"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dir)
            [[ $# -ge 2 ]] || { echo "package-studio.sh: --dir needs a path" >&2; exit 2; }
            OUT_DIR="$2"
            shift 2
            ;;
        -h|--help)
            sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "package-studio.sh: unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

STAMP="$(date +%y%m%d%H%M)"
NAME="rbr-studio-$STAMP"
STAGE="$(mktemp -d)"
PACKAGE="$STAGE/$NAME"
mkdir -p "$PACKAGE" "$OUT_DIR"

FILES=(
    studio.allspeak
    ai-draft.py
    batch_runner.py
    configure-studio.py
    journal_bundle.py
    journal_import.py
    journal_inbox.py
    journal_ingest.py
    journal_mbox.py
    journal_to_scenario.py
    scenario_library.py
    snapshot-map.py
    requirements.txt
    requirements-studio.txt
    run-studio.sh
    README.md
    ai-config.example.json
    studio-config.example.json
)
for name in "${FILES[@]}"; do
    cp "$HERE/$name" "$PACKAGE/"
done
cp -R "$HERE/scenario_runner" "$PACKAGE/scenario_runner"
cp -R "$HERE/docs" "$PACKAGE/docs"
find "$PACKAGE" -name '__pycache__' -type d -prune -exec rm -rf {} +
chmod +x "$PACKAGE/run-studio.sh"

cat > "$PACKAGE/PACKAGE.txt" <<EOF
RBR Studio package
Built:  $(date -u +%Y-%m-%dT%H:%M:%SZ)
Source: $HERE

Run:
    ./run-studio.sh

The first run creates .venv, installs the requirements and Chromium, and asks
for the folder where the controller's daily journal bundles arrive. Configure
it again later with:
    ./run-studio.sh --inbox /path/to/inbox
    python3 configure-studio.py --show
EOF

ARCHIVE="$OUT_DIR/$NAME.tar.gz"
tar -C "$STAGE" -czf "$ARCHIVE" "$NAME"
rm -rf "$STAGE"
echo "$ARCHIVE"
