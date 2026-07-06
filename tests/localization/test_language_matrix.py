"""Tests for cross-provider language matrix and router selection."""

from __future__ import annotations

import pytest

from keprix.backend.localization.providers.language_matrix import (
    bcp47_to_nllb,
    bcp47_to_sm4t,
    nllb_supports,
    sm4t_supports,
    sm4t_supports_s2t,
    sm4t_supports_t2t,
)
from keprix.backend.localization.router import LocalizationConfig, ProviderConfig, select_translation_provider, select_transcription_provider


def test_bcp47_to_sm4t_known_codes() -> None:
    assert bcp47_to_sm4t("ak-GH") == "twi"
    assert bcp47_to_sm4t("ee-GH") == "ewe"
    assert bcp47_to_sm4t("ha-NG") == "hau"


def test_bcp47_to_sm4t_unknown_returns_none() -> None:
    assert bcp47_to_sm4t("xx-XX") is None


def test_bcp47_to_nllb_nzema() -> None:
    assert bcp47_to_nllb("nzi-GH") == "nzi_Latn"


def test_bcp47_to_nllb_unknown_returns_none() -> None:
    assert bcp47_to_nllb("xx-XX") is None


def test_sm4t_supports_s2t_for_twi() -> None:
    assert sm4t_supports_s2t("ak-GH") is True


def test_sm4t_supports_t2t_for_ewe_to_english() -> None:
    assert sm4t_supports_t2t("ee-GH", "en") is True


def test_nllb_supports_nzema_to_english() -> None:
    assert nllb_supports("nzi-GH", "en") is True


def test_sm4t_internal_support_matrix() -> None:
    assert sm4t_supports("twi", "eng", "t2t") is True
    assert sm4t_supports("twi", "eng", "t2s") is True


def test_select_transcription_provider_akan() -> None:
    config = LocalizationConfig(
        seamless_m4t=ProviderConfig(enabled=True),
    )
    assert select_transcription_provider("ak-GH", config) == "seamless_m4t"


def test_select_translation_provider_ewe() -> None:
    config = LocalizationConfig(
        seamless_m4t=ProviderConfig(enabled=True),
    )
    assert select_translation_provider("ee-GH", "en", config) == "seamless_m4t"


def test_select_translation_provider_nzema_uses_nllb() -> None:
    config = LocalizationConfig(
        seamless_m4t=ProviderConfig(enabled=True),
        nllb_200=ProviderConfig(enabled=True),
    )
    assert select_translation_provider("nzi-GH", "en", config) == "nllb_200"


def test_select_translation_falls_back_to_cloud_when_sidecars_disabled() -> None:
    config = LocalizationConfig()
    assert select_translation_provider("ak-GH", "en", config) == "cloud"
