"""Agent-as-tool tests (Prompt 58)."""

from __future__ import annotations

import pytest

from keprix.backend.multiagent.agent_tool import AgentTool
from keprix.backend.multiagent.runtime import clear_messages, get_messages


@pytest.fixture(autouse=True)
def _clean():
    clear_messages()
    yield
    clear_messages()


@pytest.mark.asyncio
async def test_agent_tool_invokes_specialist():
    tool = AgentTool("researcher", workspace_id="ws-1", caller="coordinator")
    result = await tool.call("Summarize market trends")
    assert result.agent_id == "researcher"
    assert "researcher" in result.output.lower()
    messages = get_messages(run_id=tool.run_id)
    assert any(message.message_type.value == "tool" for message in messages)
    assert any(message.sender == "researcher" for message in messages)


@pytest.mark.asyncio
async def test_unknown_agent_tool_raises():
    tool = AgentTool("missing_agent")
    with pytest.raises(KeyError):
        await tool.call("test")
