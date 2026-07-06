"""Local provider stubs (identity passthrough for workspace language)."""

from __future__ import annotations

from keprix.backend.localization.providers.base import LocalizationProvider
from keprix.backend.localization.schemas import TranslationResult


class LocalProvider(LocalizationProvider):
    name = "local"
    capabilities = {"translation"}

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        preserve_terms: list[str] | None = None,
    ) -> TranslationResult:
        return TranslationResult(
            source_language=source_language,
            target_language=target_language,
            source_text=text,
            translated_text=text,
            confidence=0.5,
            glossary_matches=list(preserve_terms or []),
            warnings=["Local provider returned source text unchanged"],
            provider=self.name,
        )
