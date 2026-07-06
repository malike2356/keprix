"""Group chat policy tests (Prompt 58)."""

from __future__ import annotations

import pytest

from keprix.backend.multiagent.group_chat import GroupChat, GroupChatPolicy
from keprix.backend.multiagent.runtime import clear_messages, get_messages
from keprix.backend.multiagent.workbench import McpServerConfig, get_mcp_workbench


@pytest.fixture(autouse=True)
def _clean():
    clear_messages()
    get_mcp_workbench().clear()
    yield
    clear_messages()
    get_mcp_workbench().clear()


@pytest.mark.asyncio
async def test_round_robin_targets_one_participant_per_turn():
    chat = GroupChat(
        participants=["coordinator", "researcher", "analyst"],
        supervisor="coordinator",
        policy=GroupChatPolicy.ROUND_ROBIN,
        workspace_id="ws-1",
        run_id="run-rr",
    )
    first = await chat.dispatch("Task one")
    second = await chat.dispatch("Task two")
    assert len(first) == 1
    assert len(second) == 1
    assert first[0].recipient != second[0].recipient


@pytest.mark.asyncio
async def test_supervisor_moderated_broadcasts_to_non_supervisor():
    chat = GroupChat(
        participants=["coordinator", "researcher", "analyst"],
        supervisor="coordinator",
        policy=GroupChatPolicy.SUPERVISOR_MODERATED,
        workspace_id="ws-1",
        run_id="run-sup",
    )
    messages = await chat.dispatch("Review plan")
    recipients = {message.recipient for message in messages}
    assert "researcher" in recipients
    assert "analyst" in recipients
    assert any(message.message_type.value == "system" for message in messages)


@pytest.mark.asyncio
async def test_vote_decide_collects_votes():
    chat = GroupChat(
        participants=["coordinator", "researcher", "analyst"],
        supervisor="coordinator",
        policy=GroupChatPolicy.VOTE_DECIDE,
        workspace_id="ws-1",
        run_id="run-vote",
    )
    messages = await chat.dispatch("Choose approach A or B")
    assert any("vote" in (message.metadata or {}) for message in messages)
    assert any(message.message_type.value == "system" for message in messages)


@pytest.mark.asyncio
async def test_human_review_requires_approval_message():
    chat = GroupChat(
        participants=["coordinator", "researcher"],
        supervisor="coordinator",
        policy=GroupChatPolicy.HUMAN_REVIEW,
        workspace_id="ws-1",
        run_id="run-human",
    )
    messages = await chat.dispatch("Deploy to production")
    assert len(messages) == 1
    assert messages[0].recipient == "human_reviewer"
    assert messages[0].message_type.value == "approval"
    approval = await chat.approve_human_review(approved=True)
    assert approval.metadata.get("approved") is True


@pytest.mark.asyncio
async def test_mcp_workbench_blocks_dangerous_tool_without_approval():
    workbench = get_mcp_workbench()
    workbench.register_server(McpServerConfig(name="shell", trusted=True))
    result = await workbench.invoke_tool(
        agent_id="coordinator",
        server="shell",
        tool_name="run_command",
        params={"command": "rm -rf /"},
        workspace_id="ws-1",
        run_id="run-mcp",
        approved=False,
    )
    assert result["blocked"] is True
    approval_messages = [m for m in get_messages(run_id="run-mcp") if m.message_type.value == "approval"]
    assert approval_messages
