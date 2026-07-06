"""Tests for NEXUS orchestrator delegation and project tracking."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from keprix.multiagent.runtime import clear_messages, get_messages
from keprix.personas.nexus.orchestrator import NexusOrchestrator
from keprix.personas.nexus.project_tracker import Milestone, ProjectState


@pytest.fixture(autouse=True)
def _clear_message_log() -> None:
    clear_messages()
    yield
    clear_messages()


@pytest.fixture
def orchestrator() -> NexusOrchestrator:
    return NexusOrchestrator(workspace_id="ws-orch", run_id="run-orch")


@pytest.mark.asyncio
async def test_delegate_sends_message_to_forge(orchestrator: NexusOrchestrator) -> None:
    decision = orchestrator.route("Deploy the docker build pipeline")
    messages = await orchestrator.delegate(decision, "Deploy the docker build pipeline")
    assert len(messages) == 1
    assert messages[0].recipient == "FORGE"
    assert messages[0].sender == "NEXUS"


@pytest.mark.asyncio
async def test_coordinate_multi_uses_group_chat(orchestrator: NexusOrchestrator) -> None:
    decision = orchestrator.route("Research market trends and improve SEO ranking")
    assert decision.is_multi_domain()
    messages = await orchestrator.coordinate_multi(decision, "Coordinate research and SEO")
    recipients = {message.recipient for message in messages}
    assert "SAGE" in recipients or "PRISM" in recipients
    stored = get_messages(workspace_id="ws-orch", run_id="run-orch")
    assert len(stored) >= 1


def test_project_state_round_trip_playbook() -> None:
    state = ProjectState(
        workspace_id="ws-1",
        project_name="Launch",
        milestones=[Milestone(id="m1", title="Design", status="completed")],
        agent_status={"FORGE": "idle"},
    )
    restored = ProjectState.from_playbook_state(state.to_playbook_state())
    assert restored.project_name == "Launch"
    assert restored.milestones[0].title == "Design"


def test_detect_blockers_for_dependency(orchestrator: NexusOrchestrator) -> None:
    state = ProjectState(
        workspace_id="ws-1",
        milestones=[
            Milestone(id="m1", title="Research", status="pending"),
            Milestone(id="m2", title="Build", status="in_progress", dependencies=["m1"]),
        ],
    )
    blockers = orchestrator.detect_blockers(state.to_playbook_state())
    assert any(b["type"] == "dependency_blocked" for b in blockers)


def test_detect_blockers_for_past_deadline(orchestrator: NexusOrchestrator) -> None:
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    state = ProjectState(
        workspace_id="ws-1",
        milestones=[Milestone(id="m1", title="Ship", status="in_progress", deadline=past)],
    )
    blockers = orchestrator.detect_blockers(state.to_playbook_state())
    assert any(b["type"] == "deadline_passed" for b in blockers)


def test_escalate_returns_options(orchestrator: NexusOrchestrator) -> None:
    blockers = [{"type": "deadline_passed", "milestone_id": "m1", "title": "Ship"}]
    result = orchestrator.escalate(blockers)
    assert result["escalated"] is True
    assert len(result["options"]) >= 2


def test_status_report_includes_milestones() -> None:
    state = ProjectState(
        workspace_id="ws-1",
        project_name="Alpha",
        milestones=[Milestone(id="m1", title="Kickoff", status="in_progress", owner="NEXUS")],
    )
    report = state.generate_status_report()
    assert "Alpha" in report
    assert "Kickoff" in report
    assert "NEXUS" in report
