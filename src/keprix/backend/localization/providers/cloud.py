"""Cloud translation fallback provider."""

from __future__ import annotations

import os

from keprix.backend.localization.providers.base import LanguagePairUnsupported, LocalizationProvider
from keprix.backend.localization.providers.openai import OpenAITranslationProvider
from keprix.backend.localization.schemas import TranslationResult


class CloudTranslationProvider(LocalizationProvider):
    name = "cloud"
    capabilities = {"translation", "detection"}

    def __init__(self, *, allow_cloud: bool = True) -> None:
        self.allow_cloud = allow_cloud

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        preserve_terms: list[str] | None = None,
    ) -> TranslationResult:
        if not self.allow_cloud:
            raise LanguagePairUnsupported(
                source_language,
                target_language,
                "t2t",
                self.name,
            )
        if os.environ.get("OPENAI_API_KEY", "").strip():
            return await OpenAITranslationProvider().translate(
                text,
                source_language,
                target_language,
                preserve_terms=preserve_terms,
            )
        return TranslationResult(
            source_language=source_language,
            target_language=target_language,
            source_text=text,
            translated_text=text,
            confidence=0.0,
            glossary_matches=[],
            warnings=["Cloud translation unavailable; workspace policy or API key missing"],
            provider="cloud_unavailable",
        )
