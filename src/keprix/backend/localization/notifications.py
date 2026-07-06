"""Inbox notifications for localization corrections."""

from __future__ import annotations

from typing import Any

from keprix.backend.notifications.inbox import get_inbox_service


async def notify_localization_correction(
    *,
    workspace_id: str,
    correction_type: str,
    correction_id: str,
    message: str | None = None,
) -> dict[str, Any]:
    text = message or (
        f"User submitted a localization correction ({correction_type}). "
        "Review in Settings > Localization > Corrections."
    )
    notification = await get_inbox_service().send_notification(
        workspace_id,
        "localization_correction",
        severity="info",
        title="Localization correction submitted",
        message=text,
        href="/settings/localization/corrections",
        sensitive=False,
        metadata={"correction_id": correction_id, "correction_type": correction_type},
        source="localization",
        source_id=correction_id,
    )
    return {"inbox": True, "correction_id": correction_id, "notification_id": notification.get("id")}
