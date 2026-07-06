"""Guards for workspace users UI."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_workspace_users_files_exist() -> None:
    for relative in (
        "frontend/src/components/users/WorkspaceUsersManager.tsx",
        "frontend/src/app/(workspace)/settings/users/page.tsx",
        "frontend/src/app/(admin)/dashboard/users/page.tsx",
    ):
        assert (ROOT / relative).is_file(), relative


def test_navigation_includes_workspace_users() -> None:
    nav = (ROOT / "frontend/src/lib/navigation.ts").read_text(encoding="utf-8")
    assert 'href: "/settings/users"' in nav
    contract = (ROOT / "src/keprix/ui_contract/navigation.py").read_text(encoding="utf-8")
    assert '"/settings/users"' in contract


def test_settings_hub_links_users() -> None:
    settings = (ROOT / "frontend/src/app/(workspace)/settings/page.tsx").read_text(encoding="utf-8")
    assert "Workspace users" in settings
    assert 'href: "/settings/users"' in settings
    assert "Agent teams" in settings
    assert 'href: "/admin/teams"' in settings
