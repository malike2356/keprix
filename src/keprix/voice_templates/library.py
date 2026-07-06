"""Template lookup with workspace and language fallback resolution."""

from __future__ import annotations

from typing import Any

from keprix.voice_templates.schemas import CategoryCreate
from keprix.voice_templates.store import TemplateRecord, VoiceTemplateStore, get_voice_template_store


class VoiceTemplateLibrary:
    def __init__(self, store: VoiceTemplateStore | None = None) -> None:
        self._store = store or get_voice_template_store()

    def has_templates(self, language_code: str) -> bool:
        return self._get_approved_count(language_code) > 0

    def _get_approved_count(self, language_code: str) -> int:
        return self._store.approved_count_for_language(language_code)

    async def get_template(
        self,
        category_id: str,
        language_code: str,
        workspace_id: str | None = None,
    ) -> TemplateRecord | None:
        lang = language_code.lower()
        template = self._store.find_approved(category_id, lang, workspace_id)
        if template:
            return template
        template = self._store.find_approved(category_id, lang, None)
        if template:
            return template
        fallback = self._store.language_fallbacks.get(lang)
        if fallback and fallback != lang:
            return await self.get_template(category_id, fallback, workspace_id)
        return None

    async def get_languages_with_coverage(self) -> dict[str, dict[str, Any]]:
        total = len([c for c in self._store.list_categories() if c.domain == "generic"])
        if total == 0:
            total = len(self._store.list_categories())
        languages: dict[str, set[str]] = {}
        for record in self._store.templates.values():
            if record.status != "approved":
                continue
            languages.setdefault(record.language_code, set()).add(record.category_id)
        report: dict[str, dict[str, Any]] = {}
        for lang, covered in sorted(languages.items()):
            count = len(covered)
            report[lang] = {
                "total_categories": total,
                "covered_categories": count,
                "coverage_pct": round((count / total) * 100, 1) if total else 0.0,
            }
        return report

    async def increment_play_count(self, template_id: str) -> None:
        self._store.increment_play_count(template_id)

    def is_dynamic_category(self, category_id: str) -> bool:
        return self._store.is_dynamic_category(category_id)

    def list_categories(self, domain: str | None = None) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._store.list_categories(domain=domain)]

    def register_category(self, body: CategoryCreate) -> dict[str, Any]:
        return self._store.register_category(body).to_dict()


_library: VoiceTemplateLibrary | None = None


def get_template_library() -> VoiceTemplateLibrary:
    global _library
    if _library is None:
        _library = VoiceTemplateLibrary()
    return _library


def reset_template_library() -> None:
    global _library
    _library = None


def register_domain_category(body: CategoryCreate) -> dict[str, Any]:
    """Register a domain-specific category (called by domain packs at load time)."""
    return get_template_library().register_category(body)
