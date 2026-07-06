#!/usr/bin/env bash
# Serve MkDocs locally for preview.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
  PIP="$ROOT/.venv/bin/pip"
else
  PYTHON="python3"
  PIP="pip"
fi

bash "$ROOT/scripts/generate-docs.sh"

"$PIP" install -q \
  mkdocs \
  mkdocs-material \
  mkdocs-minify-plugin \
  mkdocs-git-revision-date-localized-plugin

"$PYTHON" -m mkdocs serve -f "$ROOT/mkdocs.yml" "$@"
