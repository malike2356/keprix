"""Tests for the Pain Mining playbook."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from keprix.opportunity.models import OpportunityRequest
from keprix.opportunity.orchestrator import run_opportunity_phase
from keprix.opportunity.playbooks.market_demand import MarketDemandInput, run_market_demand_playbook
from keprix.opportunity.playbooks.pain_mining import (
    MarketPain,
    PainMiningInput,
    rank_pains,
    run_pain_mining_playbook,
    sanitize_quote,
    validate_pain_citations,
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


def test_sanitize_quote_strips_pii():
    raw = 'Contact john@example.com or 555-123-4567 about "manual chaos"'
    cleaned = sanitize_quote(raw, source="forum")
    assert "john@example.com" not in cleaned
    assert "555-123-4567" not in cleaned
    assert "[redacted-email]" in cleaned
    assert "(forum)" in cleaned


def test_sanitize_quote_truncates_long_text():
    long_text = "x" * 200
    cleaned = sanitize_quote(long_text, source="reddit")
    assert len(cleaned) <= 140
    assert "..." in cleaned
    assert "(reddit)" in cleaned


def test_pain_ranking_orders_by_urgency_score():
    pains = [
        MarketPain(
            rank=1,
            pain="Low",
            exact_language="a",
            evidence="Moderate",
            urgency="Low",
            business_cost="Low",
            urgency_score=20,
        ),
        MarketPain(
            rank=2,
            pain="High",
            exact_language="b",
            evidence="Strong",
            urgency="High",
            business_cost="High",
            urgency_score=90,
        ),
    ]
    ranked = rank_pains(pains)
    assert ranked[0].pain == "High"
    assert ranked[0].rank == 1


def test_citation_requirements_flag_strong_without_url():
    pains = [
        MarketPain(
            rank=1,
            pain="Uncited strong claim",
            exact_language="quote",
            evidence="Strong",
            urgency="High",
            business_cost="High",
            urgency_score=80,
            citation_url="",
        ),
    ]
    assert validate_pain_citations(pains) == ["Uncited strong claim"]


@pytest.mark.asyncio
async def test_standard_produces_seven_pains(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Pain Test", niche="legal tech", research_depth="standard", source="test"),
    )
    await run_market_demand_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=MarketDemandInput(niche="legal tech", research_depth="standard"),
        title=workspace.title,
        goal="Find pains",
    )
    meta = read_opportunity_json(workspace.opportunity_id)
    pocket = meta["recommended_demand_pocket"]
    report = await run_pain_mining_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=PainMiningInput(
            demand_pocket=pocket,
            niche="legal tech",
            research_depth="standard",
        ),
    )
    updated = read_opportunity_json(workspace.opportunity_id)
    assert len(updated["top_pains"]) >= 7
    assert updated["phase"] == "pain_mining"
    assert updated["messaging_angles"]
    assert "## Top Market Pains" in report
    assert "## Compliance And Ethical Risks" in report


@pytest.mark.asyncio
async def test_reads_selected_demand_pocket_from_phase_one(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Pocket Link", niche="fintech", source="test"),
    )
    await run_market_demand_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=MarketDemandInput(niche="fintech", research_depth="standard"),
        title=workspace.title,
        goal="test",
    )
    meta = read_opportunity_json(workspace.opportunity_id)
    await run_pain_mining_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=PainMiningInput(
            demand_pocket=meta["recommended_demand_pocket"],
            niche="fintech",
            research_depth="standard",
        ),
    )
    artifact = read_artifact(workspace.opportunity_id, "02-pain-mining.md")
    assert meta["recommended_demand_pocket"] in artifact


@pytest.mark.asyncio
async def test_orchestrator_pain_mining_phase(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Orchestrator Pain", niche="edtech", source="test"),
    )
    await run_opportunity_phase(workspace.opportunity_id, "market_demand")
    await run_opportunity_phase(workspace.opportunity_id, "pain_mining")
    artifact = read_artifact(workspace.opportunity_id, "02-pain-mining.md")
    assert "# Pain Mining" in artifact
    assert "## Messaging Angles" in artifact


@pytest.mark.asyncio
async def test_empty_search_fallback_marks_inference(opp_env, monkeypatch):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Empty Pain Search", niche="obscure", source="test"),
    )
    monkeypatch.setattr(
        "keprix.opportunity.playbooks.pain_mining.web_search",
        AsyncMock(return_value=[]),
    )
    await run_pain_mining_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=PainMiningInput(
            demand_pocket="obscure segment",
            niche="obscure",
            research_depth="standard",
        ),
    )
    meta = read_opportunity_json(workspace.opportunity_id)
    assert len(meta["top_pains"]) >= 7
    assert all(p.get("is_inference") for p in meta["top_pains"])
