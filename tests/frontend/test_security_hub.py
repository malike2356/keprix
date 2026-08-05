"""Prompt 219 guards for security hub and sessions UI."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_session_routes_exist() -> None:
    assert (ROOT / "src/keprix/auth/session_routes.py").is_file()


def test_account_nav_component() -> None:
    source = (ROOT / "frontend/src/components/account/AccountNav.tsx").read_text(encoding="utf-8")
    assert "ACCOUNT_NAV_ITEMS" in source
    assert "/settings/account/sessions" in source


def test_security_overview_page() -> None:
    page = (ROOT / "frontend/src/app/(workspace)/settings/account/page.tsx").read_text(encoding="utf-8")
    assert "SecurityOverviewCard" in page
    assert "totp_enabled" in page


def test_sessions_page_exists() -> None:
    page = (ROOT / "frontend/src/app/(workspace)/settings/account/sessions/page.tsx").read_text(encoding="utf-8")
    assert "fetchActiveSessions" in page
    assert "Sign out all other devices" in page


def test_topbar_account_link() -> None:
    topbar = (ROOT / "frontend/src/components/shell/TopBar.tsx").read_text(encoding="utf-8")
    assert 'href="/settings/account"' in topbar
    assert "Account" in topbar


def test_settings_index_account_security_card() -> None:
    settings = (ROOT / "frontend/src/app/(workspace)/settings/page.tsx").read_text(encoding="utf-8")
    assert "Account and security" in settings
    assert 'href: "/settings/account"' in settings


def test_login_sends_client_label() -> None:
    ce_api = (ROOT / "frontend/src/lib/ce-api.ts").read_text(encoding="utf-8")
    assert "X-Client-Label" in ce_api
