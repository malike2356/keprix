"""Prompt 218 guards for workspace SSO login."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_sso_backend_files_exist() -> None:
    for relative in (
        "src/keprix/auth/sso/registry.py",
        "src/keprix/auth/sso/store.py",
        "src/keprix/auth/sso/routes.py",
        "src/keprix/auth/sso/providers/google.py",
        "src/keprix/auth/sso/providers/github.py",
        "src/keprix/auth/sso/providers/oidc_generic.py",
    ):
        assert (ROOT / relative).is_file(), relative


def test_account_api_sso_exports() -> None:
    source = (ROOT / "frontend/src/lib/account-api.ts").read_text(encoding="utf-8")
    for name in ("fetchSsoProviders", "fetchSsoLinks", "ssoStartUrl", "startSsoLink", "unlinkSsoProvider"):
        assert f"export async function {name}" in source or f"export function {name}" in source


def test_login_form_sso_buttons() -> None:
    login = (ROOT / "frontend/src/components/auth/LoginForm.tsx").read_text(encoding="utf-8")
    assert "fetchSsoProviders" in login
    assert "Continue with" in login
    assert "ssoStartUrl" in login


def test_sso_callback_page_exists() -> None:
    assert (ROOT / "frontend/src/app/auth/sso/callback/page.tsx").is_file()


def test_connected_accounts_page_exists() -> None:
    assert (ROOT / "frontend/src/app/(workspace)/settings/account/connected-accounts/page.tsx").is_file()


def test_login_form_does_not_embed_secrets() -> None:
    login = (ROOT / "frontend/src/components/auth/LoginForm.tsx").read_text(encoding="utf-8")
    assert "CLIENT_SECRET" not in login
    assert "KEPRIX_GOOGLE_CLIENT_SECRET" not in login
