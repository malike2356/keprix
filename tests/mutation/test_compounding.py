"""Tests for mutation compounding metrics (Prompt 154)."""

from __future__ import annotations

import textwrap

import pytest

from keprix.mutation.compounding import compute_compounding_metrics

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
    from keprix.mutation.store import MutationStore

    store = MutationStore(sqlite_path=tmp_path / "mutation.db")
    monkeypatch.setattr("keprix.mutation.store._store", store)
    monkeypatch.setattr("keprix.mutation.store.get_mutation_store", lambda: store)
    return store


def test_zero_divergence_for_new_workspace(mutation_store):
    metrics = compute_compounding_metrics("default")
    assert metrics.divergence_score == 0.0
    assert metrics.total_mutations == 0
    assert metrics.active_mutations == 0


def test_divergence_increases_with_tools(mutation_store):
    store = mutation_store
    for index in range(5):
        record = store.save_generated_tool(
            workspace_id="default",
            tool_name=f"tool_{index}",
            description="Demo",
            source_code=_VALID_TOOL.replace("demo_tool", f"tool_{index}"),
            trigger="test",
            confidence=0.95,
            auto_approve_threshold=0.85,
        )
        metadata = dict(record.metadata)
        metadata["promoted"] = True
        store.update_mutation_usage(record.id, quality_score=0.95, use_count=6, metadata=metadata)

    metrics = compute_compounding_metrics("default")
    assert metrics.divergence_score > 0.0
    assert metrics.active_mutations >= 5
    assert metrics.promoted_mutations >= 5
    assert metrics.tools_contributed >= 5


def test_divergence_increases_with_evolved_prompts(mutation_store):
    store = mutation_store
    store.save_mutation_event(
        workspace_id="default",
        tier="prompt",
        trigger="prompt_evolution",
        status="approved",
        name="default",
        description="Evolved prompt",
        after_value="new prompt",
    )
    metrics = compute_compounding_metrics("default")
    assert metrics.prompts_evolved >= 1
    assert metrics.divergence_score > 0.0


def test_divergence_increases_with_merged_code(mutation_store):
    store = mutation_store
    store.save_mutation_event(
        workspace_id="default",
        tier="code",
        trigger="self_coding",
        status="approved",
        name="fix-handler",
        description="Merged code mutation",
        source_code="diff content",
    )
    metrics = compute_compounding_metrics("default")
    assert metrics.code_mutations_merged >= 1
    assert metrics.divergence_score > 0.0
