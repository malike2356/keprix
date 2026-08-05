#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

bash scripts/check-tui-parity.sh
.venv/bin/python -m pytest tests/tui/test_tui_surpass_contract.py -q
.venv/bin/python -m pytest tests/tui/test_granularity_contract.py -q
.venv/bin/python -m pytest tests/tui/test_renderer_benchmarks.py -q
.venv/bin/python -m pytest tests/tui/test_runtime_transport_contract.py -q
.venv/bin/python -m pytest tests/tui/test_performance_budgets.py -q
.venv/bin/python -m pytest tests/tui/test_fault_matrix.py -q
.venv/bin/python -m pytest tests/tui/test_terminal_matrix.py -q
.venv/bin/python -m pytest tests/tui/test_keyboard_model.py tests/tui/test_command_center_final_contract.py tests/tui/test_command_center_surpass_proof.py -q

.venv/bin/python - <<'PY'
from keprix.tui.surpass_contract import required_surpass_failures, surpass_summary

failures = required_surpass_failures()
if failures:
    raise SystemExit("TUI surpass contract failures: " + ", ".join(item.id for item in failures))

print(surpass_summary())
print("Renderer benchmarks: passed")
print("Runtime proximity contracts: passed")
print("Granularity contracts: passed")
print("Command Center contracts: passed")
print("TUI tests: passed")
PY
