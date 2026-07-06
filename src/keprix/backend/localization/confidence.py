"""Confidence thresholds and human review decisions."""

from __future__ import annotations

from keprix.backend.localization.catalog import get_catalog_entry
from keprix.backend.localization.config import LocalizationSettings
from keprix.products.loader import get_regulated_domains


def should_require_human_review(
    *,
    settings: LocalizationSettings,
    detection_confidence: float,
    translation_confidence: float,
    glossary_warnings: list[str],
    domain: str | None = None,
    user_disputed: bool = False,
    triggers_external_action: bool = False,
) -> bool:
    if user_disputed or triggers_external_action:
        return True
    if glossary_warnings:
        return True
    threshold = settings.human_review_below_confidence
    if detection_confidence < threshold or translation_confidence < threshold:
        return True
    if domain and domain in get_regulated_domains():
        entry = get_catalog_entry(domain)
        if entry and entry.human_review_default:
            return True
        if detection_confidence < max(threshold, 0.8):
            return True
    return False
