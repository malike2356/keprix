"""Prompt 22 acceptance guards for the Keprix design system."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOKEN_DIR = ROOT / "ui" / "design-system" / "tokens"
REGISTRY = ROOT / "ui" / "design-system" / "components" / "registry.json"
FRONTEND_SRC = ROOT / "frontend" / "src"
NAV_PY = ROOT / "src" / "keprix" / "ui_contract" / "navigation.py"


def _rg(pattern: str, path: Path) -> list[str]:
    result = subprocess.run(
        ["rg", "-n", pattern, str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def test_design_system_token_files_exist():
    required = [
        "colors.json",
        "typography.json",
        "spacing.json",
        "radius.json",
        "shadows.json",
        "motion.json",
        "status.json",
        "icons.json",
    ]
    for name in required:
        assert (TOKEN_DIR / name).is_file(), name


def test_component_registry_paths_exist():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    for _name, relative in registry.items():
        assert (ROOT / relative).is_file(), relative


def test_navigation_groups_match_backend_contract():
    from keprix.ui_contract.navigation import NAV_GROUP_LABELS, NAV_GROUPS_ORDER

    nav_source = NAV_PY.read_text(encoding="utf-8")
    for group in NAV_GROUPS_ORDER:
        assert group in NAV_GROUP_LABELS
        assert f'"{group}"' in nav_source


def test_mobile_and_tui_specs_share_navigation_groups():
    mobile = json.loads((ROOT / "ui" / "mobile" / "app-shell" / "navigation.json").read_text(encoding="utf-8"))
    tui = json.loads((ROOT / "ui" / "tui" / "screens" / "navigation.json").read_text(encoding="utf-8"))
    assert mobile["navigation_groups"] == tui["navigation_groups"]


def test_shell_components_exist():
    required = [
        "components/shell/AppShell.tsx",
        "components/shell/Sidebar.tsx",
        "components/shell/TopBar.tsx",
        "components/shell/CommandPalette.tsx",
        "components/ui/ApprovalCard.tsx",
        "components/ui/StatusPill.tsx",
        "lib/ui-contract.ts",
        "lib/nav-icons.ts",
    ]
    for relative in required:
        assert (FRONTEND_SRC / relative).is_file(), relative


def test_no_forbidden_typography_in_design_system_docs():
    readme = (ROOT / "ui" / "design-system" / "README.md").read_text(encoding="utf-8")
    assert "\u2014" not in readme
    assert "\u2013" not in readme
