"""Tests for intent schema registry."""

from __future__ import annotations

from keprix.backend.intent.registry import get_intent_registry
from keprix.backend.intent.schemas import EntitySchema, IntentSchema
from keprix.backend.intent.skill_loader import get_skill_loader


def test_generic_intents_registered(intent_env) -> None:
    registry = get_intent_registry()
    schema = registry.get_schema("greeting", "generic")
    assert schema is not None
    assert schema.domain == "generic"


def test_domain_pack_visible_when_workspace_loaded(intent_env) -> None:
    get_skill_loader().set_loaded_domains("ws-borehole", ["borehole_drilling"])
    schemas = get_intent_registry().get_schemas_for_workspace("ws-borehole")
    names = {row.name for row in schemas}
    assert "request_drilling_quote" in names
    assert "greeting" in names


def test_domain_pack_hidden_when_not_loaded(intent_env) -> None:
    get_skill_loader().clear_workspace("ws-empty")
    schemas = get_intent_registry().get_schemas_for_workspace("ws-empty")
    names = {row.name for row in schemas}
    assert "request_drilling_quote" not in names


def test_register_and_lookup_custom_intent(intent_env) -> None:
    registry = get_intent_registry()
    registry.register(
        IntentSchema(
            name="custom_intent",
            domain="test_domain",
            description="Test intent",
            entities=[EntitySchema(name="field_a", type="string", required=True)],
            follow_up_template="Need {missing_fields}",
        )
    )
    get_skill_loader().set_loaded_domains("ws-test", ["test_domain"])
    found = registry.get_schema("custom_intent", "test_domain")
    assert found is not None
