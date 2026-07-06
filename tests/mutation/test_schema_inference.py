"""Tests for mutation schema inference (Prompt 150)."""

from __future__ import annotations

from keprix.mutation.schema_inference import infer_schema


def test_infers_str_int_bool_params():
    source = '''
def demo_handler(city: str, limit: int, active: bool):
    """Fetch rows."""
    pass
'''
    result = infer_schema(source, "demo_handler")
    assert not result.errors
    props = result.input_schema["properties"]
    assert props["city"] == {"type": "string"}
    assert props["limit"] == {"type": "integer"}
    assert props["active"] == {"type": "boolean"}
    assert set(result.input_schema["required"]) == {"city", "limit", "active"}


def test_infers_optional_param_not_required():
    source = '''
def demo_handler(city: str, country: str | None = None):
    """Lookup."""
    pass
'''
    result = infer_schema(source, "demo_handler")
    assert "city" in result.input_schema["required"]
    assert "country" not in result.input_schema.get("required", [])


def test_extracts_description_from_docstring():
    source = '''
def demo_handler(city: str):
    """Fetch weather for a city."""
    pass
'''
    result = infer_schema(source, "demo_handler")
    assert result.description == "Fetch weather for a city."


def test_returns_errors_when_function_not_found():
    result = infer_schema("x = 1\n", "missing_fn")
    assert result.errors
    assert "not found" in result.errors[0]


def test_no_exec_during_inference():
    source = "import os\nos.system('echo pwned')\ndef demo_handler(x: str):\n    pass\n"
    result = infer_schema(source, "demo_handler")
    assert result.input_schema["properties"]["x"] == {"type": "string"}
