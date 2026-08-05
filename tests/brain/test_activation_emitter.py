import asyncio

import pytest

from keprix.brain.activation_bus import ActivationBus
from keprix.brain.activation_emitter import ActivationEmitter, ActivationEventType
from keprix.data_architecture.graph_edges import list_graph_edges


@pytest.mark.asyncio
async def test_activation_bus_drops_full_queues() -> None:
    bus = ActivationBus()
    queue = bus.subscribe("workspace-a")

    for index in range(120):
        await bus.publish("workspace-a", {"session_id": "s1", "node_id": str(index)})

    assert queue.qsize() == 100
    bus.unsubscribe("workspace-a", queue)


@pytest.mark.asyncio
async def test_activation_emitter_publishes_and_persists_edge(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    workspace_id = "activation-test"
    emitter = ActivationEmitter()

    from keprix.brain.activation_bus import activation_bus

    queue = activation_bus.subscribe(workspace_id)
    try:
        await emitter.emit(
            ActivationEventType.TOOL_CALLED,
            workspace_id=workspace_id,
            session_id="session-1",
            node_kind="tool",
            node_id="send_email",
            relation="called_in_session",
            confidence=0.88,
        )

        event = await asyncio.wait_for(queue.get(), timeout=1)
        assert event["type"] == "tool_called"
        assert event["session_id"] == "session-1"
        assert event["node_kind"] == "tool"

        edges = list_graph_edges(workspace_id=workspace_id, source_kind="tool", source_id="send_email")
        assert edges[0]["target_kind"] == "session"
        assert edges[0]["target_id"] == "session-1"
        assert edges[0]["relation"] == "called_in_session"
        assert edges[0]["metadata"]["activation_type"] == "tool_called"
    finally:
        activation_bus.unsubscribe(workspace_id, queue)
