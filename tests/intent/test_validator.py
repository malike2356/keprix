"""Tests for entity validation."""

from __future__ import annotations

import pytest

from keprix.backend.intent.registry import get_intent_registry
from keprix.backend.intent.schemas import EntitySchema, IntentExtractionResult, IntentSchema
from keprix.backend.intent.validator import IntentEntityValidator


@pytest.mark.asyncio
async def test_invalid_enum_becomes_missing_required(intent_env) -> None:
    registry = get_intent_registry()
    schema = IntentSchema(
        name="quote_test",
        domain="test_domain",
        description="Quote test",
        entities=[
            EntitySchema(
                name="casing_type",
                type="enum",
                required=True,
                enum_values=["PVC", "steel", "unknown"],
            ),
        ],
        follow_up_template="Need {missing_fields}",
    )
    registry.register(schema)

    result = IntentExtractionResult(
        intent="quote_test",
        confidence=0.9,
        original_language="en-GH",
        domain="test_domain",
        entities={"casing_type": "concrete"},
    )
    validator = IntentEntityValidator()
    validated = await validator.validate_and_fill(
        result,
        [schema],
        "concrete casing",
        "concrete casing",
        registry=registry,
    )
    assert validated.entities["casing_type"] is None
    assert "casing_type" in validated.missing_required


@pytest.mark.asyncio
async def test_unknown_intent_falls_back(intent_env) -> None:
    result = IntentExtractionResult(
        intent="does_not_exist",
        confidence=0.9,
        original_language="en-GH",
        entities={},
    )
    validator = IntentEntityValidator()
    validated = await validator.validate_and_fill(result, [], "hello", "hello")
    assert validated.intent == "fallback"
    assert validated.confidence <= 0.3
