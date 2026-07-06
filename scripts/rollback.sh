#!/usr/bin/env bash
# Roll back the immediately preceding update
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${KEPRIX_VENV:-$ROOT/.venv}"
export PYTHONPATH="${PYTHONPATH:-}:$ROOT/src"

if [ -x "$VENV/bin/keprix" ]; then
  exec "$VENV/bin/keprix" rollback "$@"
fi

exec python3 -c "from keprix.installer.cli import cmd_rollback; raise SystemExit(cmd_rollback(__import__('sys').argv[1:]))" "$@"
