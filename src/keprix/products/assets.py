"""Load glossaries, playbook localization, and voice categories from product config."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from keprix.backend.playbook.meta import PlaybookLocalizationMeta
from keprix.products.loader import list_enabled_products, resolve_config_path
from keprix.voice_templates.schemas import CategoryCreate


def load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def load_product_glossaries() -> list[dict[str, Any]]:
    glossaries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for product in list_enabled_products():
        for relative in product.glossary_files:
            row = load_yaml_file(resolve_config_path(relative))
            glossary_id = str(row.get("id") or "")
            if not glossary_id or glossary_id in seen:
                continue
            seen.add(glossary_id)
            glossaries.append(row)
    return glossaries


def load_product_playbook_localization() -> dict[str, PlaybookLocalizationMeta]:
    rows: dict[str, PlaybookLocalizationMeta] = {}
    for product in list_enabled_products():
        for relative in product.playbook_localization_files:
            data = load_yaml_file(resolve_config_path(relative))
            if not data:
                continue
            meta = PlaybookLocalizationMeta.from_metadata(data)
            rows[meta.playbook_id] = meta
    return rows


def load_product_voice_categories() -> list[CategoryCreate]:
    categories: list[CategoryCreate] = []
    for product in list_enabled_products():
        for relative in product.voice_category_files:
            data = load_yaml_file(resolve_config_path(relative))
            for row in data.get("categories") or []:
                if not isinstance(row, dict):
                    continue
                categories.append(
                    CategoryCreate(
                        id=str(row["id"]),
                        label=str(row.get("label") or row["id"]),
                        description=str(row.get("description") or ""),
                        domain=str(row.get("domain") or "generic"),
                        is_dynamic=bool(row.get("is_dynamic", False)),
                        dynamic_placeholder=str(row.get("dynamic_placeholder") or ""),
                        sort_order=int(row.get("sort_order") or 0),
                    )
                )
    return categories
