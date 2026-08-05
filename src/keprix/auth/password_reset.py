"""Password reset email delivery."""

from __future__ import annotations

import logging

from keprix.auth.user_invites import instance_frontend_url

logger = logging.getLogger(__name__)


def password_reset_url(token: str) -> str:
    return f"{instance_frontend_url()}/auth/reset-password?token={token}"


async def send_password_reset_email(*, to_email: str, reset_url: str, user_id: str) -> bool:
    subject = "Reset your Keprix password"
    body_text = (
        "You requested a password reset for your Keprix account.\n"
        f"Reset your password:\n{reset_url}\n\n"
        "This link expires in 1 hour. If you did not request this, you can ignore this email."
    )
    body_html = (
        "<p>You requested a password reset for your Keprix account.</p>"
        f'<p><a href="{reset_url}">Reset your password</a></p>'
        "<p>This link expires in 1 hour. If you did not request this, you can ignore this email.</p>"
    )
    try:
        from keprix.notify_external.smtp_sender import SMTPNotConfigured, send_email

        await send_email(
            "default",
            to_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            triggered_by="password_reset",
            triggered_by_id=user_id,
        )
        return True
    except SMTPNotConfigured:
        logger.info("SMTP not configured; password reset link for %s: %s", to_email, reset_url)
        return False
    except Exception as exc:
        logger.warning("Failed to send password reset email to %s: %s", to_email, exc)
        return False
