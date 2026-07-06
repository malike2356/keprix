#!/usr/bin/env bash
# Run database migrations
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${KEPRIX_VENV:-$ROOT/.venv}"
export PYTHONPATH="${PYTHONPATH:-}:$ROOT/src"

if [ -x "$VENV/bin/alembic" ]; then
  exec "$VENV/bin/alembic" -c "$ROOT/alembic.ini" upgrade head
fi

if [ -x "$VENV/bin/python" ]; then
  exec "$VENV/bin/python" -m alembic -c "$ROOT/alembic.ini" upgrade head
fi

echo "alembic not found; install project deps first" >&2
exit 1
