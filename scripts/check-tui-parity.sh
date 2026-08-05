#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

.venv/bin/python -m compileall -q src/keprix/tui
.venv/bin/python -m pytest tests/tui/test_hermes_parity_contract.py -q
.venv/bin/python -m pytest tests/tui -q

.venv/bin/python - <<'PY'
from pathlib import Path
from keprix.tui.parity_contract import contract_summary, required_contract_failures

required = [
    "src/keprix/tui/runtime_store.py",
    "src/keprix/tui/details_runtime.py",
    "src/keprix/tui/widgets/slash_input.py",
    "src/keprix/tui/widgets/model_picker.py",
    "src/keprix/tui/gateway_client.py",
    "tests/tui/test_runtime_data_parity.py",
    "tests/tui/test_interaction_parity.py",
    "tests/tui/test_fault_injection.py",
    "tests/tui/test_hermes_parity_contract.py",
]
missing = [path for path in required if not Path(path).exists()]
if missing:
    raise SystemExit("Missing TUI parity files: " + ", ".join(missing))
failures = required_contract_failures()
if failures:
    raise SystemExit("Contract failures: " + ", ".join(item.id for item in failures))

style_paths = [
    Path("src/keprix/tui/parity_contract.py"),
    Path("docs/architecture/tui-hermes-behavior-parity-contract.md"),
    Path("tests/tui/test_hermes_parity_contract.py"),
    Path("1st-plan/1st-prompt/pending-prompts/README.md"),
]
for path in style_paths:
    text = path.read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), 1):
        if "\u2013" in line or "\u2014" in line:
            raise SystemExit(f"{path}:{lineno}: forbidden dash")
        for ch in line:
            code = ord(ch)
            if 0x1F000 <= code <= 0x1FAFF or 0x2600 <= code <= 0x27BF:
                raise SystemExit(f"{path}:{lineno}: emoji/symbol U+{code:04X}")

print(contract_summary())
print("TUI tests: passed")
print("Compile: passed")
print("Style: passed")
PY
