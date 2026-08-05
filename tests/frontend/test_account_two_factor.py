"""Prompt 216 guards for two-factor UI."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    "frontend/src/components/auth/TwoFactorSetupPanel.tsx",
    "frontend/src/components/auth/RecoveryCodesDialog.tsx",
    "frontend/src/app/(workspace)/settings/account/two-factor/page.tsx",
]


def test_two_factor_files_exist() -> None:
    for relative in REQUIRED_FILES:
        assert (ROOT / relative).is_file(), relative


def test_account_api_totp_exports() -> None:
    source = (ROOT / "frontend/src/lib/account-api.ts").read_text(encoding="utf-8")
    for name in ("setupTotp", "verifyTotp", "generateRecoveryCodes", "disableTotp"):
        assert f"export async function {name}" in source


def test_login_form_supports_totp_step() -> None:
    login = (ROOT / "frontend/src/components/auth/LoginForm.tsx").read_text(encoding="utf-8")
    assert "LoginChallengeError" in login
    assert "totp_required" in login
    assert "Use a recovery code" in login


def test_workspace_users_show_totp_badge() -> None:
    users = (ROOT / "frontend/src/components/users/WorkspaceUsersManager.tsx").read_text(encoding="utf-8")
    assert "totp_enabled" in users
    assert "Reset 2FA" in users
