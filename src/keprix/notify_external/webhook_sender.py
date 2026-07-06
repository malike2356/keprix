"""Signed webhook dispatch for external notifications."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from keprix.notify_external.store import get_notify_external_store, recipient_domain
from keprix.security.audit import audit_log

logger = logging.getLogger(__name__)


class WebhookTargetRejected(Exception):
    pass


def validate_webhook_url(webhook_url: str) -> None:
    parsed = urlparse(webhook_url.strip())
    if parsed.scheme != "https":
        raise WebhookTargetRejected("Webhook URL must use https")
    host = (parsed.hostname or "").lower()
    if not host:
        raise WebhookTargetRejected("Webhook URL missing hostname")
    blocked_prefixes = ("localhost", "127.", "10.", "192.168.", "169.254.")
    if host == "localhost" or host.endswith(".localhost"):
        raise WebhookTargetRejected("Webhook target rejected")
    for prefix in blocked_prefixes:
        if host.startswith(prefix):
            raise WebhookTargetRejected("Webhook target rejected")
    try:
        addr = ipaddress.ip_address(host)
        if addr.is_private or addr.is_loopback or addr.is_link_local:
            raise WebhookTargetRejected("Webhook target rejected")
    except ValueError:
        pass


def _webhook_secret_sync(workspace_id: str, config: dict[str, Any]) -> bytes:
    return f"keprix-webhook-{workspace_id}".encode("utf-8")


async def _webhook_secret(workspace_id: str, config: dict[str, Any]) -> bytes:
    vault_id = config.get("webhook_signing_secret_vault_id")
    if vault_id:
        from keprix.security.vault_service import get_vault_service

        item = await get_vault_service().get_item(str(vault_id), user_id="system", decrypt=True)
        if item is not None and getattr(item, "_value", None):
            return str(item._value).encode("utf-8")
    return _webhook_secret_sync(workspace_id, config)


async def send_webhook(
    workspace_id: str,
    webhook_url: str,
    payload: dict[str, Any],
    *,
    triggered_by: str = "api",
    triggered_by_id: str | None = None,
    timeout_seconds: int = 30,
) -> str:
    store = get_notify_external_store()
    if not store.check_rate_limit(workspace_id):
        from keprix.notify_external.smtp_sender import RateLimitExceeded

        raise RateLimitExceeded("External notification rate limit exceeded")

    validate_webhook_url(webhook_url)
    row = store.create_notification(
        workspace_id,
        {
            "channel": "webhook",
            "recipient_address": webhook_url,
            "subject": None,
            "body_text": json.dumps(payload, separators=(",", ":"), sort_keys=True),
            "template_name": None,
            "template_vars": payload,
            "triggered_by": triggered_by,
            "triggered_by_id": triggered_by_id,
        },
    )
    notification_id = str(row["id"])
    config = store.get_config(workspace_id)
    secret = await _webhook_secret(workspace_id, config)
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-Keprix-Signature": f"sha256={signature}",
        "X-Keprix-Workspace": workspace_id,
        "X-Keprix-Delivery-ID": notification_id,
        "User-Agent": "keprix/0.1.0",
    }
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=False) as client:
            response = await client.post(webhook_url, content=body, headers=headers)
        if response.status_code < 200 or response.status_code >= 300:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:500]}")
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
                "channel": "webhook",
                "recipient_domain": recipient_domain(webhook_url),
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
        logger.warning("notify_external webhook failed workspace=%s error=%s", workspace_id, exc)
        raise
    return notification_id


def verify_webhook_signature(payload: bytes, secret: bytes, signature_header: str) -> bool:
    provided = signature_header.strip()
    if provided.startswith("sha256="):
        provided = provided.split("=", 1)[1]
    expected = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided)
