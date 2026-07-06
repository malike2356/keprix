"""Tests for the Market Demand Discovery playbook."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from keprix.opportunity.models import OpportunityRequest
from keprix.opportunity.orchestrator import run_opportunity_phase
from keprix.opportunity.playbooks.market_demand import (
    DemandPocket,
    MarketDemandInput,
    ResearchSignal,
    _build_demand_pockets,
    _empty_search_fallback_pockets,
    compute_overall_demand_score,
    run_market_demand_playbook,
    validate_pockets_have_citations,
)
from keprix.opportunity.registry import reset_opportunity_registry
from keprix.opportunity.workspace import (
    create_opportunity_workspace,
    read_artifact,
    read_opportunity_json,
)
from keprix.security.rate_limiter import reset_rate_limits


@pytest.fixture
def opp_env(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(data_dir))
    reset_rate_limits()
    reset_opportunity_registry(base_dir=data_dir / "workspace" / "opportunities")
    return data_dir


def test_scoring_weights():
    overall = compute_overall_demand_score(
        urgency_score=100.0,
        evidence_score=100.0,
        willingness_to_pay_score=100.0,
        competition_gap_score=100.0,
    )
    assert overall == 100.0

    mixed = compute_overall_demand_score(
        urgency_score=60.0,
        evidence_score=40.0,
        willingness_to_pay_score=50.0,
        competition_gap_score=30.0,
    )
    expected = round((60 * 30 + 40 * 25 + 50 * 25 + 30 * 20) / 100, 1)
    assert mixed == expected


def test_missing_citations_downgrades_strong_pockets():
    pocket = DemandPocket(
        rank=1,
        name="Strong claim",
        buyer="SMB",
        pain="Manual workflows",
        urgency_score=80,
        evidence_score=80,
        willingness_to_pay_score=70,
        competition_gap_score=60,
        overall_demand_score=72.5,
        evidence_strength="Strong",
        monetisation_potential="High",
        citation_urls=[],
    )
    issues = validate_pockets_have_citations([pocket])
    assert issues == ["Strong claim"]


def test_empty_search_fallback_produces_weak_inference_pockets():
    inp = MarketDemandInput(niche="obscure niche xyz", research_depth="standard")
    pockets = _empty_search_fallback_pockets(inp)
    assert len(pockets) == 5
    assert all(p.evidence_strength == "Weak inference" for p in pockets)
    assert all(not p.citation_urls for p in pockets)


@pytest.mark.asyncio
async def test_standard_depth_produces_five_pockets(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(
            title="Estate Agent Automation",
            niche="AI automation for estate agents",
            research_depth="standard",
            source="test",
        ),
    )
    request = MarketDemandInput(
        niche="AI automation for estate agents",
        research_depth="standard",
    )
    report = await run_market_demand_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=request,
        title=workspace.title,
        goal=workspace.goal or workspace.title,
    )
    meta = read_opportunity_json(workspace.opportunity_id)
    assert len(meta["demand_pockets"]) >= 5
    assert meta["phase"] == "market_demand"
    assert meta["status"] == "researching"
    assert meta["recommended_demand_pocket"]
    assert "# Market Demand Discovery" in report
    assert "## Demand Pockets" in report
    assert "## Citations" in report
    assert "Weak inference" in report or len(meta.get("citations", [])) >= 1


@pytest.mark.asyncio
async def test_playbook_writes_artifact_and_citations(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Citation Test", niche="proptech CRM", source="test"),
    )
    await run_market_demand_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=MarketDemandInput(niche="proptech CRM", research_depth="standard"),
        title=workspace.title,
        goal="Validate demand",
    )
    artifact = read_artifact(workspace.opportunity_id, "01-market-demand.md")
    assert "## Recommended Opportunity To Explore Next" in artifact
    meta = read_opportunity_json(workspace.opportunity_id)
    pockets_with_cites = [p for p in meta["demand_pockets"] if p.get("citation_urls")]
    assert pockets_with_cites or any(
        p.get("evidence_strength") == "Weak inference" for p in meta["demand_pockets"]
    )


@pytest.mark.asyncio
async def test_empty_web_search_uses_fallback(opp_env, monkeypatch):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Empty Search", niche="niche with no data", source="test"),
    )
    monkeypatch.setattr(
        "keprix.opportunity.playbooks.market_demand.web_search",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "keprix.opportunity.playbooks.market_demand._gather_workspace_knowledge",
        AsyncMock(return_value=[]),
    )
    await run_market_demand_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=MarketDemandInput(niche="niche with no data", research_depth="standard"),
        title=workspace.title,
        goal="test",
    )
    meta = read_opportunity_json(workspace.opportunity_id)
    assert len(meta["demand_pockets"]) == 5
    assert all("fallback" in p.get("inference_note", "").lower() for p in meta["demand_pockets"])


@pytest.mark.asyncio
async def test_orchestrator_uses_playbook(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Orchestrator Hook", niche="legal tech", source="test"),
    )
    await run_opportunity_phase(workspace.opportunity_id, "market_demand")
    artifact = read_artifact(workspace.opportunity_id, "01-market-demand.md")
    assert "# Market Demand Discovery" in artifact


def test_build_pockets_from_signals_marks_inference():
    signals = [
        ResearchSignal(
            title="Short",
            url="https://example.com/a",
            snippet="tiny",
            source_kind="web_search",
        ),
    ]
    inp = MarketDemandInput(niche="test niche", research_depth="quick")
    pockets = _build_demand_pockets(signals, inp=inp)
    assert len(pockets) >= 3
    assert any(p.evidence_strength in {"Weak inference", "Moderate", "Strong"} for p in pockets)
