#!/usr/bin/env bash
# Resolve git-cliff binary (PATH, or repo .tools/git-cliff).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if command -v git-cliff >/dev/null 2>&1; then
  exec git-cliff "$@"
fi

LOCAL_BIN="$ROOT/.tools/git-cliff"
if [[ -x "$LOCAL_BIN" ]]; then
  exec "$LOCAL_BIN" "$@"
fi

echo "git-cliff not found. Install from https://git-cliff.org or run:" >&2
echo "  curl -fsSL https://github.com/orhun/git-cliff/releases/download/v2.7.0/git-cliff-2.7.0-x86_64-unknown-linux-gnu.tar.gz | tar xz -C .tools --strip-components=1 git-cliff-2.7.0/git-cliff" >&2
exit 1
