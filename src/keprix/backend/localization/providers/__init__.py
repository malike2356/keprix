"""Localization provider adapters."""

from keprix.backend.localization.providers.base import LanguagePairUnsupported, LocalizationProvider
from keprix.backend.localization.providers.language_matrix import (
    bcp47_to_nllb,
    bcp47_to_sm4t,
    nllb_supports,
    sm4t_supports,
    sm4t_supports_s2t,
    sm4t_supports_t2s,
    sm4t_supports_t2t,
    sm4t_to_bcp47,
)
from keprix.backend.localization.providers.nllb_200 import NLLB200Config, NLLB200Provider
from keprix.backend.localization.providers.seamless_m4t import (
    SeamlessM4TConfig,
    SeamlessM4TProvider,
    protect_terms,
    restore_terms,
)

__all__ = [
    "LanguagePairUnsupported",
    "LocalizationProvider",
    "NLLB200Config",
    "NLLB200Provider",
    "SeamlessM4TConfig",
    "SeamlessM4TProvider",
    "bcp47_to_nllb",
    "bcp47_to_sm4t",
    "nllb_supports",
    "protect_terms",
    "restore_terms",
    "sm4t_supports",
    "sm4t_supports_s2t",
    "sm4t_supports_t2s",
    "sm4t_supports_t2t",
    "sm4t_to_bcp47",
]
