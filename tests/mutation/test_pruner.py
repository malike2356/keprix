"""Tests for mutation pruning (Prompt 154)."""

from __future__ import annotations

import textwrap
from datetime import datetime, timedelta, timezone

import pytest

from keprix.mutation.config import get_mutation_settings
from keprix.mutation.pruner import MutationPruner

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
    get_mutation_settings.cache_clear()
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.mutation.store.get_session_factory", lambda: None)
    monkeypatch.setenv("KEPRIX_TOOL_SIGNING_KEY", str(tmp_path / "signing.pem"))
    monkeypatch.setenv("KEPRIX_TOOL_VERIFY_KEY", str(tmp_path / "verify.pem"))
    monkeypatch.setenv("KEPRIX_MUTATION_GENERATED_TOOLS_DIR", str(tmp_path / "generated"))
    monkeypatch.setenv("KEPRIX_MUTATION_PRUNE_AFTER_DAYS", "90")
    monkeypatch.setenv("KEPRIX_MUTATION_MAX_GENERATED_TOOLS", "2")
    from keprix.mutation.store import MutationStore

    store = MutationStore(sqlite_path=tmp_path / "mutation.db")
    monkeypatch.setattr("keprix.mutation.store._store", store)
    monkeypatch.setattr("keprix.mutation.store.get_mutation_store", lambda: store)
    return store, tmp_path


@pytest.fixture
def pruner(mutation_store):
    store, _tmp = mutation_store
    return MutationPruner(store=store)


def _old_timestamp(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def test_prunes_unused_low_score_tool(pruner, mutation_store, monkeypatch):
    store, tmp_path = mutation_store
    record = store.save_generated_tool(
        workspace_id="default",
        tool_name="stale_tool",
        description="Stale",
        source_code=_VALID_TOOL.replace("demo_tool", "stale_tool"),
        trigger="test",
        confidence=0.95,
        auto_approve_threshold=0.85,
    )
    store.write_tool_to_disk(record, tmp_path / "generated")
    old = _old_timestamp(120)
    with store._sqlite_conn() as conn:
        conn.execute(
            "UPDATE mutation_events SET quality_score = ?, last_used_at = ? WHERE id = ?",
            (0.2, old.isoformat(), record.id),
        )
        conn.commit()

    pruned = pruner.prune_unused_tools()
    assert "stale_tool" in pruned
    updated = store.get_generated_tool(record.id)
    assert updated is not None
    assert updated.status == "pruned"


def test_does_not_prune_high_score_tool(pruner, mutation_store):
    store, _tmp = mutation_store
    record = store.save_generated_tool(
        workspace_id="default",
        tool_name="healthy_tool",
        description="Healthy",
        source_code=_VALID_TOOL.replace("demo_tool", "healthy_tool"),
        trigger="test",
        confidence=0.95,
        auto_approve_threshold=0.85,
    )
    old = _old_timestamp(120)
    with store._sqlite_conn() as conn:
        conn.execute(
            "UPDATE mutation_events SET quality_score = ?, last_used_at = ? WHERE id = ?",
            (0.9, old.isoformat(), record.id),
        )
        conn.commit()

    pruned = pruner.prune_unused_tools()
    assert "healthy_tool" not in pruned
    updated = store.get_generated_tool(record.id)
    assert updated is not None
    assert updated.status == "approved"


def test_prunes_stale_staged_mutation(pruner, mutation_store):
    store, _tmp = mutation_store
    record = store.save_generated_tool(
        workspace_id="default",
        tool_name="staged_tool",
        description="Staged",
        source_code=_VALID_TOOL.replace("demo_tool", "staged_tool"),
        trigger="test",
        confidence=0.5,
        auto_approve_threshold=0.85,
    )
    old = _old_timestamp(45)
    with store._sqlite_conn() as conn:
        conn.execute(
            "UPDATE mutation_events SET recorded_at = ? WHERE id = ?",
            (old.isoformat(), record.id),
        )
        conn.commit()

    expired = pruner.prune_stale_staged()
    assert record.id in expired
    updated = store.get_generated_tool(record.id)
    assert updated is not None
    assert updated.status == "expired"


def test_prune_excess_removes_lowest_score_first(pruner, mutation_store):
    store, _tmp = mutation_store
    tools = []
    for index, score in enumerate((0.9, 0.4, 0.7), start=1):
        record = store.save_generated_tool(
            workspace_id="default",
            tool_name=f"tool_{index}",
            description=f"Tool {index}",
            source_code=_VALID_TOOL.replace("demo_tool", f"tool_{index}"),
            trigger="test",
            confidence=0.95,
            auto_approve_threshold=0.85,
        )
        store.update_mutation_usage(record.id, quality_score=score, use_count=index)
        tools.append(record)

    pruned = pruner.prune_excess_tools()
    assert "tool_2" in pruned
    assert store.get_generated_tool(tools[1].id).status == "pruned"


def test_dry_run_does_not_modify(pruner, mutation_store):
    store, tmp_path = mutation_store
    record = store.save_generated_tool(
        workspace_id="default",
        tool_name="dry_run_tool",
        description="Dry run",
        source_code=_VALID_TOOL.replace("demo_tool", "dry_run_tool"),
        trigger="test",
        confidence=0.95,
        auto_approve_threshold=0.85,
    )
    store.write_tool_to_disk(record, tmp_path / "generated")
    old = _old_timestamp(120)
    with store._sqlite_conn() as conn:
        conn.execute(
            "UPDATE mutation_events SET quality_score = ?, last_used_at = ? WHERE id = ?",
            (0.1, old.isoformat(), record.id),
        )
        conn.commit()

    report = pruner.run_full_prune(dry_run=True)
    assert report.total_pruned >= 1
    updated = store.get_generated_tool(record.id)
    assert updated is not None
    assert updated.status == "approved"
    assert (tmp_path / "generated" / "dry_run_tool.py").exists()


def test_full_prune_returns_report(pruner, mutation_store):
    report = pruner.run_full_prune()
    assert report.total_pruned == len(report.pruned_tools) + len(report.pruned_prompts) + len(report.pruned_code)
