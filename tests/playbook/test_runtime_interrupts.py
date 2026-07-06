"""Playbook interrupt and approval tests."""

from __future__ import annotations

import pytest

from keprix.playbook.runtime import (
    END,
    EventType,
    PlaybookGraph,
    PlaybookRunner,
    RunStatus,
    SQLiteCheckpointStore,
    interrupt,
    playbook_registry,
)


@pytest.fixture
def checkpoint_store(tmp_path):
    return SQLiteCheckpointStore(tmp_path / "checkpoints.db")


@pytest.mark.asyncio
async def test_interrupt_pauses_for_approval(checkpoint_store):
    graph = PlaybookGraph("approval")

    def gate(state):
        if not state.get("approved"):
            interrupt(
                "spending money requires approval",
                approval_request={"risk": "spend_money", "amount": state.get("amount", 0)},
            )
        return {**state, "spent": True}

    graph.add_node("gate", gate)
    graph.add_edge("gate", END)

    runner = PlaybookRunner(graph.compile(), checkpoint_store=checkpoint_store)
    run = await runner.start(workspace_id="ws-1", initial_state={"amount": 50})

    assert run.status == RunStatus.WAITING_FOR_APPROVAL
    assert run.approval_request == {"risk": "spend_money", "amount": 50}

    events = runner.events.list_events(run.run_id)
    assert EventType.APPROVAL_REQUESTED in [event.event_type for event in events]


@pytest.mark.asyncio
async def test_interrupt_without_approval(checkpoint_store):
    graph = PlaybookGraph("plain-interrupt")

    def gate(state):
        if not state.get("continue"):
            interrupt("operator review required")
        return {**state, "done": True}

    graph.add_node("gate", gate)
    graph.add_edge("gate", END)

    runner = PlaybookRunner(graph.compile(), checkpoint_store=checkpoint_store)
    run = await runner.start(workspace_id="ws-1")
    assert run.status == RunStatus.INTERRUPTED

    resumed = await runner.resume(run, state_patch={"continue": True})
    assert resumed.status == RunStatus.COMPLETED
    assert resumed.state["done"] is True


@pytest.mark.asyncio
async def test_cancelled_run_via_registry(checkpoint_store):
    graph = PlaybookGraph("cancel")

    def gate(state):
        if not state.get("done"):
            interrupt("hold for cancel test")
        return {**state, "done": True}

    graph.add_node("gate", gate)
    graph.add_edge("gate", END)

    runner = PlaybookRunner(graph.compile(), checkpoint_store=checkpoint_store)
    run = await runner.start(workspace_id="ws-1")
    playbook_registry.register(run, runner)
    assert run.status == RunStatus.INTERRUPTED

    cancelled = await playbook_registry.cancel(run.run_id)
    assert cancelled.status == RunStatus.CANCELLED


@pytest.mark.asyncio
async def test_approval_resume_via_registry(checkpoint_store):
    graph = PlaybookGraph("approval-resume")

    def gate(state):
        if not state.get("approved"):
            interrupt(
                "payment requires approval",
                approval_request={"risk": "spend_money"},
            )
        return {**state, "paid": True}

    graph.add_node("gate", gate)
    graph.add_edge("gate", END)

    runner = PlaybookRunner(graph.compile(), checkpoint_store=checkpoint_store)
    run = await runner.start(workspace_id="ws-1")
    playbook_registry.register(run, runner)

    completed = await playbook_registry.resume(
        run.run_id,
        state_patch={"approved": True},
        approved_by="operator",
    )
    assert completed.status == RunStatus.COMPLETED
    assert completed.state["paid"] is True
