"""Tests for mutation quality scoring (Prompt 154)."""

from __future__ import annotations

import textwrap
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from keprix.improvement.run_analyzer import ImprovementProposal, RunRecord
from keprix.mutation.quality import QualityScorer, classify_run_outcome, get_quality_scorer

_VALID_TOOL = textwrap.dedent(
    '''
    from tools.registry import registry, tool_result, tool_error

    def demo_tool_handler(args, **kwargs):
        return tool_result(success=True)

    registry.register(
        name="demo_tool",
        toolset="generated",
        schema={
            "name": "demo_tool",
            "description": "Demo tool",
            "parameters": {"type": "object", "properties": {}},
        },
        handler=demo_tool_handler,
    )
    '''
).strip() + "\n"


@pytest.fixture
def mutation_store(tmp_path, monkeypatch):
    from keprix.mutation.config import get_mutation_settings

    get_mutation_settings.cache_clear()
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.mutation.store.get_session_factory", lambda: None)
    monkeypatch.setenv("KEPRIX_TOOL_SIGNING_KEY", str(tmp_path / "signing.pem"))
    monkeypatch.setenv("KEPRIX_TOOL_VERIFY_KEY", str(tmp_path / "verify.pem"))
    monkeypatch.setenv("KEPRIX_MUTATION_GENERATED_TOOLS_DIR", str(tmp_path / "generated"))
    from keprix.mutation.store import MutationStore

    store = MutationStore(sqlite_path=tmp_path / "mutation.db")
    monkeypatch.setattr("keprix.mutation.store._store", store)
    monkeypatch.setattr("keprix.mutation.store.get_mutation_store", lambda: store)
    return store, tmp_path


@pytest.fixture
def scorer(mutation_store):
    store, _tmp = mutation_store
    return QualityScorer(store=store)


def test_ema_converges_on_repeated_success(scorer, mutation_store):
    store, _tmp = mutation_store
    record = store.save_generated_tool(
        workspace_id="default",
        tool_name="demo_tool",
        description="Demo",
        source_code=_VALID_TOOL,
        trigger="test",
        confidence=0.5,
        auto_approve_threshold=0.85,
    )
    store.update_mutation_usage(record.id, quality_score=0.0, use_count=0)

    for _ in range(10):
        scorer.record_sample(record.id, "success")

    updated = store.get_generated_tool(record.id)
    assert updated is not None
    assert updated.quality_score is not None
    assert updated.quality_score > 0.95
    assert updated.use_count == 10


def test_ema_drops_on_repeated_failure(scorer, mutation_store):
    store, _tmp = mutation_store
    record = store.save_generated_tool(
        workspace_id="default",
        tool_name="demo_tool",
        description="Demo",
        source_code=_VALID_TOOL,
        trigger="test",
        confidence=0.95,
        auto_approve_threshold=0.85,
    )
    store.update_mutation_usage(record.id, quality_score=1.0, use_count=0)

    for _ in range(5):
        scorer.record_sample(record.id, "failure")

    updated = store.get_generated_tool(record.id)
    assert updated is not None
    assert updated.quality_score is not None
    assert updated.quality_score < 0.3


def test_auto_quarantine_below_threshold(scorer, mutation_store, monkeypatch):
    store, tmp_path = mutation_store
    record = store.save_generated_tool(
        workspace_id="default",
        tool_name="demo_tool",
        description="Demo",
        source_code=_VALID_TOOL,
        trigger="test",
        confidence=0.95,
        auto_approve_threshold=0.85,
    )
    store.write_tool_to_disk(record, tmp_path / "generated")
    store.update_mutation_usage(record.id, quality_score=1.0, use_count=0)

    mock_registry = MagicMock()
    monkeypatch.setattr("keprix.mutation.store.registry", mock_registry, raising=False)
    monkeypatch.setattr("tools.registry.registry", mock_registry)
    notify = MagicMock()
    monkeypatch.setattr("keprix.mutation.quality._notify_operator", notify)

    for _ in range(5):
        scorer.record_sample(record.id, "failure")

    updated = store.get_generated_tool(record.id)
    assert updated is not None
    assert updated.status == "quarantined"
    assert not (tmp_path / "generated" / "demo_tool.py").exists()
    notify.assert_called()


def test_auto_promote_above_threshold_after_min_uses(scorer, mutation_store):
    store, _tmp = mutation_store
    record = store.save_generated_tool(
        workspace_id="default",
        tool_name="demo_tool",
        description="Demo",
        source_code=_VALID_TOOL,
        trigger="test",
        confidence=0.95,
        auto_approve_threshold=0.85,
    )
    store.update_mutation_usage(record.id, quality_score=0.9, use_count=4)

    scorer.record_sample(record.id, "success")

    updated = store.get_generated_tool(record.id)
    assert updated is not None
    assert updated.metadata.get("promoted") is True
    assert updated.use_count == 5


def test_record_tool_use_no_op_for_builtin_tool(scorer, mutation_store, monkeypatch):
    store, _tmp = mutation_store
    record = store.save_generated_tool(
        workspace_id="default",
        tool_name="demo_tool",
        description="Demo",
        source_code=_VALID_TOOL,
        trigger="test",
        confidence=0.95,
        auto_approve_threshold=0.85,
    )
    mock_registry = MagicMock()
    mock_registry.get_toolset_for_tool.return_value = "builtin"
    monkeypatch.setattr("tools.registry.registry", mock_registry)

    from keprix.mutation.quality import maybe_record_generated_tool_use

    maybe_record_generated_tool_use("builtin_tool", "run-1", {"ok": True})
    updated = store.get_generated_tool(record.id)
    assert updated is not None
    assert updated.use_count == 0


def test_quality_history_newest_first(scorer, mutation_store):
    store, _tmp = mutation_store
    record = store.save_generated_tool(
        workspace_id="default",
        tool_name="demo_tool",
        description="Demo",
        source_code=_VALID_TOOL,
        trigger="test",
        confidence=0.95,
        auto_approve_threshold=0.85,
    )
    scorer.record_sample(record.id, "success", run_id="run-a")
    scorer.record_sample(record.id, "failure", run_id="run-b")
    scorer.record_sample(record.id, "partial", run_id="run-c")

    history = scorer.get_quality_history(record.id, limit=10)
    assert len(history) == 3
    assert history[0].run_id == "run-c"
    assert history[1].run_id == "run-b"
    assert history[2].run_id == "run-a"


def test_classify_run_outcome_variants():
    record = RunRecord(run_id="r1", agent_id="a1", ok=True)
    assert classify_run_outcome(record, []) == "success"

    proposals = [
        ImprovementProposal("p1", "r1", "a1", "tool_failure", "t", "d"),
        ImprovementProposal("p2", "r1", "a1", "slow_step", "t", "d"),
    ]
    assert classify_run_outcome(record, proposals) == "partial"

    proposals = [
        ImprovementProposal("p1", "r1", "a1", "tool_failure", "t", "d"),
        ImprovementProposal("p2", "r1", "a1", "repeated_failure", "t", "d"),
    ]
    assert classify_run_outcome(record, proposals) == "failure"


def test_get_quality_scorer_singleton():
    first = get_quality_scorer()
    second = get_quality_scorer()
    assert first is second
