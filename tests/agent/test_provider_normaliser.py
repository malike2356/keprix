"""Tests for provider tool normalisation."""

from __future__ import annotations

import json

from agent.provider_normaliser import ProviderNormaliser, ToolResult
from agent.tool_schema import ParameterSchema, ToolSchema


def _demo_schema() -> ToolSchema:
    return ToolSchema(
        name="search",
        description="Search the web",
        parameters={
            "query": ParameterSchema(name="query", type="string", description="Search query"),
        },
    )


def test_openai_definitions_and_parse():
    normaliser = ProviderNormaliser("openai", [_demo_schema()])
    defs = normaliser.get_tool_definitions()
    assert defs[0]["type"] == "function"
    raw = {
        "id": "call_1",
        "function": {"name": "search", "arguments": json.dumps({"query": "keprix"})},
    }
    call = normaliser.parse_tool_call(raw)
    assert call.name == "search"
    assert json.loads(call.arguments)["query"] == "keprix"


def test_anthropic_definitions_and_result_format():
    normaliser = ProviderNormaliser("anthropic", [_demo_schema()])
    defs = normaliser.get_tool_definitions()
    assert defs[0]["input_schema"]["type"] == "object"
    call = normaliser.parse_tool_call({"id": "tu_1", "name": "search", "input": {"query": "x"}})
    assert call.name == "search"
    result = normaliser.format_tool_result(
        ToolResult(tool_call_id="tu_1", name="search", content="ok")
    )
    assert result["type"] == "tool_result"
    assert result["tool_use_id"] == "tu_1"


def test_google_definitions_and_parse():
    normaliser = ProviderNormaliser("google", [_demo_schema()])
    defs = normaliser.get_tool_definitions()
    assert "functionDeclarations" in defs[0]
    call = normaliser.parse_tool_call(
        {"functionCall": {"name": "search", "args": {"query": "docs"}}}
    )
    assert call.name == "search"
