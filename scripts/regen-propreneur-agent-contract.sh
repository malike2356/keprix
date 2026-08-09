#!/usr/bin/env bash
# Regenerate all Propreneur agent capability artifacts in Keprix + Propreneur (+ Carina twin).
# Prompt 637: one command, deterministic, no secrets/live data in fixtures.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

python3 keprix/scripts/generate_propreneur_agent_contract.py

# Optional PHP builder remains for operators who still sync from OpenAPI directly;
# canonical path already wrote aiva_v1_tools.php/json. Keep OpenAPI <-> canonical parity gated.
if [[ "${PROPRENEUR_ALSO_RUN_OPENAPI_PHP_BUILDER:-0}" == "1" ]]; then
  php propr/scripts/build_aiva_v1_tools_from_openapi.php
  # Re-run generator check so PHP builder cannot silently diverge
  python3 keprix/scripts/generate_propreneur_agent_contract.py --check
fi

python3 keprix/scripts/generate_propreneur_agent_contract.py --check
echo "OK: Propreneur agent contract regenerated"
