"""A2A adapter for kernel plugins."""

from __future__ import annotations

from typing import Any

from keprix.kernel.plugin_contract import KernelPlugin


def plugin_to_a2a_capabilities(plugin: KernelPlugin) -> dict[str, Any]:
    return {
        "agent_id": plugin.name,
        "version": plugin.version,
        "capabilities": [
            {
                "name": function.name,
                "description": function.description,
                "risk_level": function.risk_level,
                "permissions": function.permissions,
            }
            for function in plugin.functions
        ],
        "documentation": plugin.documentation,
    }


def a2a_task_to_invocation(task_input: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    plugin_name = str(task_input.get("plugin") or task_input.get("agent_id") or "")
    function_name = str(task_input.get("function") or task_input.get("action") or "")
    arguments = dict(task_input.get("arguments") or task_input.get("payload") or {})
    if not plugin_name or not function_name:
        raise ValueError("A2A task input requires plugin and function")
    return plugin_name, function_name, arguments
