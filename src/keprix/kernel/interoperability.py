"""Cross-runtime interoperability bridge."""

from __future__ import annotations

from typing import Any

from keprix.kernel.a2a_adapter import a2a_task_to_invocation, plugin_to_a2a_capabilities
from keprix.kernel.function_contract import FunctionContract, InvocationKind
from keprix.kernel.mcp_adapter import mcp_tool_to_function_name, plugin_to_mcp_tools
from keprix.kernel.plugin_contract import KernelPlugin, get_plugin_registry


class InteropBridge:
    def list_mcp_tools(self) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        for plugin in get_plugin_registry().all_plugins():
            tools.extend(plugin_to_mcp_tools(plugin))
        return tools

    def list_a2a_capabilities(self) -> list[dict[str, Any]]:
        return [plugin_to_a2a_capabilities(plugin) for plugin in get_plugin_registry().all_plugins()]

    def invoke_mcp_tool(self, tool_name: str, arguments: dict[str, Any], **context: Any) -> dict[str, Any]:
        plugin_name, function_name = mcp_tool_to_function_name(tool_name)
        return get_plugin_registry().invoke(plugin_name, function_name, arguments, **context)

    def invoke_a2a_task(self, task_input: dict[str, Any], **context: Any) -> dict[str, Any]:
        plugin_name, function_name, arguments = a2a_task_to_invocation(task_input)
        return get_plugin_registry().invoke(plugin_name, function_name, arguments, **context)

    def from_openai_tool(self, tool_schema: dict[str, Any]) -> FunctionContract:
        function = tool_schema.get("function") or {}
        return FunctionContract(
            name=str(function.get("name") or "tool"),
            description=str(function.get("description") or ""),
            input_schema=function.get("parameters") or {"type": "object", "properties": {}},
            invocation=InvocationKind.HTTP,
            output_type="json",
        )

    def to_sdk_manifest(self, plugin: KernelPlugin) -> dict[str, Any]:
        return {
            "app_id": plugin.name,
            "version": plugin.version,
            "capabilities": plugin.capability_tags,
            "functions": [func.to_dict() for func in plugin.functions],
            "documentation": plugin.documentation,
        }


_bridge: InteropBridge | None = None


def get_interop_bridge() -> InteropBridge:
    global _bridge
    if _bridge is None:
        _bridge = InteropBridge()
    return _bridge
