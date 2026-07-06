"""MCP adapter for kernel plugins."""

from __future__ import annotations

from typing import Any

from keprix.kernel.plugin_contract import KernelPlugin


def plugin_to_mcp_tools(plugin: KernelPlugin) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for function in plugin.functions:
        tools.append(
            {
                "name": f"{plugin.name}.{function.name}",
                "description": function.description,
                "inputSchema": function.input_schema or {"type": "object", "properties": {}},
            }
        )
    return tools


def mcp_tool_to_function_name(tool_name: str) -> tuple[str, str]:
    if "." not in tool_name:
        raise ValueError("MCP tool name must be plugin.function")
    plugin_name, function_name = tool_name.split(".", 1)
    return plugin_name, function_name
