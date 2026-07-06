"""Workspace localization configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


DEFAULT_SUPPORTED_LANGUAGES: tuple[str, ...] = (
    "en-GH",
    "ak-GH",
    "tw-GH",
    "gaa-GH",
    "ee-GH",
    "ha-NG",
    "yo-NG",
    "ig-NG",
    "pcm-NG",
    "wo-SN",
    "bm-ML",
    "sw-KE",
    "sw-TZ",
    "am-ET",
    "om-ET",
    "so-SO",
    "rw-RW",
    "zu-ZA",
    "xh-ZA",
    "st-ZA",
    "tn-BW",
    "sn-ZW",
    "ny-MW",
    "ln-CD",
    "ar-EG",
    "ary-MA",
    "kab-DZ",
)


@dataclass
class LocalizationSettings:
    enabled: bool = True
    workspace_language: str = "en-GH"
    default_output_language: str = "en-GH"
    allowed_cloud_processing: bool = True
    default_voice_output: bool = False
    human_review_below_confidence: float = 0.72
    offline_mode: bool = False
    intent_extraction_enabled: bool = True
    supported_languages: list[str] = field(default_factory=lambda: list(DEFAULT_SUPPORTED_LANGUAGES))

    @classmethod
    def from_env(cls, workspace_id: str = "default") -> LocalizationSettings:
        del workspace_id
        cloud = os.environ.get("KEPRIX_LOCALIZATION_ALLOW_CLOUD", "true").strip().lower()
        offline = os.environ.get("KEPRIX_LOCALIZATION_OFFLINE", "false").strip().lower()
        return cls(
            enabled=os.environ.get("KEPRIX_LOCALIZATION_ENABLED", "true").strip().lower()
            in {"1", "true", "yes", "on"},
            workspace_language=os.environ.get("KEPRIX_LOCALIZATION_WORKSPACE_LANGUAGE", "en-GH"),
            default_output_language=os.environ.get(
                "KEPRIX_LOCALIZATION_DEFAULT_OUTPUT", "en-GH"
            ),
            allowed_cloud_processing=cloud in {"1", "true", "yes", "on"},
            default_voice_output=os.environ.get(
                "KEPRIX_LOCALIZATION_DEFAULT_VOICE", "false"
            ).strip().lower()
            in {"1", "true", "yes", "on"},
            human_review_below_confidence=float(
                os.environ.get("KEPRIX_LOCALIZATION_REVIEW_THRESHOLD", "0.72")
            ),
            offline_mode=offline in {"1", "true", "yes", "on"},
            intent_extraction_enabled=os.environ.get(
                "KEPRIX_INTENT_EXTRACTION_ENABLED", "true"
            ).strip().lower()
            in {"1", "true", "yes", "on"},
        )
