"""Playbook graph execution tests."""

from __future__ import annotations

import pytest

from keprix.playbook.runtime import (
    END,
    EventType,
    PlaybookGraph,
    PlaybookRunner,
    RunStatus,
    SQLiteCheckpointStore,
)


@pytest.fixture
def checkpoint_store(tmp_path):
    return SQLiteCheckpointStore(tmp_path / "checkpoints.db")


@pytest.mark.asyncio
async def test_linear_graph_runs_to_completion(checkpoint_store):
    graph = PlaybookGraph("linear")
    graph.add_node("a", lambda state: {**state, "a": True})
    graph.add_node("b", lambda state: {**state, "b": True})
    graph.add_edge("a", "b")
    graph.add_edge("b", END)

    runner = PlaybookRunner(graph.compile(), checkpoint_store=checkpoint_store)
    run = await runner.start(workspace_id="ws-1", initial_state={})

    assert run.status == RunStatus.COMPLETED
    assert run.state == {"a": True, "b": True}


@pytest.mark.asyncio
async def test_conditional_branching(checkpoint_store):
    graph = PlaybookGraph("branch")
    graph.add_node("start", lambda state: {**state, "value": 2})
    graph.add_node("even", lambda state: {**state, "path": "even"})
    graph.add_node("odd", lambda state: {**state, "path": "odd"})
    graph.add_edge(
        "start",
        "even",
        condition=lambda s: "even" if s.get("value", 0) % 2 == 0 else False,
    )
    graph.add_edge(
        "start",
        "odd",
        condition=lambda s: "odd" if s.get("value", 0) % 2 == 1 else False,
    )
    graph.add_edge("even", END)
    graph.add_edge("odd", END)

    runner = PlaybookRunner(graph.compile(), checkpoint_store=checkpoint_store)
    run = await runner.start(workspace_id="ws-1")
    assert run.state["path"] == "even"


@pytest.mark.asyncio
async def test_subgraph_execution(checkpoint_store):
    inner = PlaybookGraph("inner")
    inner.add_node("x", lambda state: {**state, "x": 1})
    inner.add_edge("x", END)

    outer = PlaybookGraph("outer")
    outer.add_subgraph("sub", inner)
    outer.add_edge("sub", END)

    runner = PlaybookRunner(outer.compile(), checkpoint_store=checkpoint_store)
    run = await runner.start(workspace_id="ws-1")
    assert run.status == RunStatus.COMPLETED
    assert run.state["x"] == 1


@pytest.mark.asyncio
async def test_opportunity_engine_phase_graph(checkpoint_store):
    graph = PlaybookGraph("opportunity-engine")
    for phase in ("discover", "validate", "score", "publish"):
        graph.add_node(
            phase,
            lambda state, name=phase: {**state, "phases": [*state.get("phases", []), name]},
        )

    graph.add_edge("discover", "validate")
    graph.add_edge("validate", "score")
    graph.add_edge("score", "publish")
    graph.add_edge("publish", END)

    runner = PlaybookRunner(graph.compile(), checkpoint_store=checkpoint_store)
    run = await runner.start(workspace_id="opp-1")
    assert run.state["phases"] == ["discover", "validate", "score", "publish"]


@pytest.mark.asyncio
async def test_events_stream_in_order(checkpoint_store):
    graph = PlaybookGraph("events")
    graph.add_node("a", lambda state: state)
    graph.add_edge("a", END)

    runner = PlaybookRunner(graph.compile(), checkpoint_store=checkpoint_store)
    run = await runner.start(workspace_id="ws-1")
    types = [event.event_type for event in runner.events.list_events(run.run_id)]
    assert types == [
        EventType.RUN_STARTED,
        EventType.NODE_STARTED,
        EventType.NODE_COMPLETED,
        EventType.COMPLETED,
    ]
