"""African language catalog (Prompt 27)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class LanguageCatalogEntry:
    code: str
    name: str
    local_name: str | None = None
    regions: list[str] = field(default_factory=list)
    script: str = "Latin"
    direction: str = "ltr"
    text_detection: str = "supported"
    translation: str = "supported"
    speech_to_text: str = "partial"
    text_to_speech: str = "partial"
    fallback_languages: list[str] = field(default_factory=list)
    human_review_default: bool = False
    minimum_confidence: float = 0.65
    dialect_aliases: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "local_name": self.local_name,
            "regions": self.regions,
            "script": self.script,
            "direction": self.direction,
            "text_detection": self.text_detection,
            "translation": self.translation,
            "speech_to_text": self.speech_to_text,
            "text_to_speech": self.text_to_speech,
            "fallback_languages": self.fallback_languages,
            "human_review_default": self.human_review_default,
            "minimum_confidence": self.minimum_confidence,
            "dialect_aliases": self.dialect_aliases,
        }


def _catalog_path() -> Path:
    return Path(__file__).resolve().parent / "catalog.yaml"


def load_catalog() -> list[LanguageCatalogEntry]:
    raw = yaml.safe_load(_catalog_path().read_text(encoding="utf-8")) or []
    return [LanguageCatalogEntry(**item) for item in raw]


def get_catalog_entry(code: str) -> LanguageCatalogEntry | None:
    normalized = code.strip()
    for entry in load_catalog():
        if entry.code == normalized or normalized in entry.dialect_aliases:
            return entry
    prefix = normalized.split("-")[0]
    for entry in load_catalog():
        if entry.code.split("-")[0] == prefix:
            return entry
    return None


def catalog_as_dicts() -> list[dict[str, Any]]:
    return [entry.to_dict() for entry in load_catalog()]
