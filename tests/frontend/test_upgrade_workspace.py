"""Prompt 274 guards for upgrade alerts UI."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    "frontend/src/lib/upgrade-api.ts",
    "frontend/src/components/upgrade/UpgradeBanner.tsx",
    "frontend/src/components/upgrade/UpgradeWizardDialog.tsx",
    "frontend/src/app/(workspace)/settings/upgrade/page.tsx",
]


def test_upgrade_workspace_files_exist() -> None:
    for relative in REQUIRED_FILES:
        assert (ROOT / relative).is_file(), relative


def test_upgrade_api_client_exports() -> None:
    source = (ROOT / "frontend/src/lib/upgrade-api.ts").read_text(encoding="utf-8")
    for name in (
        "fetchUpgradeStatus",
        "checkUpgradeNow",
        "fetchUpgradeWizard",
        "executeUpgrade",
        "dryRunUpgrade",
        "rollbackUpgrade",
        "dismissUpgradeAlert",
        "snoozeUpgradeAlert",
        "fetchUpgradePreferences",
        "saveUpgradePreferences",
        "severityColor",
    ):
        assert f"export async function {name}" in source or f"export function {name}" in source


def test_app_shell_includes_upgrade_banner() -> None:
    shell = (ROOT / "frontend/src/components/shell/AppShell.tsx").read_text(encoding="utf-8")
    assert "UpgradeBanner" in shell


def test_navigation_includes_upgrade_settings() -> None:
    nav = (ROOT / "frontend/src/lib/navigation.ts").read_text(encoding="utf-8")
    assert 'href: "/settings/upgrade"' in nav
    contract = (ROOT / "src/keprix/ui_contract/navigation.py").read_text(encoding="utf-8")
    assert '"/settings/upgrade"' in contract


def test_settings_hub_links_upgrade() -> None:
    settings = (ROOT / "frontend/src/app/(workspace)/settings/page.tsx").read_text(encoding="utf-8")
    assert "Keprix upgrades" in settings
    assert 'href: "/settings/upgrade"' in settings


def test_upgrade_settings_page_is_not_stub() -> None:
    page = (ROOT / "frontend/src/app/(workspace)/settings/upgrade/page.tsx").read_text(encoding="utf-8")
    assert "This page is being rebuilt" not in page
    assert "Notification preferences" in page
    assert "fetchUpgradeStatus" in page
    assert "saveUpgradePreferences" in page
    assert "UpgradeWizardDialog" in page
    assert "Check for updates" in page
