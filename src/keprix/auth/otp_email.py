"""Email OTP delivery."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def send_otp_email(
    *,
    to_email: str,
    code: str,
    purpose: str,
    user_id: str,
    ttl_minutes: int,
    ip_address: str | None = None,
) -> bool:
    purpose_label = {
        "login": "sign in",
        "step_up": "verify your identity",
        "password_reset_fallback": "confirm your account",
    }.get(purpose, "verify your account")
    ip_hint = f"\nRequest IP: {ip_address}" if ip_address else ""
    subject = "Your Keprix sign-in code"
    body_text = (
        f"Your Keprix verification code to {purpose_label} is:\n\n"
        f"{code}\n\n"
        f"This code expires in {ttl_minutes} minutes.{ip_hint}\n"
        "If you did not request this, you can ignore this email."
    )
    body_html = (
        f"<p>Your Keprix verification code to {purpose_label} is:</p>"
        f"<p style='font-size:24px;font-weight:bold;letter-spacing:4px'>{code}</p>"
        f"<p>This code expires in {ttl_minutes} minutes.</p>"
        f"{f'<p>Request IP: {ip_address}</p>' if ip_address else ''}"
        "<p>If you did not request this, you can ignore this email.</p>"
    )
    try:
        from keprix.notify_external.smtp_sender import SMTPNotConfigured, send_email

        await send_email(
            "default",
            to_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            triggered_by=f"otp_{purpose}",
            triggered_by_id=user_id,
        )
        return True
    except SMTPNotConfigured:
        logger.info(
            "SMTP not configured; OTP for %s (%s): %s",
            to_email,
            purpose,
            code,
        )
        return False
    except Exception as exc:
        logger.warning("Failed to send OTP email to %s: %s", to_email, exc)
        return False
