"""Tests for the Offer Builder playbook."""

from __future__ import annotations

import pytest

from keprix.opportunity.models import OpportunityRequest
from keprix.opportunity.orchestrator import run_opportunity_phase
from keprix.opportunity.playbooks.market_demand import MarketDemandInput, run_market_demand_playbook
from keprix.opportunity.playbooks.offer_builder import (
    OfferBuilderInput,
    build_offer_record,
    build_pricing_hypotheses,
    detect_regulated_industry,
    run_offer_builder_playbook,
    validate_no_false_proof,
    validate_no_guaranteed_income,
)
from keprix.opportunity.playbooks.pain_mining import PainMiningInput, run_pain_mining_playbook
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


async def _seed_workspace(workspace):
    await run_market_demand_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=MarketDemandInput(niche="legal tech SaaS", research_depth="standard"),
        title=workspace.title,
        goal="Validate offer",
    )
    meta = read_opportunity_json(workspace.opportunity_id)
    await run_pain_mining_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=PainMiningInput(
            demand_pocket=meta["recommended_demand_pocket"],
            niche="legal tech SaaS",
            research_depth="standard",
        ),
    )


def test_false_proof_prevention_without_assets():
    text = "Our case study shows customer achieved 300% ROI"
    violations = validate_no_false_proof(text, existing_assets=[])
    assert violations


def test_false_proof_allowed_with_assets():
    text = "See case study in customer achieved report"
    violations = validate_no_false_proof(text, existing_assets=["case-study.pdf"])
    assert not violations


def test_guaranteed_income_blocked():
    assert validate_no_guaranteed_income("Earn guaranteed income every month")


def test_regulated_industry_detection():
    assert detect_regulated_industry("HIPAA compliant healthcare platform")
    assert not detect_regulated_industry("coffee shop loyalty app")


def test_pricing_hypotheses_minimum_three():
    rows = build_pricing_hypotheses(niche="proptech", buyer="estate agents")
    assert len(rows) >= 3
    tiers = {row.tier for row in rows}
    assert "Starter" in tiers
    assert "Growth" in tiers


def test_offer_maps_to_pains():
    inp = OfferBuilderInput(niche="legal tech", title="Legal Ops", goal="Validate")
    offer = build_offer_record(
        inp=inp,
        pains=["Manual contract review", "Slow client intake"],
        demand_pocket="Mid-size law firms",
        regulated=True,
    )
    assert "Manual contract review" in offer.pain_it_solves[0]
    assert offer.compliance_notes


@pytest.mark.asyncio
async def test_offer_builder_writes_artifacts(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Offer Test", niche="legal tech SaaS", source="test"),
    )
    await _seed_workspace(workspace)
    await run_offer_builder_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=OfferBuilderInput(niche="legal tech SaaS", title="Offer Test", goal="Validate"),
    )
    offer_doc = read_artifact(workspace.opportunity_id, "05-offer-doc.md")
    pricing = read_artifact(workspace.opportunity_id, "06-pricing.md")
    meta = read_opportunity_json(workspace.opportunity_id)
    assert "## Pain It Solves" in offer_doc
    assert "## Pricing Hypotheses" in pricing
    assert len(meta["pricing"]["hypotheses"]) >= 3
    assert meta["offer"]["offer_name"]


@pytest.mark.asyncio
async def test_orchestrator_offer_builder_phase(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Orch Offer", niche="fintech", source="test"),
    )
    await run_opportunity_phase(workspace.opportunity_id, "market_demand")
    await run_opportunity_phase(workspace.opportunity_id, "pain_mining")
    await run_opportunity_phase(workspace.opportunity_id, "offer_builder")
    offer_doc = read_artifact(workspace.opportunity_id, "05-offer-doc.md")
    assert "# Offer Doc" in offer_doc
