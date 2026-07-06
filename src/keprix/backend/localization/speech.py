"""Text-to-speech service."""

from __future__ import annotations

import os

from keprix.backend.localization.config import LocalizationSettings
from keprix.backend.localization.preferences import get_preference_service
from keprix.backend.localization.providers.seamless_m4t import SeamlessM4TConfig, SeamlessM4TProvider
from keprix.backend.localization.router import LocalizationConfig, ProviderConfig, select_speech_provider
from keprix.backend.localization.schemas import SpeechSynthesisResult


def _router_config() -> LocalizationConfig:
    sm4t_on = os.environ.get("KEPRIX_LOCALIZATION_SM4T_ENABLED", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return LocalizationConfig(
        seamless_m4t=ProviderConfig(enabled=sm4t_on),
    )


async def synthesize_speech(
    text: str,
    language: str,
    *,
    workspace_id: str = "default",
    user_id: str | None = None,
    channel_supports_audio: bool = True,
    settings: LocalizationSettings | None = None,
) -> SpeechSynthesisResult | None:
    settings = settings or LocalizationSettings.from_env(workspace_id)
    if not channel_supports_audio:
        return None
    if user_id:
        prefs = await get_preference_service().get(workspace_id, user_id, settings)
        if not prefs.get("voice_output_enabled"):
            return None

    provider_name = select_speech_provider(language, _router_config())
    if provider_name == "seamless_m4t":
        provider = SeamlessM4TProvider(SeamlessM4TConfig())
        return await provider.synthesize_speech(text, language)
    if provider_name == "cloud" and settings.allowed_cloud_processing:
        return SpeechSynthesisResult(
            language_code=language,
            voice_id="cloud_default",
            audio_url="",
            transcript=text,
            provider="cloud_unavailable",
        )
    return None
