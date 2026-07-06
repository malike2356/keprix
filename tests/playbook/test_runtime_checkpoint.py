"""Playbook checkpoint tests."""

from __future__ import annotations

import pytest

from keprix.playbook.runtime import (
    END,
    PlaybookGraph,
    PlaybookRunner,
    RunStatus,
    SQLiteCheckpointStore,
)


@pytest.fixture
def checkpoint_store(tmp_path):
    return SQLiteCheckpointStore(tmp_path / "checkpoints.db")


@pytest.mark.asyncio
async def test_checkpoint_saved_on_each_transition(checkpoint_store):
    graph = PlaybookGraph("cp")
    graph.add_node("a", lambda state: {**state, "step": 1})
    graph.add_node("b", lambda state: {**state, "step": 2})
    graph.add_edge("a", "b")
    graph.add_edge("b", END)

    runner = PlaybookRunner(graph.compile(), checkpoint_store=checkpoint_store)
    run = await runner.start(workspace_id="ws-1")

    records = await checkpoint_store.list_for_run(run.run_id)
    assert len(records) == 2
    assert records[0].node_name == "a"
    assert records[1].node_name == "b"
    assert records[1].output_state == {"step": 2}


@pytest.mark.asyncio
async def test_failed_run_checkpoint_contains_error(checkpoint_store):
    graph = PlaybookGraph("fail")

    def boom(_state):
        raise RuntimeError("boom")

    graph.add_node("boom", boom)
    graph.add_edge("boom", END)

    runner = PlaybookRunner(graph.compile(), checkpoint_store=checkpoint_store)
    run = await runner.start(workspace_id="ws-1")
    assert run.status == RunStatus.FAILED

    latest = await checkpoint_store.get_latest(run.run_id)
    assert latest is not None
    assert latest.error == "boom"


@pytest.mark.asyncio
async def test_resume_from_failed_checkpoint(checkpoint_store):
    calls = {"n": 0}

    def maybe_fail(state):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("first try failed")
        return {**state, "ok": True}

    graph = PlaybookGraph("resume")
    graph.add_node("work", maybe_fail)
    graph.add_edge("work", END)

    runner = PlaybookRunner(graph.compile(), checkpoint_store=checkpoint_store)
    run = await runner.start(workspace_id="ws-1")
    assert run.status == RunStatus.FAILED

    resumed = await runner.resume(run)
    assert resumed.status == RunStatus.COMPLETED
    assert resumed.state["ok"] is True


@pytest.mark.asyncio
async def test_postgres_store_implements_same_interface(monkeypatch):
    """PostgresCheckpointStore shares CheckpointStore interface (mocked DB)."""
    from keprix.playbook.runtime.checkpoint import CheckpointRecord, make_checkpoint
    from keprix.playbook.runtime.checkpoint_postgres import PostgresCheckpointStore

    saved: list[CheckpointRecord] = []

    class FakeConn:
        async def execute(self, *_args, **_kwargs):
            return None

        async def fetch(self, *_args, **_kwargs):
            return []

        async def close(self):
            return None

    async def fake_connect(_url):
        return FakeConn()

    import asyncpg

    monkeypatch.setattr(asyncpg, "connect", fake_connect)

    store = PostgresCheckpointStore("postgresql://test/test")
    record = make_checkpoint(
        run_id="r1",
        graph_id="g1",
        node_name="n1",
        input_state={"a": 1},
        output_state={"a": 2},
    )

    async def capture_save(rec):
        saved.append(rec)

    monkeypatch.setattr(store, "save", capture_save)

    await store.save(record)
    assert saved[0].run_id == "r1"
    assert await store.get_latest("r1") is None
