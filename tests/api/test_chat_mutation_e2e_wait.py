"""E2E: chat mutation pause-until-approve (hook + approve API)."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from keprix.agent.keprix.mutation import MutationEngine
from keprix.agent.keprix.mutation_hook import handle_tool_miss_stream
from keprix.agent.keprix.mutation_wait import (
    has_active_mutation_wait,
    register_mutation_wait_now,
    signal_mutation_resolved,
    unregister_mutation_wait,
)
from keprix.agent.keprix.schemas import ApprovalResult
from keprix.agent.keprix.store import GeneratedToolStore


@pytest.fixture
def mutation_e2e_store(tmp_path, monkeypatch):
    tools_dir = tmp_path / "generated" / "tools"
    skills_dir = tmp_path / "generated" / "skills"
    store_dir = tmp_path / "mutation"
    tools_dir.mkdir(parents=True)
    skills_dir.mkdir(parents=True)

    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("KEPRIX_MUTATION_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_MUTATION_STREAM_WAIT_APPROVAL", "true")
    monkeypatch.setenv("KEPRIX_MUTATION_REQUIRED_CHANNELS", "web_ui")
    monkeypatch.setenv("KEPRIX_MUTATION_APPROVAL_TIMEOUT", "5")
    monkeypatch.setenv("KEPRIX_GENERATED_TOOLS_DIR", str(tools_dir))
    monkeypatch.setenv("KEPRIX_GENERATED_SKILLS_DIR", str(skills_dir))
    monkeypatch.setenv("KEPRIX_TOOL_SIGNING_KEY", str(tmp_path / "signing.pem"))
    monkeypatch.setenv("KEPRIX_TOOL_VERIFY_KEY", str(tmp_path / "verify.pem"))

    store = GeneratedToolStore(path=store_dir / "generated_tools.json")
    monkeypatch.setattr("keprix.agent.keprix.store.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.mutation.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.approval.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.auditor.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.mutation_wait.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.mutation._engine", None)
    return store


def test_approve_reports_stream_waiting_when_waiter_active(mutation_e2e_store, monkeypatch):
    """Approve API must not append retry when an open stream owns the turn."""
    from keprix.api.conversation_routes import approve_mutation

    store = mutation_e2e_store
    record = store.create(
        task_that_triggered="fetch AAPL stock price",
        tool_name="fetch_stock_price",
        tool_code='"""Generated"""\nprint("ok")',
        skill_yaml="name: fetch_stock_price",
        description="Fetch stock price",
        gap_description="gap",
        static_analysis={"safe": True, "violations": []},
        sandbox_result={"passed": True, "output": "{}", "stderr": "", "exit_code": 0},
        session_id="sess-wait",
    )

    async def fake_approve(record_id, *, approver_id="admin", channel="web_ui"):
        store.update(record_id, status="installed")
        installed = store.get(record_id)
        assert installed is not None
        return ApprovalResult(record=installed, retry_message="duplicate retry")

    monkeypatch.setattr(
        "keprix.api.conversation_routes.get_mutation_engine",
        lambda: SimpleNamespace(approve=fake_approve),
    )

    register_mutation_wait_now(record.id)
    assert has_active_mutation_wait(record.id)

    try:
        body = asyncio.run(
            approve_mutation(
                record.id,
                channel="web_ui",
                session_id="sess-wait",
                user={"id": "admin", "role": "admin"},
            )
        )
        assert body.get("stream_waiting") is True
        assert body.get("retry_message") is None
    finally:
        asyncio.run(unregister_mutation_wait(record.id))


@pytest.mark.asyncio
async def test_hook_stream_waits_for_approve_signal_then_retries(mutation_e2e_store, monkeypatch):
    """Open stream turn resumes when approve signals the registered waiter."""
    store = mutation_e2e_store
    base_engine = MutationEngine()

    async def fake_run_cycle(task, available_tools, *, session_id=None, trigger="gap", requested_tool=None):
        record = store.create(
            task_that_triggered=task,
            tool_name="fetch_stock_price",
            tool_code='"""Generated"""\nprint("ok")',
            skill_yaml="name: fetch_stock_price",
            description="Fetch stock price",
            gap_description="gap",
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
        "keprix.agent.keprix.mutation_hook.get_mutation_engine",
        lambda: SimpleNamespace(
            detect_gap_async=base_engine.detect_gap_async,
            run_cycle=fake_run_cycle,
        ),
    )
    monkeypatch.setattr(
        "keprix.agent.keprix.mutation_hook.list_runtime_tool_names",
        lambda: ["todo", "web_search"],
    )

    async def fake_retry(self, **kwargs):
        return "Apple Inc. (AAPL) is currently trading at $213.42."

    monkeypatch.setattr("keprix.agent.keprix.mutation_hook.KeprixRetry.retry", fake_retry)

    record_id: str | None = None

    async def signal_after_mutation():
        await asyncio.sleep(0.05)
        assert record_id is not None
        await signal_mutation_resolved(record_id, "approved")

    async def collect():
        nonlocal record_id
        events = []
        signal_task: asyncio.Task[None] | None = None
        async for event in handle_tool_miss_stream(
            task="fetch AAPL stock price",
            user_id="web",
            session_id="sess-wait",
            requested_tool="fetch_stock_price",
            wait_for_approval=True,
        ):
            events.append(event)
            if event.event == "mutation":
                record_id = str(event.payload.get("id"))
                assert has_active_mutation_wait(record_id)
                signal_task = asyncio.create_task(signal_after_mutation())
        if signal_task is not None:
            await signal_task
        return events

    events = await asyncio.wait_for(collect(), timeout=5.0)
    mutation_events = [event for event in events if event.event == "mutation"]
    assert len(mutation_events) == 1
    text = "".join(event.payload.get("content", "") for event in events if event.event == "text_delta")
    assert "213.42" in text
    assert any(event.event == "text_done" for event in events)
