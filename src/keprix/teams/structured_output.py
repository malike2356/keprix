"""Small structured output validator used by team tasks."""

from __future__ import annotations

from typing import Any


class StructuredOutputError(ValueError):
    pass


def validate_structured_output(value: Any, schema: dict[str, Any] | None) -> None:
    if not schema:
        return
    if not isinstance(value, dict):
        raise StructuredOutputError("Structured output must be a dict")
    required = list(schema.get("required") or [])
    properties = dict(schema.get("properties") or {})
    for key in required:
        if key not in value:
            raise StructuredOutputError(f"Missing required output field: {key}")
    for key, definition in properties.items():
        if key not in value:
            continue
        expected = definition.get("type")
        if expected == "string" and not isinstance(value[key], str):
            raise StructuredOutputError(f"Output field {key} must be a string")
        if expected == "number" and not isinstance(value[key], (int, float)):
            raise StructuredOutputError(f"Output field {key} must be a number")
        if expected == "integer" and not isinstance(value[key], int):
            raise StructuredOutputError(f"Output field {key} must be an integer")
        if expected == "array" and not isinstance(value[key], list):
            raise StructuredOutputError(f"Output field {key} must be an array")
        if expected == "object" and not isinstance(value[key], dict):
            raise StructuredOutputError(f"Output field {key} must be an object")
