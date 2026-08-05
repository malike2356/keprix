#!/usr/bin/env bash
# Soft capability-mesh gate: wired+telegram nodes must list tools in core/keprix-telegram.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src"
PY=python3
command -v python3 >/dev/null || PY=python
"$PY" -m keprix.capability_mesh audit --write
"$PY" -m keprix.capability_mesh dod
