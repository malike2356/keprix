#!/usr/bin/env bash
# Render full changelog from git tags and history to stdout (review only).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

bash "$ROOT/scripts/changelog-git-cliff.sh" --config cliff.toml
