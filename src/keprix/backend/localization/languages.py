"""Language capability catalog for the localization API."""

from __future__ import annotations

from keprix.backend.localization.providers.language_matrix import (
    bcp47_to_nllb,
    bcp47_to_sm4t,
    sm4t_supports_s2t,
    sm4t_supports_t2s,
    sm4t_supports_t2t,
)
from keprix.backend.localization.router import LocalizationConfig

# Primary African and common language tags exposed in the catalog API.
_CATALOG_CODES: tuple[str, ...] = (
    "ak-GH",
    "tw-GH",
    "ee-GH",
    "gaa-GH",
    "fan-GH",
    "nzi-GH",
    "dag-GH",
    "ha-NG",
    "yo-NG",
    "ig-NG",
    "pcm-NG",
    "sw-KE",
    "am-ET",
    "zu-ZA",
    "en",
    "en-GH",
    "fr-SN",
)


def language_entry(code: str, config: LocalizationConfig) -> dict:
    sm4t_available = config.seamless_m4t.enabled and bcp47_to_sm4t(code) is not None
    nllb_available = config.nllb_200.enabled and bcp47_to_nllb(code) is not None

    transcription = sm4t_available and sm4t_supports_s2t(code)
    translation = (
        (sm4t_available and sm4t_supports_t2t(code, "en"))
        or (nllb_available and bcp47_to_nllb(code) is not None and bcp47_to_nllb("en") is not None)
    )
    speech = sm4t_available and sm4t_supports_t2s(code)

    providers: list[str] = []
    if transcription or (sm4t_available and sm4t_supports_t2t(code, "en")) or speech:
        providers.append("seamless_m4t")
    if nllb_available:
        providers.append("nllb_200")

    return {
        "code": code,
        "transcription": transcription,
        "translation": translation,
        "speech": speech,
        "providers": providers,
    }


def build_language_catalog(config: LocalizationConfig) -> list[dict]:
    return [language_entry(code, config) for code in _CATALOG_CODES]


def config_from_env() -> LocalizationConfig:
    """Build router config from environment flags."""
    from keprix.backend.localization.router import LocalizationConfig, ProviderConfig

    def _enabled(prefix: str) -> bool:
        value = __import__("os").environ.get(prefix, "").strip().lower()
        return value in {"1", "true", "yes", "on"}

    return LocalizationConfig(
        seamless_m4t=ProviderConfig(
            enabled=_enabled("KEPRIX_LOCALIZATION_SM4T_ENABLED"),
            sidecar_url=__import__("os").environ.get(
                "KEPRIX_LOCALIZATION_SM4T_URL", "http://seamless-m4t:7810"
            ),
        ),
        nllb_200=ProviderConfig(
            enabled=_enabled("KEPRIX_LOCALIZATION_NLLB_ENABLED"),
            sidecar_url=__import__("os").environ.get(
                "KEPRIX_LOCALIZATION_NLLB_URL", "http://nllb-200:7811"
            ),
        ),
        whisper=ProviderConfig(enabled=_enabled("KEPRIX_LOCALIZATION_WHISPER_ENABLED")),
    )
