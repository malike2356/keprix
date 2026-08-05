#!/usr/bin/env bash
set -euo pipefail

echo "HTTPS_PROXY=${HTTPS_PROXY:-}"
if command -v cordon >/dev/null 2>&1; then
  cordon doctor --config "${CORDON_CONFIG:-$HOME/.keprix/cordon.toml}" || true
else
  echo "cordon not found on PATH"
fi
keprix proxy status || true
keprix proxy doctor || true
