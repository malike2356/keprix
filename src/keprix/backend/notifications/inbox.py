"""Unified inbox and notification dispatch (Prompt 24)."""

from __future__ import annotations

from typing import Any

from keprix.backend.notifications.channels import get_channel_delivery
from keprix.backend.notifications.escalation import get_escalation_service
from keprix.backend.notifications.router import route_channels
from keprix.backend.notifications.schemas import NOTIFICATION_TYPES
from keprix.backend.notifications.store import get_notification_store
from keprix.backend.notifications.templates import render_notification


class InboxService:
    def __init__(self) -> None:
        self._store = get_notification_store()
        self._channels = get_channel_delivery()

    async def send_notification(
        self,
        workspace_id: str,
        notification_type: str,
        *,
        severity: str = "info",
        title: str | None = None,
        message: str,
        user_id: str | None = None,
        href: str | None = None,
        sensitive: bool = False,
        metadata: dict[str, Any] | None = None,
        source: str = "system",
        source_id: str | None = None,
        simulate_delivery_failure: bool = False,
    ) -> dict[str, Any]:
        if notification_type not in NOTIFICATION_TYPES:
            raise ValueError(f"Unsupported notification_type: {notification_type}")

        rendered = render_notification(notification_type, message, title=title)
        routing = route_channels(
            workspace_id=workspace_id,
            user_id=user_id,
            severity=severity,
            sensitive=sensitive,
            notification_type=notification_type,
        )

        notification = self._store.create_notification(
            workspace_id,
            {
                "notification_type": notification_type,
                "severity": severity,
                "title": rendered["title"],
                "message": rendered["message"],
                "user_id": user_id,
                "href": href,
                "sensitive": sensitive,
                "metadata": metadata or {},
                "source": source,
                "source_id": source_id,
                "channels_planned": routing["channels"],
            },
        )

        deliveries: list[dict[str, Any]] = []
        if routing["delay_for_digest"]:
            self._store.queue_digest(
                workspace_id,
                {
                    "notification_id": notification["id"],
                    "title": notification["title"],
                    "message": notification["message"],
                    "user_id": user_id,
                },
            )
        else:
            for channel in routing["channels"]:
                result = await self._channels.deliver(
                    workspace_id=workspace_id,
                    channel=channel,
                    notification=notification,
                    user_id=user_id,
                    sensitive=sensitive,
                    simulate_failure=simulate_delivery_failure and channel != "in_app",
                )
                deliveries.append(result)

        if notification_type in {"approval_needed", "pack_gate_pending"}:
            get_escalation_service().schedule_approval_escalation(
                workspace_id,
                notification_id=str(notification["id"]),
                user_id=user_id,
            )

        notification["deliveries"] = deliveries
        notification["delayed_for_digest"] = routing["delay_for_digest"]
        return notification

    def list_inbox(
        self,
        workspace_id: str,
        *,
        user_id: str | None = None,
        unread_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return self._store.list_notifications(
            workspace_id,
            user_id=user_id,
            unread_only=unread_only,
            limit=limit,
            offset=offset,
        )

    def get_notification(self, workspace_id: str, notification_id: str) -> dict[str, Any] | None:
        return self._store.get_notification(workspace_id, notification_id)

    def mark_read(self, workspace_id: str, notification_id: str) -> dict[str, Any] | None:
        return self._store.mark_read(workspace_id, notification_id)

    def mark_all_read(self, workspace_id: str, user_id: str | None = None) -> int:
        return self._store.mark_all_read(workspace_id, user_id)

    def unread_count(self, workspace_id: str, user_id: str | None = None) -> int:
        return self._store.unread_count(workspace_id, user_id)


_service: InboxService | None = None


def get_inbox_service() -> InboxService:
    global _service
    if _service is None:
        _service = InboxService()
    return _service
