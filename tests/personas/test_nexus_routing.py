"""Tests for NEXUS routing decisions."""

from __future__ import annotations

import pytest

from keprix.personas.nexus.orchestrator import NexusOrchestrator


@pytest.fixture
def orchestrator() -> NexusOrchestrator:
    return NexusOrchestrator(workspace_id="ws-test", run_id="run-test")


def test_routes_code_request_to_forge(orchestrator: NexusOrchestrator) -> None:
    decision = orchestrator.route("Please refactor the API code and fix the bug")
    assert decision.primary_agent == "FORGE"
    assert decision.matched_agents == ["FORGE"]
    assert not decision.handled_by_nexus


def test_routes_security_request_to_warden(orchestrator: NexusOrchestrator) -> None:
    decision = orchestrator.route("Run a security audit for GDPR compliance")
    assert decision.primary_agent == "WARDEN"


def test_routes_status_request_to_nexus(orchestrator: NexusOrchestrator) -> None:
    decision = orchestrator.route("What is the overall project status and progress?")
    assert decision.primary_agent == "NEXUS"
    assert decision.handled_by_nexus


def test_routes_research_request_to_sage(orchestrator: NexusOrchestrator) -> None:
    decision = orchestrator.route("Research market intelligence on competitors")
    assert decision.primary_agent == "SAGE"


def test_routes_seo_request_to_prism(orchestrator: NexusOrchestrator) -> None:
    decision = orchestrator.route("Improve our SEO ranking and social media growth")
    assert decision.primary_agent == "PRISM"


def test_routes_strategy_request_to_compass(orchestrator: NexusOrchestrator) -> None:
    decision = orchestrator.route("Help us build a product roadmap and prioritise strategy")
    assert decision.primary_agent == "COMPASS"


def test_routes_wellbeing_request_to_ember(orchestrator: NexusOrchestrator) -> None:
    decision = orchestrator.route("I need help with stress and building a daily habit")
    assert decision.primary_agent == "EMBER"


def test_routes_contract_request_to_codex(orchestrator: NexusOrchestrator) -> None:
    decision = orchestrator.route("Review this NDA contract for liability and indemnity clauses")
    assert decision.primary_agent == "CODEX"


def test_routes_governance_request_to_scout(orchestrator: NexusOrchestrator) -> None:
    decision = orchestrator.route("Activate the kill switch and audit our governance policy compliance")
    assert decision.primary_agent == "SCOUT"


def test_routes_marketing_request_to_beacon(orchestrator: NexusOrchestrator) -> None:
    decision = orchestrator.route("Write landing page copy for our product launch campaign")
    assert decision.primary_agent == "BEACON"


def test_routes_receptionist_request_to_echo(orchestrator: NexusOrchestrator) -> None:
    decision = orchestrator.route("Please handle inbound phone calls and book appointments for callers")
    assert decision.primary_agent == "ECHO"


def test_ambiguous_request_handled_by_nexus(orchestrator: NexusOrchestrator) -> None:
    decision = orchestrator.route("Hello there")
    assert decision.primary_agent == "NEXUS"
    assert decision.handled_by_nexus
