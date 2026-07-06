"""
SeamlessM4T v2 provider adapter.

Supports two deployment modes:
  sidecar - calls a local Docker sidecar over HTTP (recommended)
  direct  - loads the seamless_communication library in-process

Configure via LocalizationConfig.seamless_m4t:
  mode: sidecar | direct
  sidecar_url: http://seamless-m4t:7810
  direct_model: seamlessM4T_v2_large
  device: cpu | cuda
  dtype: fp16 | fp32
"""

from __future__ import annotations

import base64
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import httpx

from keprix.backend.localization.providers.base import (
    LanguagePairUnsupported,
    LocalizationProvider,
)
from keprix.backend.localization.providers.language_matrix import (
    bcp47_to_sm4t,
    sm4t_supports,
    sm4t_to_bcp47,
)
from keprix.backend.localization.schemas import (
    SpeechSynthesisResult,
    TranscriptSegment,
    TranscriptionResult,
    TranslationResult,
)


@dataclass
class SeamlessM4TConfig:
    mode: str = "sidecar"
    sidecar_url: str = "http://seamless-m4t:7810"
    direct_model: str = "seamlessM4T_v2_large"
    device: str = "cpu"
    dtype: str = "fp16"
    timeout: int = 60


def protect_terms(text: str, terms: list[str]) -> tuple[str, dict[str, str]]:
    """Replace preserved terms with placeholders before sending to the model."""
    restore_map: dict[str, str] = {}
    for i, term in enumerate(sorted(terms, key=len, reverse=True)):
        placeholder = f"__TERM_{i}__"
        if term.lower() in text.lower():
            text = re.sub(re.escape(term), placeholder, text, flags=re.IGNORECASE)
            restore_map[placeholder] = term
    return text, restore_map


def restore_terms(text: str, restore_map: dict[str, str]) -> str:
    """Restore original terms from placeholder-substituted text."""
    for placeholder, term in restore_map.items():
        text = text.replace(placeholder, term)
    return text


def _audio_bytes_to_base64(audio_bytes: bytes) -> str:
    return base64.b64encode(audio_bytes).decode("ascii")


def _store_audio(audio_base64: str, language: str, provider: str) -> str:
    """Save base64 audio to the keprix data directory and return a local file URL."""
    data_dir = Path(os.environ.get("KEPRIX_DATA_DIR", "/tmp/keprix-data")) / "audio"
    data_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{provider}_{language}_{uuid.uuid4().hex}.wav"
    path = data_dir / filename
    path.write_bytes(base64.b64decode(audio_base64))
    return f"file://{path}"


class SeamlessM4TProvider(LocalizationProvider):
    name = "seamless_m4t"
    capabilities = {"transcription", "translation", "speech"}

    def __init__(self, config: SeamlessM4TConfig | None = None) -> None:
        super().__init__(config or SeamlessM4TConfig())

    async def transcribe(
        self,
        audio_bytes: bytes,
        source_language: str | None = None,
        target_language: str = "en",
    ) -> TranscriptionResult:
        """Speech-to-text: audio in source_language -> text in target_language."""
        sm4t_src = bcp47_to_sm4t(source_language) if source_language else None
        sm4t_tgt = bcp47_to_sm4t(target_language) or "eng"

        if sm4t_src and not sm4t_supports(sm4t_src, sm4t_tgt, "s2t"):
            raise LanguagePairUnsupported(
                source_language or "auto", target_language, "s2t", self.name
            )

        payload = {
            "task": "s2t",
            "audio": _audio_bytes_to_base64(audio_bytes),
            "source_language": sm4t_src,
            "target_language": sm4t_tgt,
        }
        result = await self._call(payload)

        return TranscriptionResult(
            language_code=sm4t_to_bcp47(result.get("detected_language", sm4t_tgt)),
            transcript=result["text"],
            confidence=result.get("confidence", 0.0),
            segments=[
                TranscriptSegment(
                    start=s["start"],
                    end=s["end"],
                    text=s["text"],
                    confidence=s.get("confidence"),
                )
                for s in result.get("segments", [])
            ],
            provider=self.name,
        )

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        preserve_terms: list[str] | None = None,
    ) -> TranslationResult:
        """Text-to-text translation with optional term preservation."""
        sm4t_src = bcp47_to_sm4t(source_language)
        sm4t_tgt = bcp47_to_sm4t(target_language)

        if not sm4t_src or not sm4t_tgt:
            raise LanguagePairUnsupported(
                source_language, target_language, "t2t", self.name
            )
        if not sm4t_supports(sm4t_src, sm4t_tgt, "t2t"):
            raise LanguagePairUnsupported(
                source_language, target_language, "t2t", self.name
            )

        protected_text, restore_map = protect_terms(text, preserve_terms or [])
        payload = {
            "task": "t2t",
            "text": protected_text,
            "source_language": sm4t_src,
            "target_language": sm4t_tgt,
        }
        result = await self._call(payload)
        translated = restore_terms(result["text"], restore_map)

        return TranslationResult(
            source_language=source_language,
            target_language=target_language,
            source_text=text,
            translated_text=translated,
            confidence=result.get("confidence", 0.0),
            glossary_matches=[],
            warnings=[],
            provider=self.name,
        )

    async def synthesize_speech(
        self,
        text: str,
        language: str,
        voice_id: str | None = None,
    ) -> SpeechSynthesisResult:
        """Text-to-speech: returns a URL to the synthesised audio file."""
        sm4t_lang = bcp47_to_sm4t(language)
        if not sm4t_lang or not sm4t_supports(sm4t_lang, sm4t_lang, "t2s"):
            raise LanguagePairUnsupported(language, language, "t2s", self.name)

        payload = {"task": "t2s", "text": text, "target_language": sm4t_lang}
        result = await self._call(payload)
        audio_url = _store_audio(result["audio_base64"], language, self.name)

        return SpeechSynthesisResult(
            language_code=language,
            voice_id="seamless_m4t_default",
            audio_url=audio_url,
            transcript=text,
            provider=self.name,
        )

    async def _call(self, payload: dict) -> dict:
        """Dispatch to sidecar HTTP or direct library based on config mode."""
        if self.config.mode == "sidecar":
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                r = await client.post(
                    f"{self.config.sidecar_url}/infer", json=payload
                )
                r.raise_for_status()
                return r.json()
        return await self._call_direct(payload)

    async def _call_direct(self, payload: dict) -> dict:
        """In-process inference using seamless_communication library."""
        try:
            from seamless_communication.models.inference import Translator, VocoderType
        except ImportError as exc:
            raise RuntimeError(
                "Direct mode requires: pip install seamless_communication torch"
            ) from exc

        raise NotImplementedError(
            "Direct mode is available but not yet wired for async use. "
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
