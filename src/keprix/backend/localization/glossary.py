"""Domain glossary service."""

from __future__ import annotations

import re
from typing import Any

from keprix.backend.localization.store import get_localization_store
from keprix.products.assets import load_product_glossaries


class GlossaryService:
    def __init__(self) -> None:
        self._store = get_localization_store()
        self._ensure_product_glossaries()

    def _ensure_product_glossaries(self) -> None:
        for glossary in load_product_glossaries():
            glossary_id = str(glossary.get("id") or "")
            if glossary_id and self._store.get_glossary(glossary_id) is None:
                self._store.save_glossary(glossary)

    def get(self, glossary_id: str) -> dict[str, Any] | None:
        return self._store.get_glossary(glossary_id)

    def list_glossaries(self) -> list[dict[str, Any]]:
        return self._store.list_glossaries()

    def save(self, glossary: dict[str, Any]) -> dict[str, Any]:
        return self._store.save_glossary(glossary)

    async def upsert_term(
        self,
        *,
        domain: str,
        source_language: str,
        source_term: str,
        translated_term: str,
        workspace_id: str = "default",
        source: str = "operator_correction",
        glossary_id: str | None = None,
    ) -> dict[str, Any]:
        del workspace_id
        glossary_key = glossary_id or f"{domain}_v1"
        glossary = self.get(glossary_key) or {
            "id": glossary_key,
            "domain": domain,
            "entries": [],
        }
        entries = list(glossary.get("entries") or [])
        existing = next(
            (entry for entry in entries if str(entry.get("term") or "").lower() == source_term.lower()),
            None,
        )
        payload = {
            "term": source_term,
            "approved_equivalent": translated_term,
            "notes": f"Added via {source} ({source_language})",
            "forbidden_translations": [],
        }
        if existing:
            existing.update(payload)
        else:
            entries.append(payload)
        glossary["entries"] = entries
        return self.save(glossary)

    def protected_terms(self, glossary_id: str | None) -> list[str]:
        if not glossary_id:
            return []
        glossary = self.get(glossary_id)
        if glossary is None:
            return []
        terms: list[str] = []
        for entry in glossary.get("entries") or []:
            term = str(entry.get("term") or "").strip()
            approved = str(entry.get("approved_equivalent") or "").strip()
            if term:
                terms.append(term)
            if approved and approved.lower() != term.lower():
                terms.append(approved)
        return terms

    def validate_translation(
        self,
        translated_text: str,
        glossary_id: str | None,
    ) -> tuple[list[str], list[str]]:
        warnings: list[str] = []
        matches: list[str] = []
        if not glossary_id:
            return matches, warnings
        glossary = self.get(glossary_id)
        if glossary is None:
            return matches, warnings
        lowered = translated_text.lower()
        for entry in glossary.get("entries") or []:
            term = str(entry.get("term") or "")
            approved = str(entry.get("approved_equivalent") or "")
            forbidden = [str(item).lower() for item in entry.get("forbidden_translations") or []]
            if term and term.lower() in lowered:
                matches.append(term)
            for bad in forbidden:
                if bad and bad in lowered:
                    warnings.append(
                        f"Forbidden translation for '{term}': found '{bad}' in output"
                    )
            if approved and approved.lower() not in lowered and term.lower() in lowered:
                warnings.append(f"Protected term '{term}' may need approved equivalent '{approved}'")
        return matches, warnings

    def check_yield_test(self, translated_text: str) -> bool:
        """Return True when yield test meaning is preserved (acceptance test helper)."""
        lowered = translated_text.lower()
        if "crop yield" in lowered or "harvest yield" in lowered:
            return False
        return "yield test" in lowered or "water output" in lowered or "borehole" in lowered


_glossary_service: GlossaryService | None = None


def get_glossary_service() -> GlossaryService:
    global _glossary_service
    if _glossary_service is None:
        _glossary_service = GlossaryService()
    return _glossary_service


def reset_glossary_service() -> None:
    global _glossary_service
    _glossary_service = None
