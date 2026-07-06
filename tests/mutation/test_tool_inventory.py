"""Tests for runtime tool inventory (Prompt 139)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from keprix.agent.keprix.store import GeneratedToolStore
from keprix.agent.keprix.tool_inventory import list_runtime_tool_names


@pytest.fixture(autouse=True)
def reset_inventory_warnings():
    import keprix.agent.keprix.tool_inventory as inventory

    inventory._registry_warning_logged = False
    inventory._store_warning_logged = False
    yield


def test_list_runtime_tool_names_merges_registry_and_installed(monkeypatch, tmp_path):
    registry = SimpleNamespace(
        get_all_tool_names=lambda: ["web_search", "todo", "Web_Search"],
    )
    monkeypatch.setitem(__import__("sys").modules, "tools.registry", SimpleNamespace(registry=registry))

    store = GeneratedToolStore(path=tmp_path / "generated_tools.json")
    store.create(
        task_that_triggered="fetch stock",
        tool_name="fetch_stock_price",
        tool_code="print('ok')",
        skill_yaml="name: fetch_stock_price",
        description="Stock tool",
        gap_description="gap",
        static_analysis={"safe": True, "violations": []},
        sandbox_result={"passed": True, "output": "ok", "exit_code": 0},
    )
    installed = store.list_all(status="pending")[0]
    store.update(installed.id, status="installed")

    monkeypatch.setattr(
        "keprix.agent.keprix.store.get_generated_tool_store",
        lambda: store,
    )

    names = list_runtime_tool_names()
    assert names == ["fetch_stock_price", "todo", "web_search"]


def test_list_runtime_tool_names_returns_empty_when_sources_fail(monkeypatch):
    import builtins

    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "tools.registry":
            raise ImportError("registry unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(
        "keprix.agent.keprix.store.get_generated_tool_store",
        lambda: (_ for _ in ()).throw(RuntimeError("store unavailable")),
    )

    assert list_runtime_tool_names() == []
