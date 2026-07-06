"""Translation orchestration service."""

from __future__ import annotations

import os
from typing import Any

from keprix.backend.localization.config import LocalizationSettings
from keprix.backend.localization.glossary import get_glossary_service
from keprix.backend.localization.providers.cloud import CloudTranslationProvider
from keprix.backend.localization.providers.nllb_200 import NLLB200Config, NLLB200Provider
from keprix.backend.localization.providers.seamless_m4t import SeamlessM4TConfig, SeamlessM4TProvider
from keprix.backend.localization.router import LocalizationConfig, ProviderConfig, select_translation_provider
from keprix.backend.localization.schemas import TranslationRequest, TranslationResult
from keprix.backend.localization.translation_cache import translation_cache_override


def _router_config(settings: LocalizationSettings) -> LocalizationConfig:
    sm4t_on = os.environ.get("KEPRIX_LOCALIZATION_SM4T_ENABLED", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    nllb_on = os.environ.get("KEPRIX_LOCALIZATION_NLLB_ENABLED", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return LocalizationConfig(
        seamless_m4t=ProviderConfig(enabled=sm4t_on),
        nllb_200=ProviderConfig(enabled=nllb_on),
        whisper=ProviderConfig(enabled=bool(os.environ.get("OPENAI_API_KEY"))),
    )


async def _provider_instance(name: str, settings: LocalizationSettings) -> Any:
    if name == "seamless_m4t":
        return SeamlessM4TProvider(SeamlessM4TConfig())
    if name == "nllb_200":
        return NLLB200Provider(NLLB200Config())
    return CloudTranslationProvider(allow_cloud=settings.allowed_cloud_processing and not settings.offline_mode)


class TranslationService:
    def __init__(self, settings: LocalizationSettings | None = None) -> None:
        self.settings = settings or LocalizationSettings.from_env()

    async def translate(self, request: TranslationRequest) -> TranslationResult:
        source = request.source_language or self.settings.workspace_language
        target = request.target_language

        override = await translation_cache_override.get_override(
            request.workspace_id, source, target, request.text
        )
        if override:
            return TranslationResult(
                source_language=source,
                target_language=target,
                source_text=request.text,
                translated_text=override,
                confidence=1.0,
                glossary_matches=[],
                warnings=[],
                provider="override_cache",
            )

        if source.split("-")[0] == target.split("-")[0]:
            return TranslationResult(
                source_language=source,
                target_language=target,
                source_text=request.text,
                translated_text=request.text,
                confidence=1.0,
                glossary_matches=[],
                warnings=[],
                provider="passthrough",
            )

        glossary = get_glossary_service()
        preserve = list(request.preserve_terms)
        preserve.extend(glossary.protected_terms(request.glossary_id))

        provider_name = select_translation_provider(source, target, _router_config(self.settings))
        provider = await _provider_instance(provider_name, self.settings)
        result = await provider.translate(
            request.text,
            source,
            target,
            preserve_terms=preserve,
        )

        matches, warnings = glossary.validate_translation(result.translated_text, request.glossary_id)
        result.glossary_matches = matches
        result.warnings.extend(warnings)
        return result


async def translate_text(
    *,
    workspace_id: str,
    text: str,
    source_language: str | None,
    target_language: str,
    glossary_id: str | None = None,
    preserve_terms: list[str] | None = None,
    user_id: str | None = None,
) -> TranslationResult:
    service = TranslationService()
    request = TranslationRequest(
        workspace_id=workspace_id,
        text=text,
        source_language=source_language,
        target_language=target_language,
        glossary_id=glossary_id,
        preserve_terms=list(preserve_terms or []),
        user_id=user_id,
    )
    return await service.translate(request)
