"""Escalation policy for approval reminders (Prompt 24)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from keprix.backend.notifications.preferences import get_preferences_service
from keprix.backend.notifications.store import get_notification_store
from keprix.backend.notifications.templates import escalation_message


class EscalationService:
    def __init__(self) -> None:
        self._store = get_notification_store()

    def schedule_approval_escalation(
        self,
        workspace_id: str,
        *,
        notification_id: str,
        user_id: str | None,
    ) -> dict[str, Any]:
        prefs = get_preferences_service().get(workspace_id, user_id or "default")
        delay_minutes = int(prefs.get("escalation_delay_minutes") or 60)
        escalate_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
        return self._store.create_escalation(
            workspace_id,
            {
                "notification_id": notification_id,
                "user_id": user_id,
                "escalate_at": escalate_at.isoformat(),
                "escalation_count": 0,
            },
        )

    async def process_due_escalations(self, workspace_id: str) -> list[dict[str, Any]]:
        from keprix.backend.notifications.inbox import get_inbox_service

        now = datetime.now(timezone.utc)
        processed: list[dict[str, Any]] = []
        for row in self._store.list_escalations(workspace_id, status="pending"):
            escalate_at = row.get("escalate_at")
            if not escalate_at:
                continue
            due = datetime.fromisoformat(str(escalate_at).replace("Z", "+00:00"))
            if due > now:
                continue
            notification = self._store.get_notification(workspace_id, str(row.get("notification_id")))
            if not notification:
                self._store.update_escalation(workspace_id, str(row["id"]), {"status": "cancelled"})
                continue
            reminder = await get_inbox_service().send_notification(
                workspace_id,
                str(notification.get("notification_type") or "approval_needed"),
                severity="warning",
                title=f"Escalation: {notification.get('title')}",
                message=escalation_message(notification),
                user_id=row.get("user_id"),
                href=notification.get("href"),
                sensitive=bool(notification.get("sensitive")),
                metadata={"escalation_of": notification.get("id")},
                source="escalation",
                source_id=str(row["id"]),
            )
            self._store.update_escalation(
                workspace_id,
                str(row["id"]),
                {
                    "status": "escalated",
                    "escalated_at": now.isoformat(),
                    "escalation_count": int(row.get("escalation_count") or 0) + 1,
                    "reminder_notification_id": reminder.get("id"),
                },
            )
            processed.append({"escalation_id": row["id"], "reminder": reminder})
        return processed


_service: EscalationService | None = None


def get_escalation_service() -> EscalationService:
    global _service
    if _service is None:
        _service = EscalationService()
    return _service
