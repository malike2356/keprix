#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
python3 - <<'PY'
from provisioning import plan_provision, provision

plan = plan_provision(deployment="local", tenant_id="owner-laud")
print("Plan nodes:", len(plan["nodes"]))
receipt = provision(deployment="local", tenant_id="owner-laud", activate=False)
print("Receipt status:", receipt["status"])
print("Secrets included:", receipt["secrets_included"])
print("Carina path changed:", receipt["carina_path_changed"])
print("Receipt id:", receipt["receipt_id"])
PY
