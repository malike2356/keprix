#!/usr/bin/env bash
set -euo pipefail

secret_ref="${1:?secret ref required}"
if command -v cordon >/dev/null 2>&1; then
  cordon secret set "$secret_ref"
else
  keprix proxy rotate "$secret_ref" --verify
fi
