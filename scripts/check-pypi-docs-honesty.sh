#!/usr/bin/env bash
# Fail if docs still prescribe bare PyPI pipx install of keprix while unpublished.
# Set KEPRIX_PYPI_PUBLISHED=1 after owner publish to skip (see docs/operations/pypi-publish-checklist.md).
# Prompt 421 / gate prep for 426.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "${KEPRIX_PYPI_PUBLISHED:-}" == "1" ]]; then
  echo "check-pypi-docs-honesty: KEPRIX_PYPI_PUBLISHED=1; skipping bare-PyPI scan."
  exit 0
fi

files=(
  docs/getting-started/install.md
  docs/features/tui.md
  README.md
)

hits=0
for f in "${files[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "check-pypi-docs-honesty: missing file: $f" >&2
    exit 1
  fi
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" ]] && continue
    # Strip leading markdown line number from grep -n (N:content)
    content="${line#*:}"
    # Honest: PEP 508 git URL form
    if [[ "$content" == *"@ git+"* ]] || [[ "$content" == *"@git+"* ]] || [[ "$content" == *"git+https://"* ]]; then
      continue
    fi
    # Ignore prose that only mentions the pattern while forbidding it
    lower=$(printf '%s' "$content" | tr '[:upper:]' '[:lower:]')
    if [[ "$lower" == *"not supported"* ]] || [[ "$lower" == *"do not"* ]] || [[ "$lower" == *"don't"* ]] || [[ "$lower" == *"will fail"* ]] || [[ "$lower" == *"will 404"* ]]; then
      continue
    fi
    echo "FAIL: bare PyPI pipx prescription in $f:" >&2
    echo "  $line" >&2
    hits=$((hits + 1))
  done < <(
    # Match the three quote styles from prompt 421
    grep -nE "pipx[[:space:]]+install[[:space:]]+('keprix\[(tui|tui-voice)\]'|\"keprix\[(tui|tui-voice)\]\"|keprix\[(tui|tui-voice)\])" "$f" 2>/dev/null || true
  )
done

if [[ "$hits" -gt 0 ]]; then
  echo >&2
  echo "check-pypi-docs-honesty: docs still claim bare pipx install of keprix from PyPI." >&2
  echo "PyPI package keprix is not published until owner upload (prompt 421)." >&2
  echo "Use git URL or checkout path; see docs/operations/pypi-publish-checklist.md" >&2
  echo "After publish: set KEPRIX_PYPI_PUBLISHED=1 and update install docs." >&2
  exit 1
fi

echo "check-pypi-docs-honesty: OK (no bare PyPI keprix pipx claims in scanned docs)."
exit 0
