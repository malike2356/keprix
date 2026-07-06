#!/usr/bin/env bash
# Full Keprix backup (database dump optional when pg_dump available)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${KEPRIX_VENV:-$ROOT/.venv}"
export PYTHONPATH="${PYTHONPATH:-}:$ROOT/src"

if [ -x "$VENV/bin/keprix" ]; then
  exec "$VENV/bin/keprix" backup "$@"
fi

exec python3 -c "from keprix.installer.cli import cmd_backup; raise SystemExit(cmd_backup(__import__('sys').argv[1:]))" "$@"
