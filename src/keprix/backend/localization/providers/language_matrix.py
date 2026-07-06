"""
Cross-provider language support matrix.

BCP 47 codes are used throughout the public localization API.
This module translates between BCP 47, SeamlessM4T internal codes,
and NLLB-200 flores codes.
"""

from __future__ import annotations

# BCP 47 -> SM4T internal code
_BCP47_TO_SM4T: dict[str, str] = {
    # West Africa
    "ak-GH": "twi",
    "tw-GH": "twi",
    "ee-GH": "ewe",
    "gaa-GH": "gaa",
    "ha-NG": "hau",
    "ha-GH": "hau",
    "yo-NG": "yor",
    "ig-NG": "ibo",
    "dag-GH": "dik",
    "pcm-NG": "pcm",
    "wo-SN": "wol",
    "ff-SN": "fuv",
    "bm-ML": "bam",
    # East Africa
    "sw-KE": "swh",
    "sw-TZ": "swh",
    "am-ET": "amh",
    "om-ET": "gaz",
    "so-SO": "som",
    "rw-RW": "kin",
    # Southern Africa
    "zu-ZA": "zul",
    "xh-ZA": "xho",
    "af-ZA": "afr",
    "st-ZA": "sot",
    "tn-ZA": "tsn",
    "sn-ZW": "sna",
    # North Africa
    "ar-EG": "arz",
    "ar-MA": "ary",
    # European / fallbacks
    "en": "eng",
    "en-GH": "eng",
    "en-NG": "eng",
    "en-KE": "eng",
    "fr-SN": "fra",
    "fr-CI": "fra",
    "fr-ML": "fra",
    "pt-MZ": "por",
    "pt-AO": "por",
    "es": "spa",
    "de": "deu",
    "zh": "cmn",
    "ar": "arb",
    "fr": "fra",
    "en-US": "eng",
    "en-GB": "eng",
}

# Reverse map: SM4T code -> BCP 47 (first registered wins)
_SM4T_TO_BCP47: dict[str, str] = {}
for _bcp, _sm in _BCP47_TO_SM4T.items():
    if _sm not in _SM4T_TO_BCP47:
        _SM4T_TO_BCP47[_sm] = _bcp

# BCP 47 -> NLLB flores code
_BCP47_TO_NLLB: dict[str, str] = {
    # West Africa
    "ak-GH": "twi_Latn",
    "tw-GH": "twi_Latn",
    "ee-GH": "ewe_Latn",
    "gaa-GH": "gaa_Latn",
    "fan-GH": "aka_Latn",
    "nzi-GH": "nzi_Latn",
    "dag-GH": "dik_Latn",
    "ha-NG": "hau_Latn",
    "ha-GH": "hau_Latn",
    "yo-NG": "yor_Latn",
    "ig-NG": "ibo_Latn",
    "pcm-NG": "pcm_Latn",
    "wo-SN": "wol_Latn",
    "ff-SN": "fuv_Latn",
    "bm-ML": "bam_Latn",
    "mos-BF": "mos_Latn",
    # East Africa
    "sw-KE": "swh_Latn",
    "sw-TZ": "swh_Latn",
    "am-ET": "amh_Ethi",
    "om-ET": "gaz_Latn",
    "so-SO": "som_Latn",
    "rw-RW": "kin_Latn",
    "lg-UG": "lug_Latn",
    "lu-KE": "luo_Latn",
    "ki-KE": "kik_Latn",
    # Southern Africa
    "zu-ZA": "zul_Latn",
    "xh-ZA": "xho_Latn",
    "af-ZA": "afr_Latn",
    "st-ZA": "sot_Latn",
    "tn-ZA": "tsn_Latn",
    "sn-ZW": "sna_Latn",
    "ny-MW": "nya_Latn",
    "ln-CD": "lin_Latn",
    # North Africa
    "ar-EG": "arz_Arab",
    "ar-MA": "ary_Arab",
    "ary-MA": "ary_Arab",
    "kab-DZ": "kab_Latn",
    # European / common
    "en": "eng_Latn",
    "en-GH": "eng_Latn",
    "en-NG": "eng_Latn",
    "en-KE": "eng_Latn",
    "en-US": "eng_Latn",
    "en-GB": "eng_Latn",
    "fr": "fra_Latn",
    "fr-SN": "fra_Latn",
    "fr-CI": "fra_Latn",
    "fr-ML": "fra_Latn",
    "pt-MZ": "por_Latn",
    "pt-AO": "por_Latn",
    "ar": "arb_Arab",
    "es": "spa_Latn",
    "de": "deu_Latn",
    "zh": "zho_Hans",
}

# Languages SeamlessM4T supports for text-to-speech.
# Not all transcription languages have TTS support.
_SM4T_T2S_LANGUAGES: frozenset[str] = frozenset({
    "eng", "fra", "deu", "spa", "por", "arb",
    "hau", "yor", "swh", "zul", "som",
    "twi", "ewe", "amh",
})

# All tasks SM4T handles: s2t and t2t cover the full _BCP47_TO_SM4T set.
_SM4T_ALL_CODES: frozenset[str] = frozenset(_SM4T_TO_BCP47.keys())


def bcp47_to_sm4t(code: str) -> str | None:
    """Return the SM4T internal code for a BCP 47 tag, or None if not supported."""
    return _BCP47_TO_SM4T.get(code) or _BCP47_TO_SM4T.get(code.split("-")[0])


def sm4t_to_bcp47(sm4t_code: str) -> str:
    """Return a BCP 47 tag for an SM4T internal code. Falls back to the code itself."""
    return _SM4T_TO_BCP47.get(sm4t_code, sm4t_code)


def bcp47_to_nllb(code: str) -> str | None:
    """Return the NLLB flores code for a BCP 47 tag, or None if not supported."""
    return _BCP47_TO_NLLB.get(code) or _BCP47_TO_NLLB.get(code.split("-")[0])


def sm4t_supports(source: str, target: str, task: str) -> bool:
    """
    Return True if SM4T supports the given (source, target, task) triple.

    task: one of 's2t', 't2t', 't2s', 's2s'.
    source and target are SM4T internal codes (not BCP 47).
    """
    if task == "s2t":
        return source in _SM4T_ALL_CODES
    if task == "t2t":
        return source in _SM4T_ALL_CODES and target in _SM4T_ALL_CODES
    if task == "t2s":
        return target in _SM4T_T2S_LANGUAGES
    if task == "s2s":
        return source in _SM4T_ALL_CODES and target in _SM4T_T2S_LANGUAGES
    return False


def nllb_supports(source: str, target: str) -> bool:
    """Return True if NLLB supports translating between these two BCP 47 codes."""
    return bcp47_to_nllb(source) is not None and bcp47_to_nllb(target) is not None


def sm4t_supports_s2t(bcp47_code: str) -> bool:
    """Convenience wrapper: does SM4T support transcription from this BCP 47 language?"""
    sm4t_code = bcp47_to_sm4t(bcp47_code)
    return sm4t_code is not None and sm4t_code in _SM4T_ALL_CODES


def sm4t_supports_t2t(source_bcp47: str, target_bcp47: str) -> bool:
    """Convenience wrapper: does SM4T support T2T for these BCP 47 codes?"""
    src = bcp47_to_sm4t(source_bcp47)
    tgt = bcp47_to_sm4t(target_bcp47)
    if not src or not tgt:
        return False
    return sm4t_supports(src, tgt, "t2t")


def sm4t_supports_t2s(bcp47_code: str) -> bool:
    """Convenience wrapper: does SM4T support TTS for this BCP 47 language?"""
    sm4t_code = bcp47_to_sm4t(bcp47_code)
    return sm4t_code is not None and sm4t_code in _SM4T_T2S_LANGUAGES
