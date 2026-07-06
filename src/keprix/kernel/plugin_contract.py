"""Stable plugin contract and registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from keprix.kernel.function_contract import FunctionContract, invoke_function


@dataclass
class KernelPlugin:
    name: str
    version: str
    functions: list[FunctionContract]
    auth_requirements: list[str] = field(default_factory=list)
    risk_level: str = "low"
    capability_tags: list[str] = field(default_factory=list)
    documentation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "functions": [func.to_dict() for func in self.functions],
            "auth_requirements": self.auth_requirements,
            "risk_level": self.risk_level,
            "capability_tags": self.capability_tags,
            "documentation": self.documentation,
        }

    def get_function(self, name: str) -> FunctionContract | None:
        for function in self.functions:
            if function.name == name:
                return function
        return None


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, KernelPlugin] = {}

    def register(self, plugin: KernelPlugin) -> None:
        self._plugins[plugin.name] = plugin

    def get(self, name: str) -> KernelPlugin | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[dict[str, Any]]:
        return [plugin.to_dict() for plugin in self._plugins.values()]

    def all_plugins(self) -> list[KernelPlugin]:
        return list(self._plugins.values())

    def inspect(self, name: str) -> dict[str, Any] | None:
        plugin = self.get(name)
        return plugin.to_dict() if plugin else None

    def invoke(self, plugin_name: str, function_name: str, arguments: dict[str, Any], **context: Any) -> dict[str, Any]:
        plugin = self.get(plugin_name)
        if plugin is None:
            return {"status": "error", "error": f"Unknown plugin: {plugin_name}"}
        function = plugin.get_function(function_name)
        if function is None:
            return {"status": "error", "error": f"Unknown function: {function_name}"}
        return invoke_function(plugin_name, function, arguments, context=context)


_registry: PluginRegistry | None = None


def get_plugin_registry() -> PluginRegistry:
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
        _register_builtin_plugins(_registry)
    return _registry


def _register_builtin_plugins(registry: PluginRegistry) -> None:
    def _greet(args: dict[str, Any], _ctx: dict[str, Any]) -> dict[str, Any]:
        name = str(args.get("name") or "operator")
        return {"message": f"Hello, {name}"}

    registry.register(
        KernelPlugin(
            name="greeting",
            version="1.0.0",
            documentation="Sample kernel plugin for smoke tests.",
            capability_tags=["demo", "text"],
            functions=[
                FunctionContract(
                    name="greet",
                    description="Return a greeting for the provided name",
                    input_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
                    output_schema={"type": "object", "properties": {"message": {"type": "string"}}},
                    permissions=["memory.read"],
                    handler=_greet,
                )
            ],
        )
    )
