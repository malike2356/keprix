"""
Localization provider router.

Selects the best provider for each transcription, translation, and speech
synthesis request. African languages are routed to SeamlessM4T or NLLB-200
before falling through to cloud providers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from keprix.backend.localization.providers.language_matrix import (
    nllb_supports,
    sm4t_supports_s2t,
    sm4t_supports_t2t,
    sm4t_supports_t2s,
)

logger = logging.getLogger(__name__)

# BCP 47 prefix set for languages where SM4T/NLLB should be tried first.
AFRICAN_LANGUAGE_PREFIXES: frozenset[str] = frozenset({
    "ak", "tw", "ee", "gaa", "fan", "nzi", "dag", "ha", "yo", "ig",
    "pcm", "wo", "ff", "bm", "mos", "sw", "am", "om", "so", "rw",
    "lg", "lu", "ki", "zu", "xh", "af", "st", "tn", "sn", "ny",
    "ln", "ar", "ary", "kab",
})


@dataclass
class ProviderConfig:
    enabled: bool = False
    sidecar_url: str = ""


@dataclass
class LocalizationConfig:
    seamless_m4t: ProviderConfig = field(default_factory=lambda: ProviderConfig(enabled=False))
    nllb_200: ProviderConfig = field(default_factory=lambda: ProviderConfig(enabled=False))
    whisper: ProviderConfig = field(default_factory=lambda: ProviderConfig(enabled=False))
    cloud_provider: str = "openai"


def _is_african(language_code: str) -> bool:
    return language_code.split("-")[0].lower() in AFRICAN_LANGUAGE_PREFIXES


def _voice_template_has(language: str) -> bool:
    """Stub: returns True when Prompt 49 voice template library covers this language."""
    return False


def select_transcription_provider(source_language: str, config: LocalizationConfig) -> str:
    """
    Choose the transcription provider for the given source language.

    Priority: SeamlessM4T (African), Whisper, cloud.
    Logs a warning and falls back to cloud when preferred providers are down.
    """
    if _is_african(source_language):
        if config.seamless_m4t.enabled and sm4t_supports_s2t(source_language):
            return "seamless_m4t"
        logger.warning(
            "African language %s: SM4T not available, falling back to cloud transcription",
            source_language,
        )
    if config.whisper.enabled:
        return "whisper"
    return "cloud"


def select_translation_provider(source: str, target: str, config: LocalizationConfig) -> str:
    """
    Choose the translation provider for the given language pair.

    Priority: SeamlessM4T (if it supports T2T), NLLB-200, cloud.
    Falls back to cloud and logs a warning when preferred providers are unavailable.
    """
    if _is_african(source) or _is_african(target):
        if config.seamless_m4t.enabled and sm4t_supports_t2t(source, target):
            return "seamless_m4t"
        if config.nllb_200.enabled and nllb_supports(source, target):
            return "nllb_200"
        logger.warning(
            "African language pair (%s -> %s): SM4T/NLLB not available, "
            "falling back to cloud translation",
            source,
            target,
        )
    return "cloud"


def select_speech_provider(language: str, config: LocalizationConfig) -> str:
    """
    Choose the speech synthesis provider for the given language.

    Priority: voice templates (Prompt 49), SeamlessM4T, cloud.
    """
    if _voice_template_has(language):
        return "voice_templates"
    if _is_african(language):
        if config.seamless_m4t.enabled and sm4t_supports_t2s(language):
            return "seamless_m4t"
        logger.warning(
            "African language %s: SM4T TTS not available, falling back to cloud speech",
            language,
        )
    return "cloud"
