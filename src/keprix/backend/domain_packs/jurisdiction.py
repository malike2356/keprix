"""Jurisdiction tagging for domain packs (Prompt 30)."""

from __future__ import annotations

from keprix.backend.domain_packs.schemas import HIGH_STAKES_DOMAINS, REGULATED_JURISDICTION_TAGS, DomainPackManifest


def is_regulated_domain(domain_name: str) -> bool:
    return domain_name.lower() in HIGH_STAKES_DOMAINS


def validate_jurisdictions(pack: DomainPackManifest) -> list[str]:
    errors: list[str] = []
    if not pack.jurisdictions:
        if is_regulated_domain(pack.domain_name):
            errors.append("regulated domain requires at least one jurisdiction tag")
        return errors
    for tag in pack.jurisdictions:
        if not tag or not str(tag).strip():
            errors.append("jurisdiction tags cannot be empty")
        elif tag.upper() not in REGULATED_JURISDICTION_TAGS and len(tag) < 2:
            errors.append(f"jurisdiction tag too short: {tag}")
    return errors


def tag_source_jurisdiction(source: dict, jurisdiction: str | None) -> dict:
    row = dict(source)
    if jurisdiction:
        row["jurisdiction"] = jurisdiction.upper()
    return row


def compliance_notes_for_jurisdiction(jurisdiction: str) -> str:
    notes = {
        "GH": "Ghana data protection and sector regulators may apply to customer records.",
        "EU": "GDPR and sector-specific EU regulations may apply.",
        "UK": "UK GDPR and sector regulators may apply.",
        "US": "Federal and state regulations may apply depending on use case.",
    }
    return notes.get(jurisdiction.upper(), "Verify local compliance requirements before production use.")
