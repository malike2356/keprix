"""Tests for mutation_events store (Prompt 150)."""

from __future__ import annotations

import textwrap

import pytest

from keprix.mutation.store import MutationStore, get_mutation_store

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
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.mutation.store.get_session_factory", lambda: None)
    monkeypatch.setenv("KEPRIX_TOOL_SIGNING_KEY", str(tmp_path / "signing.pem"))
    monkeypatch.setenv("KEPRIX_TOOL_VERIFY_KEY", str(tmp_path / "verify.pem"))
    store = MutationStore(sqlite_path=tmp_path / "mutation.db")
    monkeypatch.setattr("keprix.mutation.store._store", store)
    return store, tmp_path


def test_save_auto_approves_above_threshold(mutation_store):
    store, _tmp = mutation_store
    record = store.save_generated_tool(
        workspace_id="default",
        tool_name="demo_tool",
        description="Demo",
        source_code=_VALID_TOOL,
        trigger="gap_detected",
        confidence=0.9,
        auto_approve_threshold=0.85,
    )
    assert record.status == "approved"
    assert record.approved_by == "auto"


def test_save_stages_below_threshold(mutation_store):
    store, _tmp = mutation_store
    record = store.save_generated_tool(
        workspace_id="default",
        tool_name="demo_tool",
        description="Demo",
        source_code=_VALID_TOOL,
        trigger="gap_detected",
        confidence=0.7,
        auto_approve_threshold=0.85,
    )
    assert record.status == "staged"
    assert record.approved_by is None


def test_write_tool_to_disk_atomic(mutation_store):
    store, tmp = mutation_store
    record = store.save_generated_tool(
        workspace_id="default",
        tool_name="demo_tool",
        description="Demo",
        source_code=_VALID_TOOL,
        trigger="gap_detected",
        confidence=0.9,
        auto_approve_threshold=0.85,
    )
    tools_dir = tmp / "tools"
    path = store.write_tool_to_disk(record, tools_dir)
    assert path.exists()
    assert path.read_text(encoding="utf-8") == _VALID_TOOL
    assert not (tools_dir / ".demo_tool.py.tmp").exists()


def test_load_tools_on_startup_restores_all_approved(mutation_store):
    store, tmp = mutation_store
    approved_source = _VALID_TOOL.replace("demo_tool", "startup_demo_tool").replace(
        "demo_tool_handler", "startup_demo_tool_handler"
    )
    store.save_generated_tool(
        workspace_id="default",
        tool_name="startup_demo_tool",
        description="Demo",
        source_code=approved_source,
        trigger="gap_detected",
        confidence=0.95,
        auto_approve_threshold=0.85,
    )
    staged_source = _VALID_TOOL.replace("demo_tool", "staged_tool").replace(
        "demo_tool_handler", "staged_tool_handler"
    )
    store.save_generated_tool(
        workspace_id="default",
        tool_name="staged_tool",
        description="Staged",
        source_code=staged_source,
        trigger="gap_detected",
        confidence=0.5,
        auto_approve_threshold=0.85,
    )
    tools_dir = tmp / "generated"
    count = store.load_tools_on_startup("default", tools_dir)
    assert count >= 1
    from tools.registry import registry

    assert registry.get_entry("startup_demo_tool") is not None


def test_rejected_tool_not_written_to_disk(mutation_store):
    store, tmp = mutation_store
    record = store.save_generated_tool(
        workspace_id="default",
        tool_name="demo_tool",
        description="Demo",
        source_code=_VALID_TOOL,
        trigger="gap_detected",
        confidence=0.5,
        auto_approve_threshold=0.85,
    )
    updated = store.update_status(record.id, "rejected", approved_by="admin")
    assert updated is not None
    assert updated.status == "rejected"
    with pytest.raises(ValueError):
        store.write_tool_to_disk(updated, tmp / "tools")
