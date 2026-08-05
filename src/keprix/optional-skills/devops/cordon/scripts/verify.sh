#!/usr/bin/env bash
set -euo pipefail

if command -v cordon >/dev/null 2>&1; then
  cordon doctor --config "${CORDON_CONFIG:-$HOME/.keprix/cordon.toml}" || true
fi
keprix proxy verify
