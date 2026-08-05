#!/usr/bin/env bash
# check-telegram-gateway-parity.sh: Local Hermes surface + Keprix-own gate.
#
# Compares local Hermes (pipx) COMMAND_REGISTRY to Keprix gateway registry,
# verifies product commands are registered, and checks ~/.keprix/skills sync.
# Does not talk to Contabo. Does not require Telegram to be running.
#
# Usage:
#   bash scripts/check-telegram-gateway-parity.sh
#
# Exit 0 = parity checks pass. Exit 1 = one or more failed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

export PYTHONPATH="${PROJECT_ROOT}/src:${PYTHONPATH:-}"

if [ -f .venv/bin/activate ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

PASSED=0
FAILED=0

pass() {
    echo -e "  ${GREEN}PASS${NC} $1"
    PASSED=$((PASSED + 1))
}

fail() {
    echo -e "  ${RED}FAIL${NC} $1"
    FAILED=$((FAILED + 1))
}

echo ""
echo "=========================================="
echo "  Telegram gateway parity (local Hermes)"
echo "=========================================="
echo ""

python3 - <<'PY'
import re
import sys
from pathlib import Path

hermes_commands = Path.home() / ".local/pipx/venvs/hermes-agent/lib"
candidates = list(hermes_commands.glob("python*/site-packages/hermes_cli/commands.py"))
if not candidates:
    print("MISSING_HERMES_COMMANDS")
    sys.exit(2)

text = candidates[0].read_text(encoding="utf-8", errors="ignore")
hermes = set(re.findall(r'CommandDef\(\s*"([^"]+)"', text))

sys.path.insert(0, str(Path("src").resolve()))
from keprix_cli.commands import (  # noqa: E402
    COMMAND_REGISTRY,
    PRODUCT_GATEWAY_COMMANDS,
    gateway_help_lines,
    telegram_menu_commands,
)

keprix = {c.name for c in COMMAND_REGISTRY}
hermes_only = sorted(hermes - keprix)
product = sorted(PRODUCT_GATEWAY_COMMANDS)
help_lines = gateway_help_lines()
menu, hidden = telegram_menu_commands(max_commands=100)
menu_names = {n for n, _ in menu}

skills_home = Path.home() / ".keprix" / "skills"
skill_count = len(list(skills_home.rglob("SKILL.md"))) if skills_home.exists() else 0

print(f"HERMES_COUNT={len(hermes)}")
print(f"KEPRIX_COUNT={len(keprix)}")
print(f"HERMES_ONLY={','.join(hermes_only) if hermes_only else ''}")
print(f"PRODUCT_COUNT={len(product)}")
print(f"PRODUCT={','.join(product)}")
print(f"HELP_LINES={len(help_lines)}")
print(f"MENU_COUNT={len(menu)}")
print(f"MENU_HIDDEN={hidden}")
print(f"SKILL_COUNT={skill_count}")
print(f"BILLING_IN_REGISTRY={'billing' in keprix}")
print(f"PLAYBOOK_IN_MENU={'playbook' in menu_names}")
print(f"BILLING_IN_MENU={'billing' in menu_names}")
print(f"DISPATCH_MODULE_OK={Path('src/keprix/gateway/slash/product.py').is_file()}")
PY

eval "$(python3 - <<'PY'
import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path("src").resolve()))
from keprix_cli.commands import COMMAND_REGISTRY, PRODUCT_GATEWAY_COMMANDS, telegram_menu_commands

hermes_commands = Path.home() / ".local/pipx/venvs/hermes-agent/lib"
candidates = list(hermes_commands.glob("python*/site-packages/hermes_cli/commands.py"))
text = candidates[0].read_text(encoding="utf-8", errors="ignore")
hermes = set(re.findall(r'CommandDef\(\s*"([^"]+)"', text))
keprix = {c.name for c in COMMAND_REGISTRY}
hermes_only = sorted(hermes - keprix)
menu, _ = telegram_menu_commands(max_commands=100)
menu_names = {n for n, _ in menu}
skills_home = Path.home() / ".keprix" / "skills"
skill_count = len(list(skills_home.rglob("SKILL.md"))) if skills_home.exists() else 0

print(f'HERMES_ONLY="{(",".join(hermes_only))}"')
print(f'PRODUCT_COUNT={len(PRODUCT_GATEWAY_COMMANDS)}')
print(f'SKILL_COUNT={skill_count}')
print(f'BILLING_IN_REGISTRY={1 if "billing" in keprix else 0}')
print(f'PLAYBOOK_IN_MENU={1 if "playbook" in menu_names else 0}')
print(f'BILLING_IN_MENU={1 if "billing" in menu_names else 0}')
print(f'DISPATCH_OK={1 if Path("src/keprix/gateway/slash/product.py").is_file() else 0}')
PY
)"

if [ -z "${HERMES_ONLY:-}" ]; then
    pass "Hermes command names covered by Keprix gateway registry"
else
    fail "Hermes-only commands still missing: ${HERMES_ONLY}"
fi

if [ "${BILLING_IN_REGISTRY:-0}" = "1" ]; then
    pass "/billing registered in COMMAND_REGISTRY"
else
    fail "/billing missing from COMMAND_REGISTRY"
fi

if [ "${PRODUCT_COUNT:-0}" -ge 10 ]; then
    pass "Product gateway commands registered (${PRODUCT_COUNT})"
else
    fail "Expected >=10 product gateway commands, got ${PRODUCT_COUNT:-0}"
fi

if [ "${PLAYBOOK_IN_MENU:-0}" = "1" ] && [ "${BILLING_IN_MENU:-0}" = "1" ]; then
    pass "Telegram menu includes /playbook and /billing"
else
    fail "Telegram menu missing playbook and/or billing"
fi

if [ "${SKILL_COUNT:-0}" -ge 100 ]; then
    pass "~/.keprix/skills has ${SKILL_COUNT} SKILL.md files"
else
    fail "Expected >=100 synced skills in ~/.keprix/skills, got ${SKILL_COUNT:-0}"
fi

if [ "${DISPATCH_OK:-0}" = "1" ]; then
    pass "Product slash dispatch module present"
else
    fail "Missing gateway/slash/product.py"
fi

# Smoke: product dispatch for /playbook
if python3 - <<'PY'
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))
from keprix.gateway.slash.product import dispatch_product_slash

async def main():
    msg = await dispatch_product_slash(
        text="/playbook",
        user_id="parity-test",
        chat_id="parity-test",
        channel="telegram",
    )
    assert msg is not None and len(msg) > 0, msg
    none = await dispatch_product_slash(
        text="/help",
        user_id="parity-test",
        chat_id="parity-test",
        channel="telegram",
    )
    assert none is None, none

asyncio.run(main())
print("ok")
PY
then
    pass "Product slash dispatch smoke (/playbook yes, /help no)"
else
    fail "Product slash dispatch smoke failed"
fi

echo ""
echo "Result: ${PASSED} passed, ${FAILED} failed"
if [ "$FAILED" -gt 0 ]; then
    exit 1
fi
exit 0
