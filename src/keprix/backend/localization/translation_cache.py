"""Workspace-level translation override cache."""

from __future__ import annotations

from keprix.backend.localization.store import get_localization_store


class TranslationCacheOverride:
    async def get_override(
        self,
        workspace_id: str,
        source_language: str,
        target_language: str,
        source_text: str,
    ) -> str | None:
        return get_localization_store().get_translation_override(
            workspace_id, source_language, target_language, source_text
        )

    async def set_override(
        self,
        workspace_id: str,
        source_language: str,
        target_language: str,
        source_text: str,
        corrected_text: str,
    ) -> None:
        get_localization_store().set_translation_override(
            workspace_id,
            source_language,
            target_language,
            source_text,
            corrected_text,
        )


translation_cache_override = TranslationCacheOverride()
