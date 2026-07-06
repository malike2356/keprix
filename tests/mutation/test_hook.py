"""Tests for gap-to-synthesis hooks (Prompt 151)."""

from __future__ import annotations

import asyncio
import textwrap
from types import SimpleNamespace

import pytest

from keprix.improvement.run_analyzer import RunRecord
from keprix.improvement.tool_gap_detector import ToolGapProposal
from keprix.mutation.config import get_mutation_settings
from keprix.mutation.hook import on_run_complete, on_tool_miss
from keprix.mutation.store import MutationStore
from keprix.mutation.tool_synthesizer import SynthesisResult

_GOOD_TOOL = textwrap.dedent(
    '''
    from tools.registry import registry, tool_result, tool_error

    def send_sms_handler(args, **kwargs):
        return tool_result(success=True, sent=True)

    registry.register(
        name="send_sms",
        toolset="generated",
        schema={
            "name": "send_sms",
            "description": "Send SMS",
            "parameters": {"type": "object", "properties": {}},
        },
        handler=send_sms_handler,
    )
    '''
).strip() + "\n"


@pytest.fixture
def mutation_store(tmp_path, monkeypatch):
    get_mutation_settings.cache_clear()
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.mutation.store.get_session_factory", lambda: None)
    monkeypatch.setenv("KEPRIX_TOOL_SIGNING_KEY", str(tmp_path / "signing.pem"))
    monkeypatch.setenv("KEPRIX_TOOL_VERIFY_KEY", str(tmp_path / "verify.pem"))
    monkeypatch.setenv("KEPRIX_MUTATION_GENERATED_TOOLS_DIR", str(tmp_path / "generated"))
    store = MutationStore(sqlite_path=tmp_path / "mutation.db")
    monkeypatch.setattr("keprix.mutation.store._store", store)
    monkeypatch.setattr("keprix.mutation.store.get_mutation_store", lambda: store)
    from keprix.agent.keprix.store import GeneratedToolStore

    agent_store = GeneratedToolStore(path=tmp_path / "agent_generated_tools.json")
    monkeypatch.setattr("keprix.agent.keprix.store.get_generated_tool_store", lambda: agent_store)
    monkeypatch.setattr("keprix.agent.keprix.mutation.get_generated_tool_store", lambda: agent_store)
    return store, tmp_path


@pytest.mark.asyncio
async def test_on_tool_miss_synthesizes_and_hot_loads(mutation_store, monkeypatch):
    store, tmp_path = mutation_store
    calls = {"count": 0}

    async def fake_run_tool_miss_cycle(**kwargs):
        calls["count"] += 1
        from keprix.agent.keprix.store import get_generated_tool_store

        record = get_generated_tool_store().create(
            task_that_triggered=kwargs.get("task", ""),
            tool_name="send_sms",
            tool_code=_GOOD_TOOL,
            skill_yaml="name: send_sms",
            description="Send SMS",
            gap_description="missing tool",
            static_analysis={"safe": True, "violations": []},
            sandbox_result={"passed": True, "output": "{}", "stderr": "", "exit_code": 0},
        )
        return {
            "started": True,
            "status": "pending_approval",
            "record_id": record.id,
            "tool_name": record.tool_name,
            "sandbox_passed": True,
            "record": {"id": record.id, "tool_name": record.tool_name},
        }

    async def fake_finalize(result, **kwargs):
        from keprix.mutation.hook import _hot_load_approved_record

        approved = store.save_generated_tool(
            workspace_id="default",
            tool_name="send_sms",
            description="Send SMS",
            source_code=_GOOD_TOOL,
            trigger="tool_miss",
            confidence=1.0,
            auto_approve_threshold=0.5,
        )
        _hot_load_approved_record(store, approved)
        return (
            "Tool 'send_sms' was not found. A replacement was synthesized "
            "and is now available. Retry the task."
        )

    monkeypatch.setattr("keprix.mutation.hook.run_tool_miss_cycle", fake_run_tool_miss_cycle)
    monkeypatch.setattr("keprix.mutation.hook.finalize_sync_tool_miss", fake_finalize)
    monkeypatch.setenv("KEPRIX_MUTATION_AUTO_APPROVE_THRESHOLD", "0.5")

    message = await on_tool_miss("send_sms", "send a text", "run-1", "default", store)
    assert message is not None
    assert "now available" in message
    assert calls["count"] == 1

    from tools.registry import registry

    assert registry.get_tool("send_sms") is not None
    assert (tmp_path / "generated" / "send_sms.py").exists()


@pytest.mark.asyncio
async def test_on_tool_miss_deduplicates(mutation_store, monkeypatch):
    store, _tmp = mutation_store
    calls = {"count": 0}

    async def fake_run_tool_miss_cycle(**kwargs):
        calls["count"] += 1
        return {
            "started": True,
            "sandbox_passed": True,
            "record_id": "rec-1",
            "tool_name": "dedup_sms",
        }

    async def fake_finalize(result, **kwargs):
        from keprix.mutation.hook import _hot_load_approved_record

        approved = store.save_generated_tool(
            workspace_id="default",
            tool_name="dedup_sms",
            description="Send SMS",
            source_code=_GOOD_TOOL.replace("send_sms", "dedup_sms"),
            trigger="tool_miss",
            confidence=1.0,
            auto_approve_threshold=0.5,
        )
        _hot_load_approved_record(store, approved)
        return "now available"

    monkeypatch.setattr("keprix.mutation.hook.run_tool_miss_cycle", fake_run_tool_miss_cycle)
    monkeypatch.setattr("keprix.mutation.hook.finalize_sync_tool_miss", fake_finalize)
    monkeypatch.setenv("KEPRIX_MUTATION_AUTO_APPROVE_THRESHOLD", "0.5")

    await on_tool_miss("dedup_sms", "task", "run-1", "default", store)
    await on_tool_miss("dedup_sms", "task", "run-2", "default", store)
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_on_tool_miss_returns_fallback_on_failure(mutation_store, monkeypatch):
    store, _tmp = mutation_store

    async def fake_run_tool_miss_cycle(**kwargs):
        return {
            "started": True,
            "status": "blocked",
            "sandbox_passed": False,
            "violations": ["sandbox failed"],
        }

    monkeypatch.setattr("keprix.mutation.hook.run_tool_miss_cycle", fake_run_tool_miss_cycle)
    message = await on_tool_miss("send_sms_fail", "task", "run-1", "default", store)
    assert message is not None
    assert "could not be synthesized" in message


@pytest.mark.asyncio
async def test_on_run_complete_triggers_background_synthesis(mutation_store, monkeypatch):
    store, _tmp = mutation_store
    calls = {"count": 0}

    async def fake_synthesize(proposal, workspace_id, **kwargs):
        calls["count"] += 1
        return SynthesisResult(
            success=True,
            tool_name=proposal.tool_name,
            source_code=_GOOD_TOOL.replace("send_sms", proposal.tool_name),
            inferred_schema=None,
            sandbox_result=None,
            error=None,
            attempts=1,
            tokens_used=3,
        )

    monkeypatch.setattr("keprix.mutation.hook.synthesize_tool", fake_synthesize)
    monkeypatch.setenv("KEPRIX_MUTATION_AUTO_APPROVE_THRESHOLD", "0.5")
    monkeypatch.setenv("KEPRIX_MUTATION_SYNTHESIS_MIN_CONFIDENCE", "0.75")

    record = RunRecord(
        run_id="run-bg",
        agent_id="agent-1",
        ok=False,
        metadata={"task": "need a custom weather lookup tool for London"},
    )
    gap = ToolGapProposal(
        proposal_id="p1",
        tool_name="fetch_weather",
        description="Fetch weather",
        confidence=0.9,
    )
    monkeypatch.setattr(
        "keprix.mutation.hook.detect_tool_gaps",
        lambda _record, _proposals: [gap],
    )
    names = await on_run_complete(record, [], "default", store)
    assert "fetch_weather" in names
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_on_run_complete_skips_below_confidence_threshold(mutation_store, monkeypatch):
    store, _tmp = mutation_store
    calls = {"count": 0}

    async def fake_synthesize(proposal, workspace_id, **kwargs):
        calls["count"] += 1
        return SynthesisResult(
            success=True,
            tool_name=proposal.tool_name,
            source_code=_GOOD_TOOL,
            inferred_schema=None,
            sandbox_result=None,
            error=None,
            attempts=1,
            tokens_used=1,
        )

    monkeypatch.setattr("keprix.mutation.hook.synthesize_tool", fake_synthesize)
    monkeypatch.setenv("KEPRIX_MUTATION_SYNTHESIS_MIN_CONFIDENCE", "0.75")
    gap = ToolGapProposal(
        proposal_id="p1",
        tool_name="low_conf_tool",
        description="low confidence gap",
        confidence=0.5,
    )
    monkeypatch.setattr(
        "keprix.mutation.hook.detect_tool_gaps",
        lambda _record, _proposals: [gap],
    )
    record = RunRecord(run_id="run-low", agent_id="agent-1", ok=False)
    names = await on_run_complete(record, [], "default", store)
    assert names == []
    assert calls["count"] == 0


@pytest.mark.asyncio
async def test_on_run_complete_skips_existing_tool(mutation_store, monkeypatch):
    store, _tmp = mutation_store
    calls = {"count": 0}

    async def fake_synthesize(proposal, workspace_id, **kwargs):
        calls["count"] += 1
        return SynthesisResult(
            success=True,
            tool_name=proposal.tool_name,
            source_code=_GOOD_TOOL,
            inferred_schema=None,
            sandbox_result=None,
            error=None,
            attempts=1,
            tokens_used=1,
        )

    monkeypatch.setattr("keprix.mutation.hook.synthesize_tool", fake_synthesize)
    gap = ToolGapProposal(
        proposal_id="p1",
        tool_name="send_sms",
        description="already exists",
        confidence=0.95,
    )
    monkeypatch.setattr(
        "keprix.mutation.hook.detect_tool_gaps",
        lambda _record, _proposals: [gap],
    )
    monkeypatch.setattr("keprix.mutation.hook._tool_in_registry", lambda _name: True)
    record = RunRecord(run_id="run-skip", agent_id="agent-1", ok=False)
    names = await on_run_complete(record, [], "default", store)
    assert names == []
    assert calls["count"] == 0
