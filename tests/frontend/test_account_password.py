"""Prompt 215 guards for password change and reset UI."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    "frontend/src/lib/account-api.ts",
    "frontend/src/components/auth/ChangePasswordForm.tsx",
    "frontend/src/components/auth/ForgotPasswordForm.tsx",
    "frontend/src/components/auth/ResetPasswordForm.tsx",
    "frontend/src/app/(workspace)/settings/account/password/page.tsx",
    "frontend/src/app/auth/forgot-password/page.tsx",
    "frontend/src/app/auth/reset-password/page.tsx",
    "src/keprix/auth/password_reset_store.py",
    "src/keprix/auth/password_routes.py",
]


def test_password_files_exist() -> None:
    for relative in REQUIRED_FILES:
        assert (ROOT / relative).is_file(), relative


def test_account_api_password_exports() -> None:
    source = (ROOT / "frontend/src/lib/account-api.ts").read_text(encoding="utf-8")
    for name in ("changeAccountPassword", "requestPasswordReset", "resetPasswordWithToken"):
        assert f"export async function {name}" in source


def test_login_form_forgot_password_link() -> None:
    login = (ROOT / "frontend/src/components/auth/LoginForm.tsx").read_text(encoding="utf-8")
    assert "/auth/forgot-password" in login


def test_account_layout_enables_password_tab() -> None:
    layout = (ROOT / "frontend/src/app/(workspace)/settings/account/layout.tsx").read_text(encoding="utf-8")
    assert 'href: "/settings/account/password"' in layout
    assert "disabled: true" not in layout or layout.index('href: "/settings/account/password"') < layout.index(
        "Two-factor"
    )
