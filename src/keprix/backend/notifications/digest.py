"""Digest email batching (Prompt 24)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from keprix.backend.notifications.channels import get_channel_delivery
from keprix.backend.notifications.router import in_quiet_hours
from keprix.backend.notifications.preferences import get_preferences_service
from keprix.backend.notifications.store import get_notification_store


class DigestService:
    def __init__(self) -> None:
        self._store = get_notification_store()
        self._channels = get_channel_delivery()

    async def flush_digest_queue(self, workspace_id: str, user_id: str = "default") -> dict[str, Any]:
        prefs = get_preferences_service().get(workspace_id, user_id)
        if in_quiet_hours(prefs):
            return {"flushed": 0, "reason": "still_in_quiet_hours"}

        queued = self._store.list_digest_queue(workspace_id)
        if not queued:
            return {"flushed": 0}

        lines = [f"- {row.get('title')}: {row.get('message')}" for row in queued]
        notification = {
            "id": "digest-batch",
            "title": "Notification digest",
            "message": "\n".join(lines),
            "notification_type": "digest",
            "metadata": {"email_recipient": prefs.get("digest_email")},
        }
        result = await self._channels.deliver(
            workspace_id=workspace_id,
            channel="email",
            notification=notification,
            user_id=user_id,
            sensitive=False,
        )
        self._store.clear_digest_queue(workspace_id)
        return {"flushed": len(queued), "delivery": result, "sent_at": datetime.now(timezone.utc).isoformat()}


_service: DigestService | None = None


def get_digest_service() -> DigestService:
    global _service
    if _service is None:
        _service = DigestService()
    return _service
