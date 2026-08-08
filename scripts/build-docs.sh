#!/usr/bin/env bash
# Build MkDocs site into frontend/public/guide/
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
else
  PYTHON="python3"
fi

bash "$ROOT/scripts/generate-docs.sh"

"$PYTHON" -m pip install -q \
  mkdocs \
  mkdocs-material \
  mkdocs-minify-plugin \
  mkdocs-git-revision-date-localized-plugin

# Prefer non-strict for CI friendliness; set KEPRIX_MKDOCS_STRICT=1 to fail on warnings.
MKDOCS_ARGS=(-f "$ROOT/mkdocs.yml")
if [[ "${KEPRIX_MKDOCS_STRICT:-0}" == "1" ]]; then
  MKDOCS_ARGS+=(--strict)
fi
"$PYTHON" -m mkdocs build "${MKDOCS_ARGS[@]}"
echo "Built frontend/public/guide/"
