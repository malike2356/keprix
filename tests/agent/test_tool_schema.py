"""Tests for provider-agnostic ToolSchema."""

from __future__ import annotations

from agent.tool_schema import ParameterSchema, ReturnSchema, ToolExample, ToolSchema


def test_to_openai_format():
    schema = ToolSchema(
        name="demo",
        description="Demo tool",
        parameters={
            "q": ParameterSchema(name="q", type="string", description="Query text"),
        },
    )
    payload = schema.to_openai()
    assert payload["type"] == "function"
    assert payload["function"]["name"] == "demo"
    assert payload["function"]["parameters"]["properties"]["q"]["type"] == "string"


def test_to_anthropic_and_google_formats():
    schema = ToolSchema(
        name="demo",
        description="Demo tool",
        parameters={
            "mode": ParameterSchema(
                name="mode",
                type="string",
                description="Run mode",
                enum=["fast", "safe"],
            ),
        },
        returns=ReturnSchema(type="json", description="Result payload"),
    )
    anthropic = schema.to_anthropic()
    assert anthropic["name"] == "demo"
    assert anthropic["input_schema"]["properties"]["mode"]["enum"] == ["fast", "safe"]

    google = schema.to_google()
    assert google["functionDeclarations"][0]["name"] == "demo"


def test_from_openai_function_round_trip():
    function = {
        "name": "todo",
        "description": "Manage todos",
        "parameters": {
            "type": "object",
            "properties": {
                "merge": {
                    "type": "boolean",
                    "description": "Merge mode",
                    "default": False,
                }
            },
            "required": [],
        },
    }
    schema = ToolSchema.from_openai_function(function)
    assert schema.name == "todo"
    assert "merge" in schema.parameters
    assert schema.parameters["merge"].required is False
    assert schema.to_openai()["function"]["name"] == "todo"
