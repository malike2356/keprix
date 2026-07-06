"""Tests for tool collections."""

from __future__ import annotations

from keprix.code_agent.tool_collection import (
    ToolCollection,
    load_callable_tools,
    load_hub_tool_package,
    load_mcp_collection,
    merge_collections,
)
from pathlib import Path
import json


def test_callable_tool_collection() -> None:
    collection = load_callable_tools({"add": lambda args: (args or {}).get("a", 0) + (args or {}).get("b", 0)})
    assert collection.call("add", {"a": 2, "b": 3}) == 5


def test_mcp_tool_collection_mount() -> None:
    tools = [
        {"name": "read_file", "description": "Read a file", "input_schema": {"type": "object"}},
        {"name": "write_file", "description": "Write a file", "input_schema": {"type": "object"}},
    ]
    collection = load_mcp_collection("filesystem", tools, lambda name, args: {"ok": True, "tool": name})
    assert len(collection.list_tools()) == 2
    assert collection.call("read_file", {"path": "app.py"})["tool"] == "read_file"


def test_merge_collections() -> None:
    from keprix.code_agent.tool_collection import ToolSpec

    a = ToolCollection(name="a")
    a.register(ToolSpec(name="one", description="d1", source="a", handler=lambda args: 1))
    b = ToolCollection(name="b")
    b.register(ToolSpec(name="two", description="d2", source="b", handler=lambda args: 2))
    merged = merge_collections(a, b)
    assert set(merged.tools) == {"one", "two"}


def test_hub_tool_package_load(tmp_path: Path) -> None:
    package_dir = tmp_path / "demo-tools"
    package_dir.mkdir()
    (package_dir / "tool-package.json").write_text(
        json.dumps(
            {
                "name": "demo-tools",
                "tools": [{"name": "ping", "description": "Ping tool", "input_schema": {}}],
            }
        ),
        encoding="utf-8",
    )
    collection = load_hub_tool_package(package_dir)
    assert collection.name == "demo-tools"
    assert "ping" in collection.tools
