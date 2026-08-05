"""Prompt 214 guards for account profile UI."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    "frontend/src/lib/account-api.ts",
    "frontend/src/app/(workspace)/settings/account/layout.tsx",
    "frontend/src/app/(workspace)/settings/account/profile/page.tsx",
]


def test_account_profile_files_exist() -> None:
    for relative in REQUIRED_FILES:
        assert (ROOT / relative).is_file(), relative


def test_account_api_client_exports() -> None:
    source = (ROOT / "frontend/src/lib/account-api.ts").read_text(encoding="utf-8")
    for name in ("fetchAccountProfile", "updateAccountProfile"):
        assert f"export async function {name}" in source


def test_profile_page_save_flow() -> None:
    page = (ROOT / "frontend/src/app/(workspace)/settings/account/profile/page.tsx").read_text(
        encoding="utf-8"
    )
    assert "updateAccountProfile" in page
    assert "refreshUser" in page
    assert "Save profile" in page


def test_settings_hub_links_account_profile() -> None:
    settings = (ROOT / "frontend/src/app/(workspace)/settings/page.tsx").read_text(encoding="utf-8")
    assert "Account and profile" in settings
    assert 'href: "/settings/account/profile"' in settings


def test_session_provider_exposes_refresh_user() -> None:
    source = (ROOT / "frontend/src/lib/ce-auth.tsx").read_text(encoding="utf-8")
    assert "refreshUser" in source
