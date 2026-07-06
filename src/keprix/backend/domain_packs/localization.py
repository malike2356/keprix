"""Localization integration for domain packs (Prompt 30)."""

from __future__ import annotations

from typing import Any

from keprix.backend.domain_packs.glossary import glossary_to_localization_payload
from keprix.backend.domain_packs.jurisdiction import compliance_notes_for_jurisdiction
from keprix.backend.domain_packs.schemas import DomainPackManifest, GlossaryTerm


def validate_localization_metadata(pack: DomainPackManifest) -> list[str]:
    errors: list[str] = []
    coverage = pack.localization_coverage or {}
    locales = coverage.get("locales") or []
    if not locales:
        errors.append("localization_coverage.locales is required")
    fallback = str(coverage.get("fallback") or "")
    if not fallback:
        errors.append("localization_coverage.fallback is required")
    elif fallback not in locales:
        errors.append("localization fallback locale must be listed in locales")
    examples = coverage.get("region_examples") or {}
    if not isinstance(examples, dict):
        errors.append("region_examples must be an object")
    return errors


def apply_localization(
    pack: DomainPackManifest,
    *,
    locales: list[str],
    fallback: str,
    localized_glossary: list[dict[str, Any]] | None = None,
    region_examples: dict[str, str] | None = None,
) -> DomainPackManifest:
    pack.localization_coverage = {
        "locales": locales,
        "fallback": fallback,
        "low_resource_fallback": fallback,
        "region_examples": region_examples or {},
        "compliance_notes": {
            jurisdiction: compliance_notes_for_jurisdiction(jurisdiction)
            for jurisdiction in pack.jurisdictions
        },
        "voice_friendly": True,
    }
    if localized_glossary:
        for row in localized_glossary:
            pack.glossary.append(
                GlossaryTerm(
                    term=str(row.get("term") or ""),
                    definition=str(row.get("definition") or ""),
                    locale=str(row.get("locale") or fallback),
                    approved_equivalent=row.get("approved_equivalent"),
                    forbidden_translations=list(row.get("forbidden_translations") or []),
                    voice_friendly=row.get("voice_friendly"),
                )
            )
    return pack


async def sync_glossary_to_localization(pack: DomainPackManifest) -> dict[str, Any]:
    from keprix.backend.localization.glossary import get_glossary_service

    payload = glossary_to_localization_payload(pack)
    saved = get_glossary_service().save(payload)
    return {"glossary_id": saved.get("id"), "entries": len(saved.get("entries") or [])}
