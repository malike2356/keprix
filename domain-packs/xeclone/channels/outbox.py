"""Publish outbox with idempotency; retries cannot double-post."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from approvals.service import can_publish
from kill_switch.state import is_blocked
from scout.events import emit_scout_event

_LOCK = threading.RLock()
_OUTBOX: dict[str, dict[str, Any]] = {}
_PUBLISHED_BY_APPROVAL: set[str] = set()


def reset_channels() -> None:
    with _LOCK:
        _OUTBOX.clear()
        _PUBLISHED_BY_APPROVAL.clear()


def publish(
    *,
    approval_id: str,
    idempotency_key: str,
    channel: str,
    tenant_id: str,
    actor_id: str,
    shadow: bool = False,
) -> dict[str, Any]:
    if shadow:
        return {"ok": False, "error": "shadow_never_publishes"}
    if is_blocked("publish") or is_blocked("media"):
        return {"ok": False, "error": "kill_switch_active"}
    gate = can_publish(approval_id)
    if not gate.get("ok"):
        return gate
    approval = gate["approval"]
    if approval.get("preview", {}).get("private_reply") and not approval.get("owner_reviewed"):
        return {"ok": False, "error": "private_reply_requires_owner_review"}

    with _LOCK:
        if idempotency_key in _OUTBOX:
            return {"ok": True, "deduped": True, "record": dict(_OUTBOX[idempotency_key])}
        if approval_id in _PUBLISHED_BY_APPROVAL:
            return {"ok": False, "error": "already_published", "approval_id": approval_id}
        record = {
            "outbox_id": f"out_{uuid.uuid4().hex[:12]}",
            "approval_id": approval_id,
            "idempotency_key": idempotency_key,
            "channel": channel,
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "content_hash": approval["content_hash"],
            "provider_event_id": f"prov_{uuid.uuid4().hex[:10]}",
            "status": "published",
            "at": time.time(),
        }
        _OUTBOX[idempotency_key] = record
        _PUBLISHED_BY_APPROVAL.add(approval_id)

    emit_scout_event(
        "publish",
        {
            "approval_id": approval_id,
            "content_hash": approval["content_hash"],
            "channel": channel,
            "tenant_id": tenant_id,
        },
    )
    return {"ok": True, "deduped": False, "record": record}
