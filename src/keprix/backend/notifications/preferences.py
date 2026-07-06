"""User notification preferences (Prompt 24)."""

from __future__ import annotations

from typing import Any

from keprix.backend.notifications.store import get_notification_store


class NotificationPreferencesService:
    def __init__(self) -> None:
        self._store = get_notification_store()

    def get(self, workspace_id: str, user_id: str) -> dict[str, Any]:
        prefs = self._store.get_preferences(workspace_id, user_id)
        prefs.setdefault("workspace_id", workspace_id)
        prefs.setdefault("user_id", user_id)
        return prefs

    def update(self, workspace_id: str, user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        return self._store.save_preferences(workspace_id, user_id, patch)


_service: NotificationPreferencesService | None = None


def get_preferences_service() -> NotificationPreferencesService:
    global _service
    if _service is None:
        _service = NotificationPreferencesService()
    return _service
