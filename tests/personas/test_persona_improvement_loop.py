"""Persona orchestration wired to the Agno-style improvement loop."""

from __future__ import annotations

import pytest

from keprix.multiagent.runtime import clear_messages
from keprix.personas.improvement_hook import record_persona_run, record_routing_outcome
from keprix.personas.nexus.orchestrator import NexusOrchestrator
from keprix.personas.registry import get_persona_registry


@pytest.fixture(autouse=True)
def _clear_message_log() -> None:
    clear_messages()
    yield
    clear_messages()


def test_persona_registry_includes_prompts_96_through_103() -> None:
    registry = get_persona_registry()
    expected = {"NEXUS", "FORGE", "WARDEN", "SAGE", "BEACON", "PRISM", "COMPASS", "EMBER"}
    assert expected.issubset(set(registry.list_names()))


def test_failed_persona_run_creates_improvement_proposal(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "keprix.improvement.run_analyzer._runs_dir",
        lambda: tmp_path / "runs",
    )
    monkeypatch.setattr(
        "keprix.improvement.run_analyzer._proposals_dir",
        lambda: tmp_path / "proposals",
    )
    (tmp_path / "runs").mkdir()
    (tmp_path / "proposals").mkdir()

    proposals = record_persona_run(
        run_id="persona-fail-1",
        agent_id="FORGE",
        ok=False,
        steps=[{"name": "review", "ok": False}],
    )
    assert proposals
    assert proposals[0].category == "repeated_failure"
    assert proposals[0].agent_id == "FORGE"


def test_routing_outcome_records_nexus_delegation(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "keprix.improvement.run_analyzer._runs_dir",
        lambda: tmp_path / "runs",
    )
    monkeypatch.setattr(
        "keprix.improvement.run_analyzer._proposals_dir",
        lambda: tmp_path / "proposals",
    )
    (tmp_path / "runs").mkdir()
    (tmp_path / "proposals").mkdir()

    proposals = record_routing_outcome(
        run_id="route-1",
        primary_agent="FORGE",
        matched_agents=["FORGE"],
        message_count=1,
        metadata={"reason": "Matched FORGE domain keywords"},
    )
    assert proposals == []


@pytest.mark.asyncio
async def test_multi_domain_delegation_records_improvement_metadata(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "keprix.improvement.run_analyzer._runs_dir",
        lambda: tmp_path / "runs",
    )
    monkeypatch.setattr(
        "keprix.improvement.run_analyzer._proposals_dir",
        lambda: tmp_path / "proposals",
    )
    (tmp_path / "runs").mkdir()
    (tmp_path / "proposals").mkdir()

    orchestrator = NexusOrchestrator(workspace_id="ws", run_id="run-multi")
    decision = orchestrator.route("build the API and run a security audit")
    messages = await orchestrator.coordinate_multi(decision, "Coordinate build and audit")
    proposals = record_routing_outcome(
        run_id="run-multi",
        primary_agent=decision.primary_agent,
        matched_agents=decision.matched_agents,
        message_count=len(messages),
        metadata={"coordinate_multi": True},
    )
    assert len(messages) >= 1
    assert proposals == []
