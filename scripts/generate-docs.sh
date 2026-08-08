#!/usr/bin/env bash
# Generate auto-maintained MkDocs pages before build.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
else
  echo "python3 not found"
  exit 1
fi

if ! "$PYTHON" -c "import fastapi" 2>/dev/null; then
  echo "Installing Keprix package for doc generation..."
  "$PYTHON" -m pip install -e "$ROOT" -q
fi

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
export KEPRIX_DATABASE_URL="${KEPRIX_DATABASE_URL:-sqlite+aiosqlite:///:memory:}"
export KEPRIX_JWT_SECRET="${KEPRIX_JWT_SECRET:-docs-build-placeholder-secret}"
export KEPRIX_SESSION_SECRET="${KEPRIX_SESSION_SECRET:-docs-build-placeholder-session}"
# Avoid PermissionError on /data/keprix when generating OpenAPI during docs build.
DOCS_DATA="${TMPDIR:-/tmp}/keprix-docs-build-data"
mkdir -p "$DOCS_DATA/home"
export KEPRIX_DATA_DIR="${KEPRIX_DATA_DIR:-$DOCS_DATA}"
export KEPRIX_HOME="${KEPRIX_HOME:-$DOCS_DATA/home}"

"$PYTHON" "$ROOT/scripts/generate_doc_pages.py" --docs-dir "$ROOT/docs"
