#!/usr/bin/env bash
# Dependency CVE audit for Keprix Python and frontend packages.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL_ON_HIGH="${KEPRIX_AUDIT_FAIL_ON_HIGH:-false}"
FOUND_HIGH=0

echo "=== Keprix dependency audit ==="

if command -v uv >/dev/null 2>&1; then
  echo "-- Python (uv pip audit) --"
  if ! uv pip audit; then
    echo "WARNING: Python dependency audit reported issues."
    FOUND_HIGH=1
  fi
elif command -v pip-audit >/dev/null 2>&1; then
  echo "-- Python (pip-audit) --"
  if ! pip-audit; then
    echo "WARNING: Python dependency audit reported issues."
    FOUND_HIGH=1
  fi
else
  echo "NOTE: uv or pip-audit not installed; skipping Python audit."
fi

if [ -d frontend ] && command -v pnpm >/dev/null 2>&1; then
  echo "-- Frontend (pnpm audit) --"
  if ! pnpm --dir frontend audit; then
    echo "WARNING: Frontend dependency audit reported issues."
    FOUND_HIGH=1
  fi
elif [ -d frontend ] && command -v npm >/dev/null 2>&1; then
  echo "-- Frontend (npm audit) --"
  if ! npm --dir frontend audit; then
    echo "WARNING: Frontend dependency audit reported issues."
    FOUND_HIGH=1
  fi
else
  echo "NOTE: frontend audit skipped (pnpm/npm or frontend/ missing)."
fi

if [ "$FAIL_ON_HIGH" = "true" ] && [ "$FOUND_HIGH" -ne 0 ]; then
  echo "ERROR: High or critical vulnerabilities found and KEPRIX_AUDIT_FAIL_ON_HIGH=true."
  exit 1
fi

echo "Done."
