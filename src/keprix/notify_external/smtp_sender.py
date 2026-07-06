"""SMTP dispatch for external notifications."""

from __future__ import annotations

import asyncio
import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from keprix.email.helpers import smtp_security_mode
from keprix.notify_external.store import get_notify_external_store, recipient_domain
from keprix.notify_external.templates import render_template
from keprix.security.audit import audit_log

logger = logging.getLogger(__name__)


class SMTPNotConfigured(Exception):
    pass


def _system_smtp_config() -> dict[str, Any] | None:
    host = os.environ.get("KEPRIX_SMTP_HOST", "").strip()
    if not host:
        return None
    return {
        "smtp_host": host,
        "smtp_port": int(os.environ.get("KEPRIX_SMTP_PORT", "587")),
        "smtp_use_tls": os.environ.get("KEPRIX_SMTP_USE_TLS", "true").lower() == "true",
        "smtp_username": os.environ.get("KEPRIX_SMTP_USERNAME", ""),
        "smtp_password": os.environ.get("KEPRIX_SMTP_PASSWORD", ""),
        "smtp_from_email": os.environ.get("KEPRIX_SMTP_FROM_EMAIL", os.environ.get("KEPRIX_SMTP_USERNAME", "")),
        "smtp_from_name": os.environ.get("KEPRIX_SMTP_FROM_NAME", "Keprix"),
    }


def _resolve_smtp_password_sync(smtp_config: dict[str, Any]) -> str:
    if smtp_config.get("smtp_password"):
        return str(smtp_config["smtp_password"])
    return ""


async def _resolve_smtp_password(smtp_config: dict[str, Any]) -> str:
    direct = _resolve_smtp_password_sync(smtp_config)
    if direct:
        return direct
    vault_id = smtp_config.get("smtp_password_vault_id")
    if not vault_id:
        return ""
    from keprix.security.vault_service import get_vault_service

    item = await get_vault_service().get_item(
        str(vault_id),
        user_id=smtp_config.get("vault_user_id") or "system",
        decrypt=True,
    )
    if item is None:
        return ""
    return str(getattr(item, "_value", "") or "")


def _send_smtp_sync(
    smtp_config: dict[str, Any],
    *,
    to_email: str,
    subject: str,
    body_text: str,
    body_html: str | None,
    workspace_id: str,
) -> None:
    password = str(smtp_config.get("smtp_password") or "")
    if not smtp_config.get("smtp_host") or not password:
        raise SMTPNotConfigured("SMTP is not configured")

    from_email = smtp_config.get("smtp_from_email") or smtp_config.get("smtp_username")
    from_name = smtp_config.get("smtp_from_name") or "Keprix"
    from_header = f"{from_name} <{from_email}>" if from_name else str(from_email)

    message = MIMEMultipart("alternative")
    message["From"] = from_header
    message["To"] = to_email
    message["Subject"] = subject
    message["X-Keprix-Workspace"] = workspace_id
    message.attach(MIMEText(body_text, "plain", "utf-8"))
    if body_html:
        message.attach(MIMEText(body_html, "html", "utf-8"))

    port = int(smtp_config.get("smtp_port") or 587)
    security = smtp_security_mode(port, bool(smtp_config.get("smtp_use_tls", True)))
    host = str(smtp_config["smtp_host"])
    raw = message.as_string()
    username = str(smtp_config.get("smtp_username") or "")
    if security == "ssl":
        with smtplib.SMTP_SSL(host, port, timeout=30) as smtp:
            if username:
                smtp.login(username, password)
            smtp.sendmail(str(from_email), [to_email], raw)
        return
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        if security == "starttls":
            smtp.starttls()
        if username:
            smtp.login(username, password)
        smtp.sendmail(str(from_email), [to_email], raw)


async def send_email(
    workspace_id: str,
    to_email: str,
    *,
    to_name: str | None = None,
    subject: str | None = None,
    body_text: str | None = None,
    body_html: str | None = None,
    template_name: str | None = None,
    template_vars: dict[str, Any] | None = None,
    triggered_by: str = "api",
    triggered_by_id: str | None = None,
) -> str:
    del to_name
    store = get_notify_external_store()
    if not store.check_rate_limit(workspace_id):
        raise RateLimitExceeded("External notification rate limit exceeded")

    if template_name:
        rendered = render_template(template_name, template_vars or {})
        subject = subject or rendered["subject"]
        body_text = body_text or rendered["text"]
        body_html = body_html or rendered.get("html")

    if not subject or not body_text:
        raise ValueError("subject and body_text are required")

    row = store.create_notification(
        workspace_id,
        {
            "channel": "email",
            "recipient_address": to_email,
            "subject": subject,
            "body_text": body_text,
            "body_html": body_html,
            "template_name": template_name,
            "template_vars": template_vars or {},
            "triggered_by": triggered_by,
            "triggered_by_id": triggered_by_id,
        },
    )
    notification_id = str(row["id"])
    config = store.get_config(workspace_id)
    smtp_config = dict(config)
    if not config.get("smtp_host"):
        system = _system_smtp_config()
        if system:
            smtp_config = system
    try:
        password = await _resolve_smtp_password(smtp_config)
        smtp_config = {**smtp_config, "smtp_password": password}
        await asyncio.to_thread(
            _send_smtp_sync,
            smtp_config,
            to_email=to_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            workspace_id=workspace_id,
        )
        store.update_notification(
            notification_id,
            {
                "status": "sent",
                "attempts": 1,
                "last_attempted_at": datetime.now(timezone.utc).isoformat(),
                "delivered_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        await audit_log(
            "notify_external_sent",
            event_data={
                "notification_id": notification_id,
                "channel": "email",
                "recipient_domain": recipient_domain(to_email),
                "template_name": template_name,
                "triggered_by": triggered_by,
            },
        )
    except Exception as exc:
        store.update_notification(
            notification_id,
            {
                "status": "failed",
                "attempts": 1,
                "last_attempted_at": datetime.now(timezone.utc).isoformat(),
                "failure_reason": str(exc)[:500],
            },
        )
        logger.warning(
            "notify_external email failed workspace=%s domain=%s error=%s",
            workspace_id,
            recipient_domain(to_email),
            exc,
        )
        raise
    return notification_id


class RateLimitExceeded(Exception):
    pass
