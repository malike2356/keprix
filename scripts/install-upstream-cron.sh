#!/usr/bin/env bash
# Install or print the daily Hermes upstream check crontab entry.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if command -v keprix >/dev/null 2>&1; then
  keprix upstream cron-install --install "$@"
else
  PYTHONPATH=src python3 -m keprix.keprix_cli.main upstream cron-install --install "$@"
fi
