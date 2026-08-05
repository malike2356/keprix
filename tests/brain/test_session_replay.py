from datetime import datetime, timezone
from pathlib import Path

import pytest

from keprix.brain.session_replay import SessionReplayService
from keprix.data_architecture.graph_edges import add_graph_edge
from keprix.workspace.repository import workspace_repo


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))


@pytest.mark.asyncio
async def test_session_replay_builds_messages_and_activations() -> None:
    user = {"id": "user-1", "workspace_id": "replay-ws"}
    workspace_id = "replay-ws"
    session = workspace_repo.create_session(user, "Invoice query chat")
    session_id = session["id"]
    workspace_repo.append_message(
        user,
        session_id,
        {
            "role": "user",
            "content": [{"type": "text", "content": "Can you send the invoice?"}],
            "createdAt": datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc).isoformat(),
        },
    )
    workspace_repo.append_message(
        user,
        session_id,
        {
            "role": "assistant",
            "content": [{"type": "text", "content": "Sure, pulling the invoice template now."}],
            "createdAt": datetime(2026, 1, 15, 10, 0, 5, tzinfo=timezone.utc).isoformat(),
        },
    )
    add_graph_edge(
        workspace_id=workspace_id,
        source_kind="memory",
        source_id="mem-invoice",
        target_kind="session",
        target_id=session_id,
        relation="memory_retrieved",
        metadata={"activation_type": "memory_retrieved", "confidence": 0.94},
    )

    data = await SessionReplayService().build(user, workspace_id, session_id)

    assert data.session_title == "Invoice query chat"
    assert len(data.messages) == 2
    assert data.activation_count == 1
    assert data.has_brain_activity is True
    assert data.activations[0].node_id == "mem-invoice"
    assert data.activations[0].step == 1
    assert "memory:mem-invoice" in data.messages[1].activations_during


@pytest.mark.asyncio
async def test_session_replay_lists_sessions_with_activation_counts() -> None:
    user = {"id": "user-2", "workspace_id": "replay-ws-2"}
    workspace_id = "replay-ws-2"
    session = workspace_repo.create_session(user, "Tenant enquiry")
    add_graph_edge(
        workspace_id=workspace_id,
        source_kind="skill",
        source_id="send-invoice",
        target_kind="session",
        target_id=session["id"],
        relation="skill_fired",
    )

    sessions = await SessionReplayService().list_sessions(user, workspace_id)
    assert sessions[0]["activation_count"] == 1
    assert sessions[0]["title"] == "Tenant enquiry"
