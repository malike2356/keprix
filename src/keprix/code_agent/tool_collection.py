"""Unified tool collections for code agents."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class ToolSpec:
    name: str
    description: str
    source: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    handler: Callable[[dict[str, Any]], Any] | None = None


@dataclass
class ToolCollection:
    name: str
    tools: dict[str, ToolSpec] = field(default_factory=dict)

    def register(self, spec: ToolSpec) -> None:
        self.tools[spec.name] = spec

    def call(self, name: str, args: dict[str, Any] | None = None) -> Any:
        spec = self.tools.get(name)
        if spec is None:
            raise KeyError(f"tool not found: {name}")
        if spec.handler is None:
            raise RuntimeError(f"tool has no handler: {name}")
        return spec.handler(args or {})

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": spec.name,
                "description": spec.description,
                "source": spec.source,
                "input_schema": spec.input_schema,
            }
            for spec in self.tools.values()
        ]


def load_native_tools() -> ToolCollection:
    collection = ToolCollection(name="native")
    try:
        from keprix.tools.registry import registry

        for name, entry in registry._tools.items():
            collection.register(
                ToolSpec(
                    name=name,
                    description=getattr(entry, "description", "") or "",
                    source="native",
                    input_schema=getattr(entry, "input_schema", {}) or {},
                    handler=lambda args, tool_name=name: registry.dispatch(tool_name, args),
                )
            )
    except Exception:
        pass
    return collection


def load_callable_tools(callables: dict[str, Callable[[dict[str, Any]], Any]]) -> ToolCollection:
    collection = ToolCollection(name="callable")
    for name, handler in callables.items():
        collection.register(
            ToolSpec(
                name=name,
                description=f"Callable adapter for {name}",
                source="callable",
                handler=handler,
            )
        )
    return collection


def load_mcp_collection(server_name: str, tools: list[dict[str, Any]], caller: Callable[[str, dict[str, Any]], Any]) -> ToolCollection:
    collection = ToolCollection(name=f"mcp-{server_name}")
    for tool in tools:
        tool_name = tool["name"]

        def _handler(args: dict[str, Any], name: str = tool_name) -> Any:
            return caller(name, args)

        collection.register(
            ToolSpec(
                name=tool_name,
                description=tool.get("description", ""),
                source=f"mcp:{server_name}",
                input_schema=tool.get("input_schema", {}),
                handler=_handler,
            )
        )
    return collection


def load_hub_tool_package(package_dir: Path) -> ToolCollection:
    manifest_path = package_dir / "tool-package.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"missing tool-package.json in {package_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    collection = ToolCollection(name=manifest.get("name", package_dir.name))
    for tool in manifest.get("tools", []):
        collection.register(
            ToolSpec(
                name=tool["name"],
                description=tool.get("description", ""),
                source="hub",
                input_schema=tool.get("input_schema", {}),
            )
        )
    return collection


def load_remote_tools(endpoint: str, tools: list[dict[str, Any]], caller: Callable[[str, dict[str, Any]], Any]) -> ToolCollection:
    collection = ToolCollection(name=f"remote:{endpoint}")
    for tool in tools:
        tool_name = tool["name"]

        def _handler(args: dict[str, Any], name: str = tool_name) -> Any:
            return caller(name, args)

        collection.register(
            ToolSpec(
                name=tool_name,
                description=tool.get("description", ""),
                source=f"remote:{endpoint}",
                input_schema=tool.get("input_schema", {}),
                handler=_handler,
            )
        )
    return collection


def load_adapter_tools(*, dry_run: bool = False, approved: bool = False) -> ToolCollection:
    """Expose Prompt 56 adapter registry handlers to the agent runtime."""
    from keprix.backend.tools.adapters.registry import ALL_ADAPTERS, run_adapter

    collection = ToolCollection(name="adapters")

    async def _invoke(adapter_name: str, args: dict[str, Any]) -> dict[str, Any]:
        action = str(args.get("action") or "search")
        params = dict(args.get("params") or args)
        params.pop("action", None)
        result = await run_adapter(
            adapter_name,
            action,
            params,
            dry_run=bool(args.get("dry_run", dry_run)),
            approved=bool(args.get("approved", approved)),
        )
        return result.to_dict()

    for adapter in ALL_ADAPTERS:
        name = f"adapter.{adapter.category}.{adapter.name}"

        def _handler(args: dict[str, Any], adapter_name: str = adapter.name) -> Any:
            import asyncio

            return asyncio.run(_invoke(adapter_name, args))

        collection.register(
            ToolSpec(
                name=name,
                description=f"{adapter.category} adapter: {adapter.name}",
                source=f"adapter:{adapter.category}",
                input_schema={
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "params": {"type": "object"},
                        "dry_run": {"type": "boolean"},
                        "approved": {"type": "boolean"},
                    },
                },
                handler=_handler,
            )
        )
    return collection


def merge_collections(*collections: ToolCollection) -> ToolCollection:
    merged = ToolCollection(name="merged")
    for collection in collections:
        for spec in collection.tools.values():
            merged.register(spec)
    return merged
