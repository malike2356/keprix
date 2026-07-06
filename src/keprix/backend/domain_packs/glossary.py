"""Glossary helpers for domain packs (Prompt 30)."""

from __future__ import annotations

from keprix.backend.domain_packs.schemas import DomainPackManifest, GlossaryTerm


def validate_glossary(pack: DomainPackManifest) -> list[str]:
    errors: list[str] = []
    seen: set[tuple[str, str]] = set()
    for index, term in enumerate(pack.glossary, start=1):
        if not term.term.strip():
            errors.append(f"glossary term {index} missing term")
        if not term.definition.strip():
            errors.append(f"glossary term {index} missing definition")
        key = (term.term.lower(), term.locale.lower())
        if key in seen:
            errors.append(f"duplicate glossary term: {term.term} ({term.locale})")
        seen.add(key)
    return errors


def preserve_glossary_terms(existing: list[GlossaryTerm], incoming: list[GlossaryTerm]) -> list[GlossaryTerm]:
    merged: dict[tuple[str, str], GlossaryTerm] = {}
    for term in existing:
        merged[(term.term.lower(), term.locale.lower())] = term
    for term in incoming:
        key = (term.term.lower(), term.locale.lower())
        if key not in merged:
            merged[key] = term
    return sorted(merged.values(), key=lambda row: (row.locale, row.term.lower()))


def glossary_to_localization_payload(pack: DomainPackManifest) -> dict:
    return {
        "id": f"{pack.domain_name}_v1",
        "domain": pack.domain_name,
        "entries": [
            {
                "term": term.term,
                "approved_equivalent": term.approved_equivalent or term.definition,
                "notes": term.definition,
                "forbidden_translations": term.forbidden_translations,
            }
            for term in pack.glossary
        ],
    }
