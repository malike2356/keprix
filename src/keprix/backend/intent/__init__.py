"""Structured intent extraction engine (Prompt 48)."""

from keprix.backend.intent.engine import IntentExtractionEngine, get_intent_engine
from keprix.backend.intent.registry import IntentRegistry, get_intent_registry
from keprix.backend.intent.schemas import (
    EntitySchema,
    IntentExtractionResult,
    IntentSchema,
)

__all__ = [
    "EntitySchema",
    "IntentExtractionEngine",
    "IntentExtractionResult",
    "IntentRegistry",
    "IntentSchema",
    "get_intent_engine",
    "get_intent_registry",
]
