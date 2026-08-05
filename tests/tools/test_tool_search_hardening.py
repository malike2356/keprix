"""Deferred tool search hardening tests (Prompt 294)."""

from __future__ import annotations

import json

from tools.tool_search import (
    BRIDGE_TOOL_NAMES,
    ToolSearchConfig,
    assemble_tool_defs,
    clear_session_schema_cache,
    dispatch_tool_describe,
    dispatch_tool_search,
    get_deferred_tool_stats,
    reset_deferred_tool_stats,
    resolve_underlying_call,
    should_activate,
    validate_deferred_invoke,
)
from agent.layers.tools import DEFERRED_TOOLS_CLAUSE, render_tools_layer
from agent.layered_prompt import PromptSessionContext
from types import SimpleNamespace


def _td(name: str, desc: str = "d", props: dict | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": props or {"q": {"type": "string"}},
            },
        },
    }


def test_count_threshold_activates_auto() -> None:
    cfg = ToolSearchConfig.from_raw({"enabled": "auto", "count_threshold": 3, "threshold_pct": 90})
    assert should_activate(cfg, deferrable_tokens=10, context_length=200_000, deferrable_count=3)
    assert not should_activate(cfg, deferrable_tokens=10, context_length=200_000, deferrable_count=2)


def test_above_count_threshold_assembly_defers(monkeypatch) -> None:
    from tools.registry import registry

    reset_deferred_tool_stats()
    names = []
    for i in range(5):
        name = f"mcp_hard_defer_{i}"
        names.append(name)

        def _handler(args, task_id=None, **kw):
            return json.dumps({"ok": True})

        registry.register(
            name=name,
            handler=_handler,
            schema=_td(name, f"plugin tool {i}"),
            toolset="mcp-hard-defer",
        )

    defs = [_td("terminal", "shell")] + [_td(n) for n in names]
    # Force core classification for terminal via real registry; terminal is core.
    cfg = ToolSearchConfig.from_raw({"enabled": "auto", "count_threshold": 3, "threshold_pct": 99})
    result = assemble_tool_defs(defs, context_length=200_000, config=cfg)
    assert result.activated is True
    assert result.deferred_count >= 3
    assert result.system_note
    visible_names = {(td.get("function") or {}).get("name") for td in result.tool_defs}
    assert "terminal" in visible_names
    for bridge in BRIDGE_TOOL_NAMES:
        assert bridge in visible_names
    for n in names:
        assert n not in visible_names
    stats = get_deferred_tool_stats()
    assert stats.activated is True
    assert stats.deferred_tokens_saved >= 0


def test_invoke_without_search_fails() -> None:
    clear_session_schema_cache("sess-miss")
    reset_deferred_tool_stats()
    name, args, err = resolve_underlying_call(
        {"name": "mcp_hard_defer_0", "arguments": {"q": "x"}},
        session_id="sess-miss",
    )
    assert name is None
    assert err is not None
    assert "tool_search" in err.lower()
    assert get_deferred_tool_stats().schema_misses >= 1


def test_schema_miss_on_guessed_params() -> None:
    clear_session_schema_cache("sess-guess")
    reset_deferred_tool_stats()
    defs = [_td("mcp_hard_defer_0", "d", {"repo": {"type": "string"}})]
    # Pretend registry classifies as deferrable by using dispatch with defs only.
    # Seed via describe path using catalog from defs.
    from tools.tool_search import get_session_schema_cache

    # Manually remember exact schema, then guess a param.
    get_session_schema_cache("sess-guess").remember_tool(
        "mcp_hard_defer_0",
        {"type": "object", "properties": {"repo": {"type": "string"}}},
    )
    err = validate_deferred_invoke(
        "mcp_hard_defer_0",
        {"repo": "a/b", "invented": True},
        session_id="sess-guess",
    )
    assert err is not None
    assert "invented" in err
    assert get_deferred_tool_stats().schema_misses >= 1


def test_search_then_invoke_ok(monkeypatch) -> None:
    from tools.registry import registry

    clear_session_schema_cache("sess-ok")
    reset_deferred_tool_stats()

    def _handler(args, task_id=None, **kw):
        return json.dumps({"ok": True, "args": args})

    registry.register(
        name="mcp_hard_ok_tool",
        handler=_handler,
        schema=_td("mcp_hard_ok_tool", "ok tool", {"repo": {"type": "string"}}),
        toolset="mcp-hard-ok",
    )
    defs = [_td("mcp_hard_ok_tool", "ok tool", {"repo": {"type": "string"}})]
    search = json.loads(
        dispatch_tool_search(
            {"query": "mcp_hard_ok_tool", "limit": 5},
            current_tool_defs=defs,
            session_id="sess-ok",
        )
    )
    assert search["matches"]
    name, args, err = resolve_underlying_call(
        {"name": "mcp_hard_ok_tool", "arguments": {"repo": "a/b"}},
        session_id="sess-ok",
    )
    assert err is None
    assert name == "mcp_hard_ok_tool"
    assert args == {"repo": "a/b"}


def test_tools_layer_includes_deferred_clause() -> None:
    agent = SimpleNamespace(
        valid_tool_names=["terminal", "tool_search", "tool_describe", "tool_call"],
        _deferred_tools_note="12 tools available via tool_search",
        model="gpt-4.1",
        provider="openai",
    )
    ctx = PromptSessionContext(
        model_name="gpt-4.1",
        provider_name="openai",
        session_id="s",
        keprix_version="0.1.0",
    )
    text = render_tools_layer(ctx, agent)
    assert DEFERRED_TOOLS_CLAUSE.split("\n")[0] in text
    assert "tool_search" in text
    assert "12 tools available via tool_search" in text


def test_deferred_stats_endpoint_shape() -> None:
    reset_deferred_tool_stats()
    from tools.tool_search import get_deferred_tool_stats

    payload = get_deferred_tool_stats().to_dict()
    for key in (
        "core_visible",
        "deferred_count",
        "deferred_tokens_saved",
        "searches",
        "invokes",
        "schema_misses",
    ):
        assert key in payload
