#!/usr/bin/env bash
# Validate community infrastructure files for Prompt 35.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0

require_file() {
  local path="$1"
  if [ ! -f "$path" ]; then
    echo "MISSING: $path"
    FAIL=1
  else
    echo "OK: $path"
  fi
}

echo "=== Required community files ==="
require_file "CONTRIBUTING.md"
require_file "SECURITY.md"
require_file "THIRD_PARTY_NOTICES.md"
require_file "CHANGELOG.md"
require_file "CODE_OF_CONDUCT.md"
require_file ".github/PULL_REQUEST_TEMPLATE.md"
require_file "docs/community/contributing.md"

echo "=== Issue templates ==="
for template in bug_report feature_request security_report skill_pack_submission question; do
  require_file ".github/ISSUE_TEMPLATE/${template}.yml"
done

echo "=== CHANGELOG format ==="
if ! grep -q '^## \[Unreleased\]' CHANGELOG.md; then
  echo "CHANGELOG.md must include a '## [Unreleased]' section"
  FAIL=1
else
  echo "OK: CHANGELOG has Unreleased section"
fi

echo "=== Issue template YAML ==="
if command -v python3 >/dev/null 2>&1; then
  python3 - <<'PY'
import pathlib
import sys

try:
    import yaml
except ImportError:
    print("NOTE: PyYAML not installed; skipping YAML parse checks")
    sys.exit(0)

root = pathlib.Path(".github/ISSUE_TEMPLATE")
failed = False
for path in sorted(root.glob("*.yml")):
    try:
        yaml.safe_load(path.read_text(encoding="utf-8"))
        print(f"OK: {path}")
    except Exception as exc:
        print(f"INVALID YAML: {path}: {exc}")
        failed = True
sys.exit(1 if failed else 0)
PY
  FAIL=$((FAIL + $?))
fi

echo "=== PR template checklist ==="
if ! grep -qi "engineering pillars" .github/PULL_REQUEST_TEMPLATE.md; then
  echo "PULL_REQUEST_TEMPLATE.md must mention engineering pillars"
  FAIL=1
else
  echo "OK: PR template includes engineering pillars checklist"
fi

echo "=== No emojis in community files ==="
python3 - <<'PY'
import pathlib
import re
import sys

files = [
    "CONTRIBUTING.md",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
]
files.extend(str(p) for p in pathlib.Path(".github/ISSUE_TEMPLATE").glob("*.yml"))

emoji_re = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\u2600-\u27BF"
    "\uFE0F"
    "\u200D"
    "]"
)
failed = False
for rel in files:
    path = pathlib.Path(rel)
    if not path.exists():
        continue
    text = path.read_text(encoding="utf-8")
    for idx, line in enumerate(text.splitlines(), start=1):
        if emoji_re.search(line):
            print(f"EMOJI: {rel}:{idx}: {line.strip()}")
            failed = True
if failed:
    sys.exit(1)
print("OK: no emojis in community files")
PY
FAIL=$((FAIL + $?))

if [ "$FAIL" -ne 0 ]; then
  echo "Community file validation failed"
  exit 1
fi

echo "Community file validation passed"
