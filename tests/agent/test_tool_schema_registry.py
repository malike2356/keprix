"""Registry-wide ToolSchema coverage."""

from __future__ import annotations

from tools.registry import discover_builtin_tools, registry


def test_all_registered_tools_have_tool_schemas():
    discover_builtin_tools()
    tool_names = sorted(registry.get_tool_to_toolset_map().keys())
    assert len(tool_names) >= 60

    schemas = registry.get_tool_schemas(tool_names, quiet=True)
    assert len(schemas) == len(tool_names)

    for schema in schemas:
        assert schema.name
        assert schema.description
        openai = schema.to_openai()
        anthropic = schema.to_anthropic()
        google = schema.to_google()
        assert openai["function"]["name"] == schema.name
        assert anthropic["name"] == schema.name
        assert google["functionDeclarations"][0]["name"] == schema.name
