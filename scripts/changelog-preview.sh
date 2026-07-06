#!/usr/bin/env bash
# Print unreleased changelog section to stdout (does not write CHANGELOG.md).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

bash "$ROOT/scripts/changelog-git-cliff.sh" --unreleased --config cliff.toml \
  | sed -n '/^## \[Unreleased\]/,$p'
