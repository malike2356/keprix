"""Prompt 217 guards for email OTP UI."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_otp_backend_files_exist() -> None:
    for relative in (
        "src/keprix/auth/otp_store.py",
        "src/keprix/auth/otp_routes.py",
        "src/keprix/auth/step_up_store.py",
        "src/keprix/auth/otp_email.py",
    ):
        assert (ROOT / relative).is_file(), relative


def test_account_api_otp_exports() -> None:
    source = (ROOT / "frontend/src/lib/account-api.ts").read_text(encoding="utf-8")
    for name in ("sendEmailOtp", "verifyEmailOtpLogin", "verifyEmailOtpStepUp", "fetchAuthConfig"):
        assert f"export async function {name}" in source


def test_login_form_email_otp_flow() -> None:
    login = (ROOT / "frontend/src/components/auth/LoginForm.tsx").read_text(encoding="utf-8")
    assert "Email me a sign-in code" in login
    assert "verifyEmailOtpLogin" in login


def test_step_up_dialog_exists() -> None:
    assert (ROOT / "frontend/src/components/auth/StepUpOtpDialog.tsx").is_file()


def test_two_factor_panel_mentions_email_otp() -> None:
    panel = (ROOT / "frontend/src/components/auth/TwoFactorSetupPanel.tsx").read_text(encoding="utf-8")
    assert "StepUpOtpDialog" in panel
    assert "Email OTP step-up" in panel
