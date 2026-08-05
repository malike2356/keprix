#!/usr/bin/env bash
set -euo pipefail

mkdir -p "$HOME/.keprix"
template_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/templates"
cp "$template_dir/cordon.toml.template" "$HOME/.keprix/cordon.toml"
if command -v cordon >/dev/null 2>&1; then
  cordon setup hermes || true
  echo "Install service with: cordon service install --config $HOME/.keprix/cordon.toml"
else
  echo "cordon not found. Install with: npm install -g @codezero-io/cordon"
fi
echo "Wrote $HOME/.keprix/cordon.toml"
