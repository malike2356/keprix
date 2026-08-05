"""Playbook runtime event payload tests (Prompt 209)."""

from __future__ import annotations

import pytest

from keprix.playbook.runtime import END, EventType, PlaybookGraph, PlaybookRunner, RunStatus
from keprix.playbook.runtime.event_payload import truncate_state


@pytest.mark.asyncio
async def test_node_completed_event_includes_io_and_duration():
    graph = PlaybookGraph("io-events")
    graph.add_node("prepare", lambda state: {**state, "prepare_output": "ready"})
    graph.add_edge("prepare", END)

    runner = PlaybookRunner(graph.compile())
    run = await runner.start(workspace_id="ws-io", initial_state={"topic": "demo"})

    assert run.status == RunStatus.COMPLETED
    completed = [
        event
        for event in runner.events.list_events(run.run_id)
        if event.event_type == EventType.NODE_COMPLETED
    ]
    assert len(completed) == 1
    payload = completed[0].payload
    assert payload["node"] == "prepare"
    assert payload["input_state"] == {"topic": "demo"}
    assert payload["output_state"] == {"topic": "demo", "prepare_output": "ready"}
    assert isinstance(payload["duration_ms"], int)
    assert payload["duration_ms"] >= 0


@pytest.mark.asyncio
async def test_node_failed_event_includes_input_and_error():
    graph = PlaybookGraph("fail-events")

    def _boom(_state):
        raise RuntimeError("step failed")

    graph.add_node("boom", _boom)
    graph.add_edge("boom", END)

    runner = PlaybookRunner(graph.compile())
    run = await runner.start(workspace_id="ws-fail", initial_state={"seed": 1})

    assert run.status == RunStatus.FAILED
    failed = [
        event
        for event in runner.events.list_events(run.run_id)
        if event.event_type == EventType.NODE_FAILED
    ]
    assert len(failed) == 1
    payload = failed[0].payload
    assert payload["node"] == "boom"
    assert payload["input_state"] == {"seed": 1}
    assert payload["error"] == "step failed"
    assert isinstance(payload["duration_ms"], int)


def test_truncate_state_returns_preview_when_large():
    large = {"blob": "x" * 40000}
    truncated = truncate_state(large, max_bytes=1024)
    assert truncated["_truncated"] is True
    assert "preview" in truncated
    assert truncated["byte_size"] > 1024
