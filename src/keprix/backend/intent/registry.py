"""Intent schema registration and lookup."""

from __future__ import annotations

from keprix.backend.intent.domain_intents import load_product_domain_intents
from keprix.backend.intent.generic_intents import GENERIC_INTENTS
from keprix.backend.intent.schemas import IntentSchema
from keprix.backend.intent.skill_loader import get_skill_loader


class IntentRegistry:
    """Holds all registered intent schemas for this Keprix instance."""

    def __init__(self) -> None:
        self._schemas: dict[str, list[IntentSchema]] = {}
        for schema in GENERIC_INTENTS:
            self.register(schema)
        for schema in load_product_domain_intents():
            self.register(schema)

    def register(self, schema: IntentSchema) -> None:
        domain = schema.domain
        bucket = self._schemas.setdefault(domain, [])
        bucket[:] = [row for row in bucket if row.name != schema.name]
        bucket.append(schema)

    def unregister(self, name: str, *, domain: str) -> None:
        bucket = self._schemas.get(domain, [])
        self._schemas[domain] = [row for row in bucket if row.name != name]

    def get_schemas_for_workspace(self, workspace_id: str) -> list[IntentSchema]:
        loaded_domains = get_skill_loader().get_loaded_domains(workspace_id)
        schemas = list(self._schemas.get("generic", []))
        for domain in loaded_domains:
            schemas.extend(self._schemas.get(domain, []))
        return schemas

    def get_schema(self, name: str, domain: str = "generic") -> IntentSchema | None:
        return next((row for row in self._schemas.get(domain, []) if row.name == name), None)

    def find_schema(self, name: str, schemas: list[IntentSchema]) -> IntentSchema | None:
        return next((row for row in schemas if row.name == name), None)

    def list_domains(self) -> list[str]:
        return sorted(self._schemas.keys())

    def list_schemas(self, *, domain: str | None = None) -> list[IntentSchema]:
        if domain:
            return list(self._schemas.get(domain, []))
        rows: list[IntentSchema] = []
        for bucket in self._schemas.values():
            rows.extend(bucket)
        return rows


_intent_registry: IntentRegistry | None = None


def get_intent_registry() -> IntentRegistry:
    global _intent_registry
    if _intent_registry is None:
        _intent_registry = IntentRegistry()
    return _intent_registry


def reset_intent_registry() -> IntentRegistry:
    global _intent_registry
    _intent_registry = IntentRegistry()
    return _intent_registry
