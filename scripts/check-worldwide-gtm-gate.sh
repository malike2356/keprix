#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="python3"
[[ -x "$ROOT/.venv/bin/python" ]] && PYTHON="$ROOT/.venv/bin/python"
VERSION="$(cd "$ROOT" && "$PYTHON" -c 'from pathlib import Path; import tomllib; print(tomllib.loads(Path("pyproject.toml").read_text())["project"]["version"])' 2>/dev/null || true)"
failures=0

pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; failures=$((failures + 1)); }
require_file() { [[ -s "$ROOT/$1" ]] && pass "$1" || fail "$1 missing or empty"; }

echo "Keprix worldwide GTM gate"
[[ -n "$VERSION" ]] && pass "version $VERSION" || fail "canonical version unavailable"
"$PYTHON" "$ROOT/scripts/check-release-version-sync.py" && pass "version synchronization" || fail "version synchronization"
"$PYTHON" -m pytest "$ROOT/tests/release" -q && pass "release contract tests" || fail "release contract tests"
bash "$ROOT/scripts/check-public-gtm-gate.sh" && pass "public repository gate" || fail "public repository gate"
require_file "SECURITY.md"
require_file "CONTRIBUTING.md"
require_file "THIRD_PARTY_NOTICES.md"
require_file "docs/operations/owner-release-configuration.md"
require_file ".github/workflows/publish-pypi.yml"
require_file ".github/workflows/release.yml"
require_file ".github/workflows/desktop-release.yml"

if [[ "${KEPRIX_GTM_REQUIRE_LIVE_ARTIFACTS:-0}" == "1" ]]; then
  manifest_url="${KEPRIX_RELEASE_MANIFEST_URL:-https://keprixai.com/releases/manifest.json}"
  tmp_manifest="$(mktemp)"
  trap 'rm -f "$tmp_manifest"' EXIT
  curl -fsSL "$manifest_url" -o "$tmp_manifest" || fail "live manifest unavailable"
  "$PYTHON" - "$tmp_manifest" <<'PY' || fail "live manifest invalid or empty"
import json, sys
from keprix.release_manifest import validate_manifest
data = json.load(open(sys.argv[1], encoding="utf-8"))
errors = validate_manifest(data)
if errors or not data.get("artifacts"):
    raise SystemExit("; ".join(errors) or "no published artifacts")
PY
  [[ "$failures" -gt 0 ]] || pass "live release manifest"
else
  echo "CONFIG  live artifact checks are reserved until owner publishing credentials are configured"
fi

if [[ "$failures" -gt 0 ]]; then
  printf 'GTM gate failed with %d issue(s).\n' "$failures"
  exit 1
fi
echo "GTM code readiness passed. Live market readiness still requires KEPRIX_GTM_REQUIRE_LIVE_ARTIFACTS=1."
