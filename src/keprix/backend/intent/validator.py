"""Entity validation and missing-field detection."""

from __future__ import annotations

import re
from typing import Any

from keprix.backend.intent.registry import IntentRegistry, get_intent_registry
from keprix.backend.intent.schemas import EntitySchema, IntentExtractionResult, IntentSchema


class IntentEntityValidator:
    async def validate_and_fill(
        self,
        result: IntentExtractionResult,
        schemas: list[IntentSchema],
        translated_text: str,
        original_text: str,
        *,
        registry: IntentRegistry | None = None,
    ) -> IntentExtractionResult:
        registry = registry or get_intent_registry()
        schema = registry.find_schema(result.intent, schemas)
        if not schema:
            result.intent = "fallback"
            result.domain = "generic"
            result.confidence = min(result.confidence, 0.3)
            result.entities.setdefault("raw_query", translated_text)
            return result

        result.domain = schema.domain
        normalized = self._normalize_entities(result.entities, schema)
        result.entities = normalized

        for entity_schema in schema.entities:
            value = result.entities.get(entity_schema.name)
            if value is None or value == "":
                recovered = self._recover_from_original(entity_schema, original_text)
                if recovered is not None:
                    result.entities[entity_schema.name] = recovered

        for entity_schema in schema.entities:
            value = result.entities.get(entity_schema.name)
            if value is None or value == "":
                continue
            if entity_schema.type == "enum" and entity_schema.enum_values:
                if str(value) not in entity_schema.enum_values:
                    result.entities[entity_schema.name] = None
            elif entity_schema.type == "number":
                coerced = self._coerce_number(value)
                result.entities[entity_schema.name] = coerced
            elif entity_schema.type == "boolean":
                result.entities[entity_schema.name] = self._coerce_boolean(value)

        result.missing_required = [
            entity.name
            for entity in schema.entities
            if entity.required
            and (
                result.entities.get(entity.name) is None
                or result.entities.get(entity.name) == ""
            )
        ]
        return result

    def _normalize_entities(self, entities: dict[str, Any], schema: IntentSchema) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for entity in schema.entities:
            output[entity.name] = entities.get(entity.name)
        for key, value in entities.items():
            if key not in output:
                output[key] = value
        return output

    def _coerce_number(self, value: Any) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            match = re.search(r"(\d+(?:\.\d+)?)", value)
            if match:
                return float(match.group(1))
        return None

    def _coerce_boolean(self, value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "yes", "1", "y"}:
                return True
            if lowered in {"false", "no", "0", "n"}:
                return False
        return None

    def _recover_from_original(self, entity_schema: EntitySchema, original_text: str) -> Any | None:
        if entity_schema.type != "string" or not original_text.strip():
            return None
        if entity_schema.name == "location_description":
            return original_text.strip()[:120]
        return None


_validator: IntentEntityValidator | None = None


def get_intent_validator() -> IntentEntityValidator:
    global _validator
    if _validator is None:
        _validator = IntentEntityValidator()
    return _validator
