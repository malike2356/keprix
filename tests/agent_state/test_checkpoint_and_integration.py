"""Checkpoint gates and multi-session chunk integration."""

from __future__ import annotations

import json

import pytest

from keprix.agent_state.checkpoint_validator import (
    CheckpointBlockedError,
    CheckpointValidator,
)
from keprix.agent_state.context_state import ContextStateStore
from keprix.agent_state.task_decomposer import TaskDecomposer
from keprix.tools.agent_state_tool import agent_state_tool


def _complete_chunk_steps(store: ContextStateStore, session_id: str, chunk_id: str) -> None:
    state = store.require_state(session_id)
    for step in list(state.in_progress) + list(state.pending):
        if step.chunk_id == chunk_id or step.id in {
            s for c in state.chunks if c.id == chunk_id for s in c.steps
        }:
            store.update_state_file(
                session_id,
                step_id=step.id,
                status="completed",
                output=f"done {step.id}",
                files_changed=[f"{step.id}.py"],
            )


def test_checkpoint_blocks_until_human_approves(tmp_path):
    store = ContextStateStore(root=tmp_path)
    store.create_state_file(
        "gate",
        "Chunked work",
        steps=[f"S{i}" for i in range(1, 16)],
    )
    TaskDecomposer(store).decompose("gate")
    validator = CheckpointValidator(store)
    state = store.require_state("gate")
    chunk_a = state.chunks[0].id
    validator.start_chunk("gate", chunk_a)
    _complete_chunk_steps(store, "gate", chunk_a)

    paused = validator.pause_for_review("gate", chunk_a)
    assert paused["can_proceed"] is False
    assert "what_was_built" in paused["summary"]
    assert "next_chunk_preview" in paused["summary"]
    assert "files_changed" in paused["summary"]
    assert "decisions_made" in paused["summary"]

    with pytest.raises(CheckpointBlockedError):
        validator.start_chunk("gate", state.chunks[1].id)

    with pytest.raises(CheckpointBlockedError):
        validator.merge_approved_chunk("gate", chunk_a)

    validator.approve("gate", chunk_a, human_signal="looks good")
    merged = validator.merge_approved_chunk("gate", chunk_a)
    assert merged.chunks[0].status == "merged"
    assert merged.checkpoint.status == "none"

    # Next chunk can start
    validator.start_chunk("gate", merged.chunks[1].id)


def test_rollback_restores_prior_checkpoint(tmp_path):
    store = ContextStateStore(root=tmp_path)
    store.create_state_file("rb", "Rollback demo", steps=[f"S{i}" for i in range(1, 8)])
    TaskDecomposer(store).decompose("rb")
    validator = CheckpointValidator(store)
    chunk_id = store.require_state("rb").chunks[0].id
    before = store.require_state("rb").snapshot()
    validator.start_chunk("rb", chunk_id)
    store.update_state_file(
        "rb",
        step_id="step-001",
        status="completed",
        output="mutated",
        decision="bad decision",
    )
    restored = validator.rollback_chunk("rb", chunk_id)
    assert restored.last_completed_step_id == before.get("last_completed_step_id")
    assert all(s.status != "completed" or s.id != "step-001" for s in restored.completed) or not restored.completed
    # Snapshot had no completed steps
    assert len(restored.completed) == len(before["completed"])


def test_three_chunk_task_across_session_breaks(tmp_path):
    """Execute a 3-chunk task with simulated session breaks between chunks."""
    store = ContextStateStore(root=tmp_path)
    steps = [f"Work step {i}" for i in range(1, 16)]  # -> 3 chunks of 5
    store.create_state_file("journey", "Three chunk journey", steps=steps)
    state = TaskDecomposer(store).decompose("journey")
    assert len(state.chunks) == 3
    assert all(len(c.steps) == 5 for c in state.chunks)

    validator = CheckpointValidator(store)

    for index, chunk in enumerate(list(state.chunks)):
        # Simulate new session: read resume payload only
        resume = store.resume("journey")
        assert resume["can_proceed"] is True or index == 0
        injection = store.format_for_injection("journey")
        assert injection is not None

        # Fresh validator/store handles (new "session")
        store2 = ContextStateStore(root=tmp_path)
        validator2 = CheckpointValidator(store2)
        if index > 0:
            # Prior chunk must already be merged
            prior = store2.require_state("journey").chunks[index - 1]
            assert prior.status == "merged"

        validator2.start_chunk("journey", chunk.id)
        _complete_chunk_steps(store2, "journey", chunk.id)
        store2.update_state_file(
            "journey",
            decision=f"Decision after {chunk.id}",
        )
        paused = validator2.pause_for_review("journey", chunk.id)
        assert paused["can_proceed"] is False
        assert paused["summary"]["next_chunk_preview"] is not None or index == 2

        # Human approval in a third "session"
        store3 = ContextStateStore(root=tmp_path)
        validator3 = CheckpointValidator(store3)
        with pytest.raises(CheckpointBlockedError):
            validator3.assert_can_proceed("journey")
        validator3.approve("journey", chunk.id, human_signal=f"approve-{chunk.id}")
        validator3.merge_approved_chunk("journey", chunk.id)

    final = store.require_state("journey")
    assert all(c.status == "merged" for c in final.chunks)
    assert len(final.completed) == 15
    # State remains JSON-parseable
    json.loads(store.state_path("journey").read_text(encoding="utf-8"))


def test_agent_state_tool_roundtrip(tmp_path):
    sid = "tool-sess"
    created = json.loads(
        agent_state_tool(
            "create",
            sid,
            task_description="Via tool",
            steps=[f"T{i}" for i in range(1, 12)],
            base_dir=str(tmp_path),
        )
    )
    assert created["ok"] is True
    decomposed = json.loads(
        agent_state_tool("decompose", sid, base_dir=str(tmp_path))
    )
    assert decomposed["ok"] is True
    chunk_id = decomposed["chunks"][0]["id"]
    started = json.loads(
        agent_state_tool("start_chunk", sid, chunk_id=chunk_id, base_dir=str(tmp_path))
    )
    assert started["ok"] is True
    for step_id in decomposed["chunks"][0]["steps"]:
        updated = json.loads(
            agent_state_tool(
                "update",
                sid,
                step_id=step_id,
                status="completed",
                output="ok",
                base_dir=str(tmp_path),
            )
        )
        assert updated["ok"] is True
    paused = json.loads(
        agent_state_tool(
            "pause_for_review", sid, chunk_id=chunk_id, base_dir=str(tmp_path)
        )
    )
    assert paused["can_proceed"] is False
    blocked = json.loads(
        agent_state_tool(
            "start_chunk",
            sid,
            chunk_id=decomposed["chunks"][1]["id"],
            base_dir=str(tmp_path),
        )
    )
    assert blocked.get("error") or blocked.get("ok") is False
    approved = json.loads(
        agent_state_tool(
            "approve",
            sid,
            chunk_id=chunk_id,
            human_signal="ship it",
            base_dir=str(tmp_path),
        )
    )
    assert approved["ok"] is True
    merged = json.loads(
        agent_state_tool("merge", sid, chunk_id=chunk_id, base_dir=str(tmp_path))
    )
    assert merged["ok"] is True
