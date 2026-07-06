"""Delivery retry logic (Prompt 24)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from keprix.backend.notifications.channels import get_channel_delivery
from keprix.backend.notifications.store import get_notification_store

MAX_RETRIES = 3
RETRY_INTERVAL_SECONDS = 60


class DeliveryService:
    def __init__(self) -> None:
        self._store = get_notification_store()
        self._channels = get_channel_delivery()

    async def retry_failed_deliveries(self, workspace_id: str) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        results: list[dict[str, Any]] = []
        for row in self._store.list_deliveries(workspace_id, status="failed"):
            attempts = int(row.get("attempts") or 0)
            if attempts >= MAX_RETRIES:
                continue
            next_retry = row.get("next_retry_at")
            if next_retry:
                retry_at = datetime.fromisoformat(str(next_retry).replace("Z", "+00:00"))
                if retry_at > now:
                    continue
            notification = self._store.get_notification(workspace_id, str(row.get("notification_id")))
            if not notification:
                continue
            result = await self._channels.deliver(
                workspace_id=workspace_id,
                channel=str(row.get("channel")),
                notification=notification,
                user_id=row.get("user_id"),
                sensitive=bool(notification.get("sensitive")),
            )
            attempts += 1
            patch: dict[str, Any] = {
                "attempts": attempts,
                "last_retry_at": now.isoformat(),
            }
            if result.get("status") == "delivered":
                patch["status"] = "delivered"
                patch["delivered_at"] = now.isoformat()
            elif attempts >= MAX_RETRIES:
                patch["status"] = "permanent_failure"
            else:
                patch["next_retry_at"] = (now + timedelta(seconds=RETRY_INTERVAL_SECONDS)).isoformat()
            self._store.update_delivery(workspace_id, str(row["id"]), patch)
            results.append({"delivery_id": row["id"], **result, "attempts": attempts})
        return results


_service: DeliveryService | None = None


def get_delivery_service() -> DeliveryService:
    global _service
    if _service is None:
        _service = DeliveryService()
    return _service
