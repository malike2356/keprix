"""Retry failed or pending external notifications."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from keprix.notify_external.smtp_sender import RateLimitExceeded, SMTPNotConfigured, send_email
from keprix.notify_external.store import get_notify_external_store
from keprix.notify_external.webhook_sender import WebhookTargetRejected, send_webhook

logger = logging.getLogger(__name__)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


async def _alert_max_retries(workspace_id: str, row: dict[str, Any]) -> None:
    try:
        from keprix.backend.notifications.inbox import get_inbox_service

        await get_inbox_service().send_notification(
            workspace_id,
            "notify_external_exhausted",
            severity="warning",
            title="External notification delivery failed",
            message=(
                f"Notification {row.get('id')} exhausted retries "
                f"({row.get('channel')} to {row.get('recipient_address')})."
            ),
            href="/settings/notify-external",
            sensitive=False,
            metadata={
                "notification_id": row.get("id"),
                "channel": row.get("channel"),
                "failure_reason": row.get("failure_reason"),
            },
            source="notify_external",
        )
    except Exception as exc:
        logger.warning("notify_external inbox alert failed: %s", exc)


async def retry_notification(notification_id: str) -> dict[str, Any]:
    store = get_notify_external_store()
    row = store.get_notification(notification_id)
    if row is None:
        raise ValueError("Notification not found")
    if row.get("status") == "sent":
        return {"notification_id": notification_id, "status": "sent", "retried": False}

    workspace_id = str(row.get("workspace_id") or "default")
    config = store.get_config(workspace_id)
    max_retries = int(config.get("max_retries") or 3)
    attempts = int(row.get("attempts") or 0)
    if attempts >= max_retries:
        await _alert_max_retries(workspace_id, row)
        raise ValueError("max retries exceeded")

    channel = str(row.get("channel") or "email")
    try:
        if channel == "email":
            await send_email(
                workspace_id,
                str(row.get("recipient_address") or ""),
                subject=row.get("subject"),
                body_text=row.get("body_text"),
                body_html=row.get("body_html"),
                template_name=row.get("template_name"),
                template_vars=row.get("template_vars") or {},
                triggered_by=str(row.get("triggered_by") or "retry"),
                triggered_by_id=str(row.get("triggered_by_id") or notification_id),
                existing_notification_id=notification_id,
            )
        elif channel == "webhook":
            await send_webhook(
                workspace_id,
                str(row.get("recipient_address") or ""),
                row.get("template_vars") or row.get("webhook_payload") or {},
                triggered_by=str(row.get("triggered_by") or "retry"),
                triggered_by_id=str(row.get("triggered_by_id") or notification_id),
                existing_notification_id=notification_id,
            )
        else:
            raise ValueError(f"unsupported channel: {channel}")
    except (SMTPNotConfigured, RateLimitExceeded, WebhookTargetRejected, ValueError):
        updated = store.get_notification(notification_id) or row
        if int(updated.get("attempts") or 0) >= max_retries:
            await _alert_max_retries(workspace_id, updated)
        raise

    updated = store.get_notification(notification_id) or row
    if updated.get("status") != "sent" and int(updated.get("attempts") or 0) >= max_retries:
        await _alert_max_retries(workspace_id, updated)
    return {
        "notification_id": notification_id,
        "status": updated.get("status"),
        "attempts": updated.get("attempts"),
        "retried": True,
    }


async def retry_failed_external_notifications(
    *,
    workspace_id: str | None = None,
) -> dict[str, Any]:
    """Retry failed/pending notifications that are due (cron every ~5 minutes)."""
    store = get_notify_external_store()
    rows = store._read_notifications()
    now = datetime.now(timezone.utc)
    retried = 0
    skipped = 0
    errors = 0
    for row in rows:
        if workspace_id and row.get("workspace_id") != workspace_id:
            continue
        if row.get("status") not in {"pending", "failed"}:
            continue
        ws = str(row.get("workspace_id") or "default")
        config = store.get_config(ws)
        max_retries = int(config.get("max_retries") or 3)
        interval = int(config.get("retry_interval_seconds") or 300)
        attempts = int(row.get("attempts") or 0)
        if attempts >= max_retries:
            skipped += 1
            continue
        last = _parse_iso(row.get("last_attempted_at"))
        if last is not None and now - last < timedelta(seconds=interval):
            skipped += 1
            continue
        try:
            await retry_notification(str(row["id"]))
            retried += 1
        except Exception as exc:
            errors += 1
            logger.warning("notify_external retry failed id=%s error=%s", row.get("id"), exc)
    return {"retried": retried, "skipped": skipped, "errors": errors}
