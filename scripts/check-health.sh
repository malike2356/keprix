#!/usr/bin/env bash
# Post-install health checks for Keprix
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${KEPRIX_VENV:-$ROOT/.venv}"
PYTHON="$VENV/bin/python"

if [ -x "$PYTHON" ]; then
  exec "$PYTHON" -m keprix.installer.health
fi

if command -v python3 >/dev/null 2>&1; then
  PYTHONPATH="${PYTHONPATH:-}:$ROOT/src" exec python3 -m keprix.installer.health
fi

echo "FAIL python not available" >&2
exit 1
