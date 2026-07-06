"""
NLLB-200 (No Language Left Behind) provider adapter.

Text-to-text translation only. Used as:
  - Fallback when SeamlessM4T does not support the language pair.
  - Primary translator for languages where NLLB has better coverage.
  - Batch translation for glossary and corpus preparation.

Configure via LocalizationConfig.nllb_200:
  mode: sidecar | direct
  sidecar_url: http://nllb-200:7811
  model: facebook/nllb-200-distilled-600M
  max_length: 512
  num_beams: 4
  device: cpu
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx

from keprix.backend.localization.providers.base import (
    LanguagePairUnsupported,
    LocalizationProvider,
)
from keprix.backend.localization.providers.language_matrix import bcp47_to_nllb
from keprix.backend.localization.providers.seamless_m4t import protect_terms, restore_terms
from keprix.backend.localization.schemas import TranslationResult


@dataclass
class NLLB200Config:
    mode: str = "sidecar"
    sidecar_url: str = "http://nllb-200:7811"
    model: str = "facebook/nllb-200-distilled-600M"
    max_length: int = 512
    num_beams: int = 4
    device: str = "cpu"
    timeout: int = 60


class NLLB200Provider(LocalizationProvider):
    name = "nllb_200"
    capabilities = {"translation"}  # no transcription, no speech

    def __init__(self, config: NLLB200Config | None = None) -> None:
        super().__init__(config or NLLB200Config())

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        preserve_terms: list[str] | None = None,
    ) -> TranslationResult:
        """Translate a single text string between two BCP 47 languages."""
        nllb_src = bcp47_to_nllb(source_language)
        nllb_tgt = bcp47_to_nllb(target_language)

        if not nllb_src or not nllb_tgt:
            raise LanguagePairUnsupported(
                source_language, target_language, "t2t", self.name
            )

        protected_text, restore_map = protect_terms(text, preserve_terms or [])
        payload = {
            "text": protected_text,
            "source_language": nllb_src,
            "target_language": nllb_tgt,
        }
        result = await self._call(payload)
        translated = restore_terms(result["translation"], restore_map)

        return TranslationResult(
            source_language=source_language,
            target_language=target_language,
            source_text=text,
            translated_text=translated,
            confidence=result.get("score", 0.0),
            glossary_matches=[],
            warnings=[],
            provider=self.name,
        )

    async def batch_translate(
        self,
        texts: list[str],
        source_language: str,
        target_language: str,
    ) -> list[TranslationResult]:
        """Translate multiple texts in a single sidecar call."""
        nllb_src = bcp47_to_nllb(source_language)
        nllb_tgt = bcp47_to_nllb(target_language)

        if not nllb_src or not nllb_tgt:
            raise LanguagePairUnsupported(
                source_language, target_language, "t2t", self.name
            )

        payload = {
            "texts": texts,
            "source_language": nllb_src,
            "target_language": nllb_tgt,
        }
        result = await self._call_batch(payload)
        translations = result.get("translations", [])

        return [
            TranslationResult(
                source_language=source_language,
                target_language=target_language,
                source_text=original,
                translated_text=translated.get("translation", ""),
                confidence=translated.get("score", 0.0),
                glossary_matches=[],
                warnings=[],
                provider=self.name,
            )
            for original, translated in zip(texts, translations)
        ]

    async def _call(self, payload: dict) -> dict:
        if self.config.mode == "sidecar":
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                r = await client.post(
                    f"{self.config.sidecar_url}/translate", json=payload
                )
                r.raise_for_status()
                return r.json()
        return await self._call_direct(payload)

    async def _call_batch(self, payload: dict) -> dict:
        if self.config.mode == "sidecar":
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                r = await client.post(
                    f"{self.config.sidecar_url}/translate-batch", json=payload
                )
                r.raise_for_status()
                return r.json()
        raise NotImplementedError("Direct batch mode not yet implemented")

    async def _call_direct(self, payload: dict) -> dict:
        """In-process inference using the transformers library."""
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "Direct mode requires: pip install transformers sentencepiece"
            ) from exc

        raise NotImplementedError(
            "Direct mode is available but requires async wrapping. "
            "Set mode='sidecar' and run the Docker sidecar instead."
        )

    async def health_check(self) -> dict:
        try:
            if self.config.mode == "sidecar":
                async with httpx.AsyncClient(timeout=5) as client:
                    r = await client.get(f"{self.config.sidecar_url}/health")
                    return {
                        "status": "ok" if r.status_code == 200 else "degraded",
                        "provider": self.name,
                        "mode": "sidecar",
                    }
            return {"status": "ok", "provider": self.name, "mode": "direct"}
        except Exception as exc:
            return {"status": "error", "provider": self.name, "detail": str(exc)}
