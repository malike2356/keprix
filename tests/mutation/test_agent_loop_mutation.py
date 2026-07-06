"""Tests for agent loop mutation hook (Prompt 143)."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from keprix.agent.keprix.mutation import MutationEngine
from keprix.agent.keprix.mutation_hook import (
    evaluate_turn_tool_miss,
    handle_tool_miss_stream,
    run_agent_loop_mutation_turn,
    wait_for_mutation_resolution,
)
from keprix.agent.keprix.static_analyser import static_analyser
from keprix.agent.keprix.store import GeneratedToolStore
from keprix.agent.keprix.tool_dispatch import ToolDispatchResult, classify_registry_result, dispatch_tool
from keprix.interfaces.web_ui_stream_events import GatewayStreamEvent


@pytest.fixture(autouse=True)
def mutation_hook_env(tmp_path, monkeypatch):
    tools_dir = tmp_path / "generated" / "tools"
    skills_dir = tmp_path / "generated" / "skills"
    store_dir = tmp_path / "mutation"
    tools_dir.mkdir(parents=True)
    skills_dir.mkdir(parents=True)
    monkeypatch.setenv("KEPRIX_MUTATION_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_CHAT_MUTATION_SIDECAR", "false")
    monkeypatch.setenv("KEPRIX_GENERATED_TOOLS_DIR", str(tools_dir))
    monkeypatch.setenv("KEPRIX_GENERATED_SKILLS_DIR", str(skills_dir))
    monkeypatch.setenv("KEPRIX_MUTATION_REQUIRED_CHANNELS", "web_ui")
    monkeypatch.setenv("KEPRIX_TOOL_SIGNING_KEY", str(tmp_path / "signing.pem"))
    monkeypatch.setenv("KEPRIX_TOOL_VERIFY_KEY", str(tmp_path / "verify.pem"))
    monkeypatch.setenv("KEPRIX_MUTATION_APPROVAL_TIMEOUT", "2")
    store = GeneratedToolStore(path=store_dir / "generated_tools.json")
    monkeypatch.setattr("keprix.agent.keprix.store.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.mutation.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.approval.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.auditor.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.mutation_wait.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.mutation._engine", None)
    yield {"store": store, "tools_dir": tools_dir}


def test_classify_registry_result_not_found():
    result = classify_registry_result("fetch_stock_price", '{"error": "Unknown tool: fetch_stock_price"}')
    assert result.error_code == "not_found"
    assert result.ok is False


def test_dispatch_tool_not_found(monkeypatch):
    monkeypatch.setattr(
        "tools.registry.registry.dispatch",
        lambda name, args, **kwargs: __import__("json").dumps({"error": f"Unknown tool: {name}"}),
    )
    result = dispatch_tool("missing_tool", {})
    assert result.error_code == "not_found"


@pytest.mark.asyncio
async def test_evaluate_turn_tool_miss_for_stock_gap(monkeypatch):
    monkeypatch.setattr(
        "keprix.agent.keprix.mutation_hook.list_runtime_tool_names",
        lambda: ["todo", "web_search"],
    )
    miss = await evaluate_turn_tool_miss(task="fetch AAPL stock price")
    assert miss is not None
    assert miss.error_code == "not_found"
    assert miss.tool_name == "fetch_stock_price"


@pytest.mark.asyncio
async def test_evaluate_turn_tool_miss_for_explicit_unknown_tool():
    miss = await evaluate_turn_tool_miss(
        task="run custom lookup",
        requested_tool="fetch_stock_price",
        available_tools=["todo"],
    )
    assert miss is not None
    assert miss.error_code == "not_found"


@pytest.mark.asyncio
async def test_dispatcher_not_found_calls_run_cycle_once(monkeypatch, mutation_hook_env):
    store = mutation_hook_env["store"]
    run_calls: list[dict] = []

    async def fake_run_tool_miss_cycle(**kwargs):
        run_calls.append(dict(kwargs))
        task = str(kwargs.get("task") or "")
        session_id = kwargs.get("session_id")
        record = store.create(
            task_that_triggered=task,
            tool_name="fetch_stock_price",
            tool_code='"""Generated"""\nprint("ok")',
            skill_yaml="name: fetch_stock_price",
            description="Fetch stock price",
            gap_description="No tool exists to fetch live stock prices.",
            static_analysis={"safe": True, "violations": []},
            sandbox_result={"passed": True, "output": '{"price": 213.42}', "stderr": "", "exit_code": 0},
            session_id=session_id,
        )
        return {
            "started": True,
            "status": "pending_approval",
            "record_id": record.id,
            "tool_name": record.tool_name,
            "sandbox_passed": True,
            "record": asdict(record),
        }

    monkeypatch.setattr(
        "keprix.agent.keprix.mutation_hook.run_tool_miss_cycle",
        fake_run_tool_miss_cycle,
    )
    monkeypatch.setattr(
        "keprix.agent.keprix.mutation_hook.list_runtime_tool_names",
        lambda: ["todo", "web_search"],
    )

    events = [
        event
        async for event in handle_tool_miss_stream(
            task="fetch AAPL stock price",
            user_id="web",
            session_id="sess-1",
            requested_tool="fetch_stock_price",
            wait_for_approval=False,
        )
    ]
    assert len(run_calls) == 1
    assert run_calls[0].get("requested_tool") == "fetch_stock_price"
    assert any(event.event == "mutation" for event in events)


@pytest.mark.asyncio
async def test_pending_approval_pauses_until_approve(monkeypatch, mutation_hook_env):
    store = mutation_hook_env["store"]

    async def fake_run_tool_miss_cycle(**kwargs):
        task = str(kwargs.get("task") or "")
        session_id = kwargs.get("session_id")
        record = store.create(
            task_that_triggered=task,
            tool_name="fetch_stock_price",
            tool_code='"""Generated"""\nprint("ok")',
            skill_yaml="name: fetch_stock_price",
            description="Fetch stock price",
            gap_description="gap",
            static_analysis={"safe": True, "violations": []},
            sandbox_result={"passed": True, "output": "{}", "stderr": "", "exit_code": 0},
            session_id=session_id,
        )
        return {
            "started": True,
            "status": "pending_approval",
            "record_id": record.id,
            "tool_name": record.tool_name,
            "sandbox_passed": True,
            "record": asdict(record),
        }

    async def approve_later(record_id: str):
        await asyncio.sleep(0.15)
        store.update(record_id, status="installed")

    monkeypatch.setattr(
        "keprix.agent.keprix.mutation_hook.run_tool_miss_cycle",
        fake_run_tool_miss_cycle,
    )
    monkeypatch.setattr(
        "keprix.agent.keprix.mutation_hook.list_runtime_tool_names",
        lambda: ["todo"],
    )
    async def fake_retry(self, **kwargs):
        return "Apple Inc. (AAPL) is currently trading at $213.42."

    monkeypatch.setattr(
        "keprix.agent.keprix.mutation_hook.KeprixRetry.retry",
        fake_retry,
    )

    async def collect():
        events: list[GatewayStreamEvent] = []
        async for event in handle_tool_miss_stream(
            task="fetch AAPL stock price",
            user_id="web",
            requested_tool="fetch_stock_price",
            wait_for_approval=True,
        ):
            events.append(event)
            if event.event == "mutation":
                record_id = event.payload.get("id")
                asyncio.create_task(approve_later(str(record_id)))
        return events

    events = await asyncio.wait_for(collect(), timeout=3.0)
    text = "".join(event.payload.get("content", "") for event in events if event.event == "text_delta")
    assert "213.42" in text


@pytest.mark.asyncio
async def test_reject_yields_polite_message(monkeypatch, mutation_hook_env):
    store = mutation_hook_env["store"]

    async def fake_run_tool_miss_cycle(**kwargs):
        task = str(kwargs.get("task") or "")
        record = store.create(
            task_that_triggered=task,
            tool_name="fetch_stock_price",
            tool_code='"""Generated"""\nprint("ok")',
            skill_yaml="name: fetch_stock_price",
            description="Fetch stock price",
            gap_description="gap",
            static_analysis={"safe": True, "violations": []},
            sandbox_result={"passed": True, "output": "{}", "stderr": "", "exit_code": 0},
        )
        return {
            "started": True,
            "status": "pending_approval",
            "record_id": record.id,
            "tool_name": record.tool_name,
            "sandbox_passed": True,
            "record": asdict(record),
        }

    monkeypatch.setattr(
        "keprix.agent.keprix.mutation_hook.run_tool_miss_cycle",
        fake_run_tool_miss_cycle,
    )
    monkeypatch.setattr(
        "keprix.agent.keprix.mutation_hook.list_runtime_tool_names",
        lambda: ["todo"],
    )

    async def collect():
        events: list[GatewayStreamEvent] = []
        async for event in handle_tool_miss_stream(
            task="fetch AAPL stock price",
            user_id="web",
            requested_tool="fetch_stock_price",
            wait_for_approval=True,
        ):
            events.append(event)
            if event.event == "mutation":
                store.update(str(event.payload.get("id")), status="rejected")
        return events

    events = await collect()
    text = "".join(event.payload.get("content", "") for event in events if event.event == "text_delta")
    assert "rejected" in text.lower()


@pytest.mark.asyncio
async def test_mutation_disabled_skips_cycle(monkeypatch):
    monkeypatch.setenv("KEPRIX_MUTATION_ENABLED", "false")
    from keprix.agent.keprix.config import get_mutation_config

    if hasattr(get_mutation_config, "cache_clear"):
        get_mutation_config.cache_clear()

    run_calls: list[str] = []

    async def fake_run_tool_miss_cycle(**kwargs):
        run_calls.append(kwargs.get("task", ""))
        return {"started": False, "reason": "mutation_disabled"}

    monkeypatch.setattr(
        "keprix.agent.keprix.mutation_hook.run_tool_miss_cycle",
        fake_run_tool_miss_cycle,
    )

    events = [
        event
        async for event in handle_tool_miss_stream(
            task="fetch AAPL stock price",
            user_id="web",
            requested_tool="fetch_stock_price",
        )
    ]
    assert run_calls == []
    text = "".join(event.payload.get("content", "") for event in events if event.event == "text_delta")
    assert "cannot synthesise" in text.lower() or "disabled" in text.lower()


def test_recursive_guard_blocks_mutation_import():
    code = "from keprix.agent.keprix.mutation import get_mutation_engine"
    analysis = static_analyser.scan(code)
    assert analysis.safe is False


@pytest.mark.asyncio
async def test_web_ui_stream_uses_loop_not_sidecar(monkeypatch, mutation_hook_env):
    from keprix.interfaces.web_ui_stream import iter_web_ui_gateway_stream

    seen: dict[str, bool] = {}

    async def fake_loop_turn(**kwargs):
        seen["loop"] = True
        yield GatewayStreamEvent("mutation", {"id": "mut-1", "toolName": "fetch_stock_price", "status": "pending"})
        yield GatewayStreamEvent("text_done", {})
        yield GatewayStreamEvent("done", {})

    monkeypatch.setattr(
        "keprix.agent.keprix.mutation_hook.run_agent_loop_mutation_turn",
        fake_loop_turn,
    )
    monkeypatch.setattr(
        "keprix.agent.keprix.mutation_hook.chat_mutation_sidecar_enabled",
        lambda: False,
    )

    events = [
        event
        async for event in iter_web_ui_gateway_stream(
            agent_id="default",
            trace_id="trace",
            message="fetch AAPL stock price",
            user_id="web",
        )
    ]
    assert seen.get("loop") is True
    assert any(event.event == "mutation" for event in events)


@pytest.mark.asyncio
async def test_wait_for_mutation_resolution_timeout(mutation_hook_env):
    store = mutation_hook_env["store"]
    record = store.create(
        task_that_triggered="task",
        tool_name="demo_tool",
        tool_code="print(1)",
        skill_yaml="name: demo_tool",
        description="demo",
        gap_description="gap",
        static_analysis={"safe": True, "violations": []},
        sandbox_result={"passed": True, "output": "", "stderr": "", "exit_code": 0},
    )
    result = await wait_for_mutation_resolution(record.id, timeout_s=0.2)
    assert result == "timeout"


@pytest.mark.asyncio
async def test_run_agent_loop_mutation_turn_no_duplicate_cycles(monkeypatch):
    calls = 0

    async def fake_handle(**kwargs):
        nonlocal calls
        calls += 1
        yield GatewayStreamEvent("text_done", {})

    monkeypatch.setattr("keprix.agent.keprix.mutation_hook.handle_tool_miss_stream", fake_handle)
    async def fake_evaluate(**kwargs):
        return ToolDispatchResult(
            ok=False,
            error_code="not_found",
            tool_name="fetch_stock_price",
            message="missing",
        )

    monkeypatch.setattr("keprix.agent.keprix.mutation_hook.evaluate_turn_tool_miss", fake_evaluate)

    events = [event async for event in run_agent_loop_mutation_turn(user_text="fetch AAPL", user_id="web")]
    assert calls == 1
    assert events
