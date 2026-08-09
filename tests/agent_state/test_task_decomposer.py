"""Unit tests for 5-7 step task chunking."""

from __future__ import annotations

from keprix.agent_state.context_state import ContextStateStore
from keprix.agent_state.task_decomposer import TaskDecomposer, decompose, plan_chunk_sizes


def test_plan_chunk_sizes_thirty_steps_five_chunks():
    sizes = plan_chunk_sizes(30)
    assert len(sizes) == 5
    assert sum(sizes) == 30
    assert all(5 <= size <= 7 for size in sizes)


def test_decompose_thirty_step_plan():
    steps = [f"Step {i}" for i in range(1, 31)]
    chunks = decompose("Thirty step plan", steps=steps)
    assert len(chunks) <= 5
    assert len(chunks) == 5
    assert all(5 <= len(c.steps) <= 7 for c in chunks)
    assert sum(len(c.steps) for c in chunks) == 30
    assert chunks[1].dependencies == ["chunk-01"]
    assert chunks[0].context_snapshot == {}


def test_decomposer_writes_chunks_to_state(tmp_path):
    store = ContextStateStore(root=tmp_path)
    store.create_state_file(
        "d1",
        "Plan",
        steps=[f"Work item {i}" for i in range(1, 19)],
    )
    state = TaskDecomposer(store).decompose("d1")
    assert len(state.chunks) >= 3
    assert all(c.context_snapshot.get("session_id") == "d1" for c in state.chunks)
    assert all(s.chunk_id for s in state.pending)
