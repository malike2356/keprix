"""Playbook localization metadata model (no product config imports)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlaybookLocalizationMeta:
    playbook_id: str
    domain: str = "generic"
    workspace_language: str = "en-GH"
    supported_input_languages: list[str] = field(default_factory=list)
    default_output_mode: str = "text"
    glossary_id: str | None = None
    human_review_below_confidence: float = 0.72
    bilingual_replies: bool = False

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any]) -> PlaybookLocalizationMeta:
        return cls(
            playbook_id=str(metadata.get("id") or metadata.get("playbook_id") or "unknown"),
            domain=str(metadata.get("domain") or "generic"),
            workspace_language=str(metadata.get("workspace_language") or "en-GH"),
            supported_input_languages=[
                str(code) for code in metadata.get("supported_input_languages") or []
            ],
            default_output_mode=str(metadata.get("default_output_mode") or "text"),
            glossary_id=str(metadata["glossary_id"]) if metadata.get("glossary_id") else None,
            human_review_below_confidence=float(
                metadata.get("human_review_below_confidence") or 0.72
            ),
            bilingual_replies=bool(metadata.get("bilingual_replies")),
        )

    def supports_language(self, language_code: str) -> bool:
        if not self.supported_input_languages:
            return True
        prefix = language_code.split("-")[0]
        return language_code in self.supported_input_languages or prefix in {
            code.split("-")[0] for code in self.supported_input_languages
        }

    def review_threshold(self) -> float:
        return self.human_review_below_confidence
