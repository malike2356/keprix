"""Channel delivery adapters (Prompt 24)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from keprix.backend.notifications.store import get_notification_store

GROUP_CHANNELS = frozenset({"slack", "telegram", "discord", "webchat"})


class ChannelDelivery:
    def __init__(self) -> None:
        self._store = get_notification_store()
        self._group_deliveries: list[dict[str, Any]] = []

    def reset_group_deliveries(self) -> None:
        self._group_deliveries.clear()

    def pop_group_deliveries(self) -> list[dict[str, Any]]:
        rows = list(self._group_deliveries)
        self._group_deliveries.clear()
        return rows

    async def deliver(
        self,
        *,
        workspace_id: str,
        channel: str,
        notification: dict[str, Any],
        user_id: str | None,
        sensitive: bool,
        simulate_failure: bool = False,
    ) -> dict[str, Any]:
        if sensitive and channel in GROUP_CHANNELS:
            return {
                "channel": channel,
                "status": "blocked",
                "reason": "sensitive_data",
            }

        delivery = self._store.create_delivery(
            workspace_id,
            {
                "notification_id": notification.get("id"),
                "channel": channel,
                "user_id": user_id,
                "notification_type": notification.get("notification_type"),
            },
        )

        if simulate_failure:
            self._store.update_delivery(
                workspace_id,
                str(delivery["id"]),
                {
                    "status": "failed",
                    "attempts": 1,
                    "last_error": "simulated_failure",
                    "next_retry_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            return {"channel": channel, "status": "failed", "delivery_id": delivery["id"]}

        if channel == "in_app":
            self._store.update_delivery(
                workspace_id,
                str(delivery["id"]),
                {"status": "delivered", "delivered_at": datetime.now(timezone.utc).isoformat()},
            )
            return {"channel": channel, "status": "delivered", "delivery_id": delivery["id"]}

        if channel == "email":
            result = await self._deliver_email(workspace_id, notification, user_id)
            status = "delivered" if result.get("queued") else "failed"
            self._store.update_delivery(
                workspace_id,
                str(delivery["id"]),
                {
                    "status": status,
                    "delivered_at": datetime.now(timezone.utc).isoformat() if status == "delivered" else None,
                    "details": result,
                },
            )
            return {"channel": channel, "status": status, "delivery_id": delivery["id"], "details": result}

        if channel in GROUP_CHANNELS:
            payload = {
                "channel": channel,
                "notification_id": notification.get("id"),
                "title": notification.get("title"),
                "message": notification.get("message"),
            }
            self._group_deliveries.append(payload)
            self._store.update_delivery(
                workspace_id,
                str(delivery["id"]),
                {"status": "delivered", "delivered_at": datetime.now(timezone.utc).isoformat()},
            )
            return {"channel": channel, "status": "delivered", "delivery_id": delivery["id"]}

        if channel == "push":
            from keprix.backend.notifications.push import get_push_service

            await get_push_service().send(
                workspace_id=workspace_id,
                title=str(notification.get("title") or "Notification"),
                message=str(notification.get("message") or ""),
                user_id=user_id,
            )
            self._store.update_delivery(
                workspace_id,
                str(delivery["id"]),
                {"status": "delivered", "delivered_at": datetime.now(timezone.utc).isoformat()},
            )
            return {"channel": channel, "status": "delivered", "delivery_id": delivery["id"]}

        self._store.update_delivery(
            workspace_id,
            str(delivery["id"]),
            {"status": "failed", "last_error": "unknown_channel"},
        )
        return {"channel": channel, "status": "failed", "delivery_id": delivery["id"]}

    async def _deliver_email(
        self,
        workspace_id: str,
        notification: dict[str, Any],
        user_id: str | None,
    ) -> dict[str, Any]:
        recipient = notification.get("metadata", {}).get("email_recipient")
        if not recipient:
            return {"queued": False, "reason": "no_recipient"}
        try:
            from keprix.notify_external.smtp_sender import send_email

            notification_id = await send_email(
                workspace_id,
                recipient,
                template_name="generic_alert",
                template_vars={
                    "title": notification.get("title"),
                    "message": notification.get("message"),
                    "href": notification.get("href") or "",
                },
                triggered_by="notifications",
                triggered_by_id=str(notification.get("id")),
            )
            return {"queued": True, "notification_id": notification_id}
        except Exception as exc:
            return {"queued": False, "error": str(exc)}


_delivery: ChannelDelivery | None = None


def get_channel_delivery() -> ChannelDelivery:
    global _delivery
    if _delivery is None:
        _delivery = ChannelDelivery()
    return _delivery
