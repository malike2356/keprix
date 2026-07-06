"""Message runtime tests (Prompt 58)."""

from __future__ import annotations

import pytest

from keprix.backend.multiagent.message import AgentMessage, MessageType
from keprix.backend.multiagent.runtime import clear_messages, get_messages, get_run_events, send_message


@pytest.fixture(autouse=True)
def _clean():
    clear_messages()
    yield
    clear_messages()


@pytest.mark.asyncio
async def test_send_message_records_structured_fields():
    message = await send_message(
        AgentMessage(
            sender="coordinator",
            recipient="researcher",
            workspace_id="ws-1",
            run_id="run-1",
            content="Find sources on AI safety",
            message_type=MessageType.AGENT,
            artifact_refs=["brief.md"],
        )
    )
    assert message.trace_id
    stored = get_messages(run_id="run-1")[0]
    assert stored.recipient == "researcher"
    assert stored.artifact_refs == ["brief.md"]
    events = get_run_events("run-1")
    assert events and events[0]["type"] == "message_sent"


@pytest.mark.asyncio
async def test_message_routing_filters_by_workspace():
    await send_message(
        AgentMessage(
            sender="a",
            recipient="b",
            workspace_id="ws-a",
            run_id="run-a",
            content="one",
        )
    )
    await send_message(
        AgentMessage(
            sender="a",
            recipient="b",
            workspace_id="ws-b",
            run_id="run-b",
            content="two",
        )
    )
    assert len(get_messages(workspace_id="ws-a")) == 1
    assert get_messages(workspace_id="ws-a")[0].content == "one"
