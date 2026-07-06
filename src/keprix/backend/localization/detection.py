"""Language detection providers."""

from __future__ import annotations

import os
import re
from typing import Any

import httpx

from keprix.backend.localization.catalog import get_catalog_entry, load_catalog
from keprix.backend.localization.schemas import LanguageDetectionResult


_SCRIPT_HINTS: list[tuple[str, str, float]] = [
    (r"[\u1200-\u137F]", "am-ET", 0.82),
    (r"[\u0600-\u06FF]", "ar-EG", 0.78),
]

_KEYWORD_HINTS: list[tuple[str, str, float]] = [
    (r"\b(mepa|borehole|twi|akwaaba)\b", "ak-GH", 0.72),
    (r"\b(ɛ|eʋe|eve)\b", "ee-GH", 0.7),
    (r"\b(sawa|jambo|habari)\b", "sw-KE", 0.75),
    (r"\b(sannu|ina kwana)\b", "ha-NG", 0.75),
    (r"\b(bawo|se daade)\b", "yo-NG", 0.72),
    (r"\b(kedu|nno)\b", "ig-NG", 0.72),
    (r"\b(sawubona|yebo)\b", "zu-ZA", 0.72),
]


class LocalLanguageDetector:
    name = "local"

    async def detect(self, text: str, *, hint: str | None = None) -> LanguageDetectionResult:
        if hint:
            entry = get_catalog_entry(hint)
            if entry:
                return LanguageDetectionResult(
                    language_code=entry.code,
                    language_name=entry.name,
                    confidence=0.95,
                    provider=self.name,
                    script=entry.script,
                )

        lowered = text.lower().strip()
        if not lowered:
            return LanguageDetectionResult(
                language_code="en",
                language_name="English",
                confidence=0.0,
                provider=self.name,
                alternatives=[],
            )

        if re.search(r"^[a-z0-9\s.,!?;:'\"()-]+$", lowered):
            return LanguageDetectionResult(
                language_code="en-GH",
                language_name="English (Ghana)",
                confidence=0.55,
                provider=self.name,
                script="Latin",
            )

        for pattern, code, confidence in _SCRIPT_HINTS:
            if re.search(pattern, text):
                entry = get_catalog_entry(code)
                return LanguageDetectionResult(
                    language_code=code,
                    language_name=entry.name if entry else code,
                    confidence=confidence,
                    provider=self.name,
                    script=entry.script if entry else None,
                )

        for pattern, code, confidence in _KEYWORD_HINTS:
            if re.search(pattern, lowered):
                entry = get_catalog_entry(code)
                return LanguageDetectionResult(
                    language_code=code,
                    language_name=entry.name if entry else code,
                    confidence=confidence,
                    provider=self.name,
                    alternatives=[{"language_code": "en-GH", "confidence": 0.4}],
                )

        return LanguageDetectionResult(
            language_code="en-GH",
            language_name="English (Ghana)",
            confidence=0.35,
            provider=self.name,
            alternatives=[entry.to_dict() for entry in load_catalog()[:3]],
        )


class CloudLanguageDetector:
    name = "cloud_openai"

    async def detect(self, text: str, *, hint: str | None = None) -> LanguageDetectionResult:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            return await LocalLanguageDetector().detect(text, hint=hint)

        payload = {
            "model": os.environ.get("KEPRIX_LOCALIZATION_DETECT_MODEL", "gpt-4o-mini"),
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Detect the language of the user message. "
                        "Return JSON: {language_code, language_name, confidence} using BCP 47."
                    ),
                },
                {"role": "user", "content": text[:2000]},
            ],
            "response_format": {"type": "json_object"},
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
            import json

            content = body["choices"][0]["message"]["content"]
            parsed: dict[str, Any] = json.loads(content)
            return LanguageDetectionResult(
                language_code=str(parsed.get("language_code") or "en"),
                language_name=str(parsed.get("language_name") or "Unknown"),
                confidence=float(parsed.get("confidence") or 0.8),
                provider=self.name,
            )
        except Exception:
            return await LocalLanguageDetector().detect(text, hint=hint)


async def detect_language(
    text: str,
    *,
    hint: str | None = None,
    allow_cloud: bool = True,
) -> LanguageDetectionResult:
    if allow_cloud and os.environ.get("OPENAI_API_KEY", "").strip():
        return await CloudLanguageDetector().detect(text, hint=hint)
    return await LocalLanguageDetector().detect(text, hint=hint)
