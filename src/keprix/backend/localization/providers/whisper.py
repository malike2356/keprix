"""Whisper-compatible transcription provider."""

from __future__ import annotations

import os

import httpx

from keprix.backend.localization.providers.base import LocalizationProvider
from keprix.backend.localization.schemas import TranscriptionResult, TranscriptSegment


class WhisperProvider(LocalizationProvider):
    name = "whisper"
    capabilities = {"transcription"}

    async def transcribe(
        self,
        audio_bytes: bytes,
        source_language: str | None = None,
        target_language: str = "en",
    ) -> TranscriptionResult:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            return TranscriptionResult(
                language_code=source_language or "en",
                transcript="",
                confidence=0.0,
                segments=[],
                provider=self.name,
            )

        files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
        data = {"model": os.environ.get("KEPRIX_WHISPER_MODEL", "whisper-1")}
        if source_language:
            data["language"] = source_language.split("-")[0]

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                data=data,
                files=files,
            )
            response.raise_for_status()
            body = response.json()

        text = str(body.get("text") or "")
        return TranscriptionResult(
            language_code=source_language or "en",
            transcript=text,
            confidence=0.85,
            segments=[TranscriptSegment(start=0.0, end=0.0, text=text, confidence=0.85)],
            provider=self.name,
        )
