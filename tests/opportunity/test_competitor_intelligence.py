"""Tests for the Competitor Intelligence playbook."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from keprix.opportunity.models import OpportunityRequest
from keprix.opportunity.orchestrator import run_opportunity_phase
from keprix.opportunity.playbooks.competitor_intelligence import (
    CompetitorIntelligenceInput,
    CompetitorRecord,
    is_private_source,
    merge_duplicate_competitors,
    run_competitor_intelligence_playbook,
    validate_competitor_citations,
)
from keprix.opportunity.playbooks.market_demand import MarketDemandInput, run_market_demand_playbook
from keprix.opportunity.playbooks.offer_builder import OfferBuilderInput, run_offer_builder_playbook
from keprix.opportunity.playbooks.pain_mining import PainMiningInput, run_pain_mining_playbook
from keprix.opportunity.playbooks.icp_builder import IcpBuilderInput, run_icp_builder_playbook
from keprix.opportunity.registry import reset_opportunity_registry
from keprix.opportunity.workspace import create_opportunity_workspace, read_artifact, read_opportunity_json
from keprix.security.rate_limiter import reset_rate_limits


@pytest.fixture
def opp_env(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(data_dir))
    reset_rate_limits()
    reset_opportunity_registry(base_dir=data_dir / "workspace" / "opportunities")
    return data_dir


def test_merge_duplicate_competitors_by_domain():
    rows = [
        CompetitorRecord(name="Acme", domain="acme.com", offer="A", citation_urls=["https://acme.com/a"]),
        CompetitorRecord(
            name="Acme Inc",
            domain="acme.com",
            offer="B",
            market_strength=80,
            citation_urls=["https://acme.com/b"],
        ),
    ]
    merged = merge_duplicate_competitors(rows)
    assert len(merged) == 1
    assert merged[0].market_strength == 80
    assert len(merged[0].citation_urls) == 2


def test_citation_enforcement_for_factual_claims():
    rows = [
        CompetitorRecord(
            name="No Cite Co",
            domain="nocite.com",
            offer="SaaS tool",
            pricing_signal="$99/mo",
            citation_urls=[],
        ),
    ]
    assert validate_competitor_citations(rows) == ["No Cite Co"]


def test_private_source_policy():
    assert is_private_source("members only content", "https://example.com/members")
    assert is_private_source("login required to view", "https://example.com/pricing")


@pytest.mark.asyncio
async def test_competitor_playbook_writes_report(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Comp Intel", niche="CRM for agencies", source="test"),
    )
    await run_market_demand_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=MarketDemandInput(niche="CRM for agencies", research_depth="standard"),
        title=workspace.title,
        goal="test",
    )
    meta = read_opportunity_json(workspace.opportunity_id)
    await run_pain_mining_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=PainMiningInput(
            demand_pocket=meta["recommended_demand_pocket"],
            niche="CRM for agencies",
            research_depth="standard",
        ),
    )
    await run_offer_builder_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=OfferBuilderInput(niche="CRM for agencies", title="Comp Intel", goal="test"),
    )
    await run_icp_builder_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=IcpBuilderInput(
            niche="CRM for agencies",
            offer_name="Comp Intel",
            who_it_is_for="Agencies",
        ),
    )
    report = await run_competitor_intelligence_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=CompetitorIntelligenceInput(
            niche="CRM for agencies",
            icp_summary="Agencies",
            offer_name="Comp Intel",
            research_depth="standard",
        ),
    )
    updated = read_opportunity_json(workspace.opportunity_id)
    assert len(updated["competitors"]) >= 5
    assert "## Competitor Map" in report
    assert "## Differentiation Opportunities" in report
    assert updated["differentiation_recommendation"]


@pytest.mark.asyncio
async def test_banned_domains_skipped(opp_env, monkeypatch):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Banned", niche="saas", source="test"),
    )
    monkeypatch.setattr(
        "keprix.opportunity.playbooks.competitor_intelligence.web_search",
        AsyncMock(
            return_value=[
                {
                    "title": "Bad Competitor",
                    "url": "https://banned.example.com/page",
                    "snippet": "pricing $99",
                },
                {
                    "title": "Good Competitor",
                    "url": "https://allowed.example.com/page",
                    "snippet": "CRM software",
                },
            ],
        ),
    )
    await run_competitor_intelligence_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=CompetitorIntelligenceInput(
            niche="saas",
            banned_domains=["banned.example.com"],
            research_depth="quick",
        ),
    )
    report = read_artifact(workspace.opportunity_id, "04-competitors.md")
    assert "banned.example.com" not in report


@pytest.mark.asyncio
async def test_orchestrator_competitor_phase(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Orch Comp", niche="proptech", source="test"),
    )
    for phase in ("market_demand", "pain_mining", "offer_builder", "icp_builder", "competitor_intelligence"):
        await run_opportunity_phase(workspace.opportunity_id, phase)
    artifact = read_artifact(workspace.opportunity_id, "04-competitors.md")
    assert "# Competitor Intelligence" in artifact
    assert "Unverified" in artifact or "citations" in artifact.lower()
