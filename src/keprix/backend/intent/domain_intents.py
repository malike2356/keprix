"""Load domain intent schemas from product config (no hardcoded project intents)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from keprix.backend.intent.schemas import EntitySchema, IntentSchema
from keprix.products.loader import list_enabled_products, resolve_config_path


def _entity_from_dict(row: dict[str, Any]) -> EntitySchema:
    return EntitySchema(
        name=str(row["name"]),
        type=str(row.get("type") or "string"),
        required=bool(row.get("required", False)),
        enum_values=[str(item) for item in row["enum_values"]] if row.get("enum_values") else None,
        description=str(row.get("description") or ""),
        example_values=[str(item) for item in row["example_values"]]
        if row.get("example_values")
        else None,
    )


def intent_from_dict(row: dict[str, Any]) -> IntentSchema:
    triggers = row.get("keyword_triggers") or {}
    return IntentSchema(
        name=str(row["name"]),
        description=str(row.get("description") or ""),
        domain=str(row.get("domain") or "generic"),
        entities=[_entity_from_dict(entity) for entity in row.get("entities") or []],
        follow_up_template=str(row.get("follow_up_template") or ""),
        examples=[str(item) for item in row.get("examples") or []] or None,
        keyword_triggers={
            "all": [str(item).lower() for item in triggers.get("all") or []],
            "any": [str(item).lower() for item in triggers.get("any") or []],
        }
        if triggers
        else None,
        heuristic_extractors={
            str(key): str(value) for key, value in (row.get("heuristic_extractors") or {}).items()
        }
        or None,
    )


def load_intents_from_yaml(path: Path) -> list[IntentSchema]:
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows = raw.get("intents") or []
    return [intent_from_dict(row) for row in rows if isinstance(row, dict)]


def load_product_domain_intents() -> list[IntentSchema]:
    schemas: list[IntentSchema] = []
    seen: set[tuple[str, str]] = set()
    for product in list_enabled_products():
        for relative in product.domain_intent_files:
            for schema in load_intents_from_yaml(resolve_config_path(relative)):
                key = (schema.domain, schema.name)
                if key in seen:
                    continue
                seen.add(key)
                schemas.append(schema)
    return schemas
