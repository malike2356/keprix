"""Tests for Crew: delegation, dependency ordering, failed task retry."""

from __future__ import annotations

import pytest

from keprix.teams.agent_role import AgentRole
from keprix.teams.crew import Crew, CrewError
from keprix.teams.task import RetryPolicy, TeamTask


def _task(task_id: str, *, role: str = "builder", dependencies: list[str] | None = None, **kwargs) -> TeamTask:
    return TeamTask(
        id=task_id,
        description=f"Task {task_id}",
        role=role,
        dependencies=dependencies or [],
        **kwargs,
    )


@pytest.mark.asyncio
async def test_dependency_ordering_respects_dag() -> None:
    crew = Crew(
        name="ordering",
        tasks=[
            _task("c", dependencies=["a", "b"]),
            _task("b", dependencies=["a"]),
            _task("a"),
        ],
    )
    ordered_ids = [t.id for t in crew.order_tasks()]
    assert ordered_ids.index("a") < ordered_ids.index("b")
    assert ordered_ids.index("b") < ordered_ids.index("c")


@pytest.mark.asyncio
async def test_cycle_detection_raises() -> None:
    crew = Crew(
        name="cycle",
        tasks=[
            _task("a", dependencies=["b"]),
            _task("b", dependencies=["a"]),
        ],
    )
    with pytest.raises(CrewError, match="cycle"):
        crew.order_tasks()


@pytest.mark.asyncio
async def test_run_completes_all_tasks() -> None:
    crew = Crew(
        name="run",
        tasks=[_task("first"), _task("second", dependencies=["first"])],
    )
    state = await crew.run("test objective")
    assert "first" in state["task_results"]
    assert "second" in state["task_results"]


@pytest.mark.asyncio
async def test_delegation_routes_to_qa_reviewer() -> None:
    delegating_builder = AgentRole(
        name="builder",
        goal="Build things",
        backstory="Builder with delegation enabled",
        delegation_policy="allowed",
    )
    qa_role = AgentRole(name="qa_reviewer", goal="Review quality", backstory="QA expert")
    call_log: list[str] = []

    def logging_executor(role, task, state):
        call_log.append(role.name)
        return {"reviewed": True}

    crew = Crew(
        name="delegation",
        roles={"builder": delegating_builder, "qa_reviewer": qa_role},
        tasks=[_task("do_review", allow_delegation=True)],
        executor=logging_executor,
    )
    state = await crew.run("review docs")
    result = state["task_results"]["do_review"]
    assert result["delegated_to"] == "qa_reviewer"
    assert "qa_reviewer" in call_log


@pytest.mark.asyncio
async def test_failed_task_retries_up_to_max_attempts() -> None:
    call_count = [0]

    def flaky_executor(role, task, state):
        call_count[0] += 1
        if call_count[0] < 2:
            raise RuntimeError("transient failure")
        return {"recovered": True}

    crew = Crew(
        name="retry",
        tasks=[
            _task("flaky", retry_policy=RetryPolicy(max_attempts=2)),
        ],
        executor=flaky_executor,
    )
    state = await crew.run("retry test")
    assert state["task_results"]["flaky"]["attempts"] == 2


@pytest.mark.asyncio
async def test_task_fails_after_exhausting_retries() -> None:
    def always_fail(role, task, state):
        raise RuntimeError("always fails")

    crew = Crew(
        name="exhaust",
        tasks=[_task("broken", retry_policy=RetryPolicy(max_attempts=2))],
        executor=always_fail,
    )
    with pytest.raises(CrewError, match="failed after"):
        await crew.run("will fail")


@pytest.mark.asyncio
async def test_missing_dependency_raises() -> None:
    crew = Crew(
        name="missing_dep",
        tasks=[_task("dependent", dependencies=["nonexistent"])],
    )
    with pytest.raises(CrewError, match="Unknown task dependency"):
        crew.order_tasks()
