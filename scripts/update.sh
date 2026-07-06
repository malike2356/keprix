#!/usr/bin/env bash
# Safe non-destructive Keprix update
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${KEPRIX_VENV:-$ROOT/.venv}"
export PYTHONPATH="${PYTHONPATH:-}:$ROOT/src"

if [ -x "$VENV/bin/keprix" ]; then
  exec "$VENV/bin/keprix" update "$@"
fi

exec python3 -c "from keprix.installer.cli import cmd_update; raise SystemExit(cmd_update(__import__('sys').argv[1:]))" "$@"
