"""User and channel language preferences."""

from __future__ import annotations

from typing import Any

from keprix.backend.localization.config import LocalizationSettings
from keprix.backend.localization.store import get_localization_store


class PreferenceService:
    def __init__(self) -> None:
        self._store = get_localization_store()

    async def get(
        self,
        workspace_id: str,
        user_id: str,
        settings: LocalizationSettings | None = None,
    ) -> dict[str, Any]:
        settings = settings or LocalizationSettings.from_env(workspace_id)
        existing = await self._store.get_preferences(workspace_id, user_id)
        if existing:
            return existing
        return {
            "workspace_id": workspace_id,
            "user_id": user_id,
            "preferred_input_language": None,
            "preferred_output_language": settings.default_output_language,
            "voice_output_enabled": settings.default_voice_output,
            "preferred_voice_id": None,
            "bilingual_replies": False,
        }

    async def resolve_output_language(
        self,
        workspace_id: str,
        user_id: str | None,
        *,
        channel_language: str | None = None,
        settings: LocalizationSettings | None = None,
    ) -> str:
        settings = settings or LocalizationSettings.from_env(workspace_id)
        if user_id:
            prefs = await self.get(workspace_id, user_id, settings)
            if prefs.get("preferred_output_language"):
                return str(prefs["preferred_output_language"])
        if channel_language:
            return channel_language
        return settings.default_output_language

    async def update(self, workspace_id: str, user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "preferred_input_language",
            "preferred_output_language",
            "voice_output_enabled",
            "preferred_voice_id",
            "bilingual_replies",
        }
        filtered = {key: value for key, value in patch.items() if key in allowed}
        return await self._store.upsert_preferences(workspace_id, user_id, filtered)

    async def reset(self, workspace_id: str, user_id: str) -> dict[str, Any]:
        settings = LocalizationSettings.from_env(workspace_id)
        return await self._store.upsert_preferences(
            workspace_id,
            user_id,
            {
                "preferred_input_language": None,
                "preferred_output_language": settings.default_output_language,
                "voice_output_enabled": settings.default_voice_output,
                "preferred_voice_id": None,
                "bilingual_replies": False,
            },
        )


_preference_service: PreferenceService | None = None


def get_preference_service() -> PreferenceService:
    global _preference_service
    if _preference_service is None:
        _preference_service = PreferenceService()
    return _preference_service


def reset_preference_service() -> None:
    global _preference_service
    _preference_service = None
