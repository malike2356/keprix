"""Tests for TeamFlow: approval pause and graph compilation."""

from __future__ import annotations

import pytest

from keprix.playbook.runtime import PlaybookInterrupt
from keprix.teams.crew import Crew
from keprix.teams.flow import TeamFlow
from keprix.teams.task import TeamTask


def _crew_with_task(task: TeamTask) -> Crew:
    return Crew(name="flow-test", tasks=[task])


@pytest.mark.asyncio
async def test_human_review_task_raises_interrupt_when_not_approved() -> None:
    task = TeamTask(
        id="needs_review",
        description="approve this action",
        role="builder",
        human_review=True,
        risk_level="high",
    )
    crew = _crew_with_task(task)
    flow = TeamFlow(name="test", start="needs_review")
    graph = flow.compile_to_playbook(crew)
    handler = graph._nodes["needs_review"].handler

    with pytest.raises(PlaybookInterrupt) as exc_info:
        await handler({"objective": "test"})

    assert exc_info.value.approval_request["task_id"] == "needs_review"
    assert exc_info.value.approval_request["risk_level"] == "high"


@pytest.mark.asyncio
async def test_human_review_task_proceeds_when_approved() -> None:
    task = TeamTask(
        id="approved_task",
        description="approved action",
        role="builder",
        human_review=True,
    )
    crew = _crew_with_task(task)
    flow = TeamFlow(name="test", start="approved_task")
    graph = flow.compile_to_playbook(crew)
    handler = graph._nodes["approved_task"].handler

    state = await handler({"objective": "test", "approved_tasks": ["approved_task"]})
    assert "approved_task" in state["task_results"]


@pytest.mark.asyncio
async def test_flow_compiles_tasks_into_graph() -> None:
    tasks = [
        TeamTask(id="step_a", description="step a", role="builder"),
        TeamTask(id="step_b", description="step b", role="builder", dependencies=["step_a"]),
    ]
    crew = Crew(name="flow-compile", tasks=tasks)
    flow = TeamFlow(name="two-step", start="step_a")
    graph = flow.compile_to_playbook(crew)

    assert "step_a" in graph._nodes
    assert "step_b" in graph._nodes
    assert graph._entry == "step_a"


@pytest.mark.asyncio
async def test_unknown_start_task_raises() -> None:
    task = TeamTask(id="real_task", description="real", role="builder")
    crew = Crew(name="bad-start", tasks=[task])
    flow = TeamFlow(name="bad", start="nonexistent")

    with pytest.raises(ValueError, match="Unknown flow start"):
        flow.compile_to_playbook(crew)
