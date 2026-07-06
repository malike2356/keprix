#!/usr/bin/env bash
# Verify CHANGELOG.md is valid and docs/reference/changelog.md is in sync.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f CHANGELOG.md ]]; then
  echo "CHANGELOG.md not found"
  exit 1
fi

if ! grep -q '^## \[Unreleased\]' CHANGELOG.md; then
  echo "CHANGELOG.md must include a '## [Unreleased]' section"
  exit 1
fi

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
else
  PYTHON="python3"
fi

"$PYTHON" "$ROOT/scripts/generate_doc_pages.py" --docs-dir "$ROOT/docs" --only changelog >/dev/null

if ! git diff --quiet -- docs/reference/changelog.md; then
  echo "docs/reference/changelog.md is out of sync with CHANGELOG.md"
  echo "Run: python3 scripts/generate_doc_pages.py --docs-dir docs --only changelog"
  git diff -- docs/reference/changelog.md
  exit 1
fi

echo "OK: CHANGELOG.md and docs/reference/changelog.md are in sync"

if command -v git-cliff >/dev/null 2>&1 || [[ -x "$ROOT/.tools/git-cliff" ]]; then
  if PREVIEW="$(bash "$ROOT/scripts/changelog-preview.sh" 2>/dev/null || true)" && [[ -n "$PREVIEW" ]]; then
    echo "Note: git-cliff unreleased preview available (scripts/changelog-preview.sh)"
  fi
fi
