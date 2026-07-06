"""OpenAI-backed translation provider."""

from __future__ import annotations

import json
import os

import httpx

from keprix.backend.localization.providers.base import LocalizationProvider
from keprix.backend.localization.providers.seamless_m4t import protect_terms, restore_terms
from keprix.backend.localization.schemas import TranslationResult


class OpenAITranslationProvider(LocalizationProvider):
    name = "openai"
    capabilities = {"translation"}

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        preserve_terms: list[str] | None = None,
    ) -> TranslationResult:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            return TranslationResult(
                source_language=source_language,
                target_language=target_language,
                source_text=text,
                translated_text=text,
                confidence=0.0,
                glossary_matches=[],
                warnings=["OPENAI_API_KEY not configured"],
                provider=self.name,
            )

        protected, restore_map = protect_terms(text, preserve_terms or [])
        payload = {
            "model": os.environ.get("KEPRIX_LOCALIZATION_TRANSLATE_MODEL", "gpt-4o-mini"),
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"Translate from {source_language} to {target_language}. "
                        "Preserve placeholders like __TERM_0__ exactly."
                    ),
                },
                {"role": "user", "content": protected},
            ],
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        translated = restore_terms(body["choices"][0]["message"]["content"].strip(), restore_map)
        return TranslationResult(
            source_language=source_language,
            target_language=target_language,
            source_text=text,
            translated_text=translated,
            confidence=0.88,
            glossary_matches=list(preserve_terms or []),
            warnings=[],
            provider=self.name,
        )
