#!/usr/bin/env bash
# Restore from a Keprix backup archive
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${KEPRIX_VENV:-$ROOT/.venv}"
export PYTHONPATH="${PYTHONPATH:-}:$ROOT/src"

ARCHIVE="${1:-}"
if [ -z "$ARCHIVE" ]; then
  echo "Usage: $0 <keprix-backup-*.tar.gz>" >&2
  exit 2
fi

if [ -x "$VENV/bin/keprix" ]; then
  exec "$VENV/bin/keprix" restore "$ARCHIVE"
fi

exec python3 -c "from keprix.installer.cli import cmd_restore; import sys; raise SystemExit(cmd_restore(sys.argv[1:]))" "$ARCHIVE"
