#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 - <<'PY'
from provisioning import plan_provision, provision
plan = plan_provision(deployment="local", workspace_id="ws-alpha", mode="local_community", edition="community")
print("plan_nodes", len(plan["nodes"]))
receipt = provision(deployment="local", workspace_id="ws-alpha", mode="local_community", edition="community", dry_run=True)
assert receipt["secrets_included"] is False
print("dry_run_ok", receipt["status"])
PY
echo "Local provision dry-run complete."
