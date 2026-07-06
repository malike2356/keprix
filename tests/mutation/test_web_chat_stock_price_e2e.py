"""Web chat stock price mutation E2E stream tests (Prompt 193)."""

from __future__ import annotations

from dataclasses import asdict

import pytest

from keprix.agent.keprix.mutation import MutationEngine
from keprix.interfaces.web_ui_stream import iter_web_ui_gateway_stream, web_ui_agent_loop_enabled
from keprix.interfaces.web_ui_stream_events import GatewayStreamEvent


@pytest.fixture(autouse=True)
def mutation_stream_env(tmp_path, monkeypatch):
    tools_dir = tmp_path / "generated" / "tools"
    skills_dir = tmp_path / "generated" / "skills"
    store_dir = tmp_path / "mutation"
    tools_dir.mkdir(parents=True)
    skills_dir.mkdir(parents=True)
    from keprix.agent.keprix.store import GeneratedToolStore

    monkeypatch.setenv("KEPRIX_MUTATION_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_CHAT_MUTATION_SIDECAR", "false")
    monkeypatch.setenv("KEPRIX_GENERATED_TOOLS_DIR", str(tools_dir))
    monkeypatch.setenv("KEPRIX_GENERATED_SKILLS_DIR", str(skills_dir))
    monkeypatch.setenv("KEPRIX_MUTATION_REQUIRED_CHANNELS", "web_ui")
    monkeypatch.setenv("KEPRIX_TOOL_SIGNING_KEY", str(tmp_path / "signing.pem"))
    monkeypatch.setenv("KEPRIX_TOOL_VERIFY_KEY", str(tmp_path / "verify.pem"))
    store = GeneratedToolStore(path=store_dir / "generated_tools.json")
    monkeypatch.setattr("keprix.agent.keprix.store.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.mutation.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.approval.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.auditor.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.mutation_wait.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.mutation._engine", None)
    yield {"store": store}


@pytest.mark.asyncio
async def test_stock_price_gateway_stream_emits_mutation(monkeypatch, mutation_stream_env):
    store = mutation_stream_env["store"]

    async def fake_run_tool_miss_cycle(**kwargs):
        record = store.create(
            task_that_triggered=kwargs.get("task", ""),
            tool_name="fetch_stock_price",
            tool_code='"""Generated"""\nprint("ok")',
            skill_yaml="name: fetch_stock_price",
            description="Fetch stock price",
            gap_description="No tool exists to fetch live stock prices.",
            static_analysis={"safe": True, "violations": []},
            sandbox_result={"passed": True, "output": '{"price": 213.42}', "stderr": "", "exit_code": 0},
            session_id=kwargs.get("session_id"),
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
    monkeypatch.setattr(
        "keprix.agent.keprix.mutation_hook.mutation_stream_wait_enabled",
        lambda: False,
    )
    monkeypatch.setattr(
        "keprix.interfaces.web_ui_stream._stream_agent_tool_loop",
        lambda **_kwargs: _empty_agent_loop(),
    )
    monkeypatch.delenv("KEPRIX_WEB_UI_AGENT_LOOP", raising=False)

    events = [
        event
        async for event in iter_web_ui_gateway_stream(
            agent_id="default",
            trace_id="trace-stock",
            message="What is the current stock price of Apple?",
            user_id="web",
            session_id="sess-stock",
        )
    ]
    assert any(event.event == "mutation" for event in events)
    mutation = next(event for event in events if event.event == "mutation")
    assert mutation.payload.get("toolName") == "fetch_stock_price"


def test_web_ui_agent_loop_defaults_on_for_developer(monkeypatch):
    monkeypatch.delenv("KEPRIX_WEB_UI_AGENT_LOOP", raising=False)
    monkeypatch.setattr(
        "keprix.keys.local_access.effective_access_level",
        lambda: "developer",
    )
    assert web_ui_agent_loop_enabled() is True


def test_web_ui_agent_loop_explicit_false_overrides_developer(monkeypatch):
    monkeypatch.setenv("KEPRIX_WEB_UI_AGENT_LOOP", "false")
    monkeypatch.setattr(
        "keprix.keys.local_access.effective_access_level",
        lambda: "developer",
    )
    assert web_ui_agent_loop_enabled() is False


async def _empty_agent_loop():
    if False:
        yield GatewayStreamEvent("text_done", {})
    return
    yield  # pragma: no cover
