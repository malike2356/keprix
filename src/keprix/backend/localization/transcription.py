"""Speech transcription service."""

from __future__ import annotations

import os

from keprix.backend.localization.config import LocalizationSettings
from keprix.backend.localization.detection import detect_language
from keprix.backend.localization.providers.seamless_m4t import SeamlessM4TConfig, SeamlessM4TProvider
from keprix.backend.localization.providers.whisper import WhisperProvider
from keprix.backend.localization.router import LocalizationConfig, ProviderConfig, select_transcription_provider
from keprix.backend.localization.schemas import TranscriptionResult


def _router_config() -> LocalizationConfig:
    sm4t_on = os.environ.get("KEPRIX_LOCALIZATION_SM4T_ENABLED", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return LocalizationConfig(
        seamless_m4t=ProviderConfig(enabled=sm4t_on),
        whisper=ProviderConfig(enabled=bool(os.environ.get("OPENAI_API_KEY"))),
    )


async def transcribe_audio(
    audio_bytes: bytes,
    *,
    source_language: str | None = None,
    target_language: str = "en",
    settings: LocalizationSettings | None = None,
) -> TranscriptionResult:
    settings = settings or LocalizationSettings.from_env()
    provider_name = select_transcription_provider(source_language or "en", _router_config())
    if provider_name == "seamless_m4t":
        provider = SeamlessM4TProvider(SeamlessM4TConfig())
    elif provider_name == "whisper":
        provider = WhisperProvider()
    else:
        if settings.allowed_cloud_processing and os.environ.get("OPENAI_API_KEY"):
            provider = WhisperProvider()
        else:
            return TranscriptionResult(
                language_code=source_language or "en",
                transcript="",
                confidence=0.0,
                segments=[],
                provider="unavailable",
            )

    result = await provider.transcribe(audio_bytes, source_language, target_language)
    if not result.language_code and result.transcript:
        detected = await detect_language(
            result.transcript,
            allow_cloud=settings.allowed_cloud_processing,
        )
        result.language_code = detected.language_code
    return result
