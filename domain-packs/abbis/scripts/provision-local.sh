#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"
python3 - <<'PY'
from provisioning import provision
receipt = provision(deployment="local", tenant_id="tenant-alpha", stakeholder="S07", dry_run=False, activate=False)
print(receipt)
PY
