"""Typed models for structured intent extraction."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EntitySchema(BaseModel):
    name: str
    type: str
    required: bool = False
    enum_values: list[str] | None = None
    description: str = ""
    example_values: list[str] | None = None


class IntentSchema(BaseModel):
    name: str
    description: str
    domain: str = "generic"
    entities: list[EntitySchema] = Field(default_factory=list)
    follow_up_template: str = ""
    examples: list[str] | None = None
    keyword_triggers: dict[str, list[str]] | None = None
    heuristic_extractors: dict[str, str] | None = None


class IntentExtractionResult(BaseModel):
    intent: str
    confidence: float = Field(ge=0.0, le=1.0)
    original_language: str
    domain: str = "generic"
    entities: dict[str, Any] = Field(default_factory=dict)
    missing_required: list[str] = Field(default_factory=list)
    follow_up_prompt: str | None = None
    extraction_notes: str | None = None


EXTRACTION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "intent": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "domain": {"type": "string"},
        "entities": {"type": "object"},
        "extraction_notes": {"type": ["string", "null"]},
    },
    "required": ["intent", "confidence", "entities"],
}
