"""Tests for the ICP Builder playbook."""

from __future__ import annotations

import pytest

from keprix.opportunity.models import OpportunityRequest
from keprix.opportunity.orchestrator import run_opportunity_phase
from keprix.opportunity.playbooks.icp_builder import (
    IcpBuilderInput,
    build_icp_profiles,
    run_icp_builder_playbook,
    validate_no_predatory_targeting,
)
from keprix.opportunity.playbooks.market_demand import MarketDemandInput, run_market_demand_playbook
from keprix.opportunity.playbooks.offer_builder import OfferBuilderInput, run_offer_builder_playbook
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


async def _seed_through_offer(workspace):
    await run_market_demand_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=MarketDemandInput(niche="healthcare ops", research_depth="standard"),
        title=workspace.title,
        goal="Build ICP",
    )
    meta = read_opportunity_json(workspace.opportunity_id)
    await run_pain_mining_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=PainMiningInput(
            demand_pocket=meta["recommended_demand_pocket"],
            niche="healthcare ops",
            research_depth="standard",
        ),
    )
    await run_offer_builder_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=OfferBuilderInput(
            niche="healthcare ops",
            title=workspace.title,
            goal="Build ICP",
        ),
    )


def test_predatory_targeting_blocked():
    assert validate_no_predatory_targeting("Use predatory targeting on vulnerable users")


def test_icp_profiles_include_primary_and_two_secondary():
    inp = IcpBuilderInput(
        niche="healthcare",
        offer_name="Ops Playbook",
        who_it_is_for="Clinic operators",
        pains=["Manual scheduling"],
    )
    primary, secondary = build_icp_profiles(inp)
    assert primary.is_primary
    assert len(secondary) >= 2


@pytest.mark.asyncio
async def test_icp_builder_writes_profile(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="ICP Test", niche="healthcare ops", source="test"),
    )
    await _seed_through_offer(workspace)
    await run_icp_builder_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=IcpBuilderInput(
            niche="healthcare ops",
            offer_name="ICP Test",
            who_it_is_for="Clinic operators",
            pains=["Manual scheduling"],
        ),
    )
    icp = read_artifact(workspace.opportunity_id, "03-icp.md")
    meta = read_opportunity_json(workspace.opportunity_id)
    assert "## Primary ICP" in icp
    assert "## Secondary ICPs" in icp
    assert "## Disqualification Criteria" in icp
    assert "Compliance" in icp
    assert len(meta["icp"]["secondary"]) >= 2
    assert meta["status"] == "approval_required"


@pytest.mark.asyncio
async def test_orchestrator_icp_builder_phase(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Orch ICP", niche="edtech", source="test"),
    )
    await run_opportunity_phase(workspace.opportunity_id, "market_demand")
    await run_opportunity_phase(workspace.opportunity_id, "pain_mining")
    await run_opportunity_phase(workspace.opportunity_id, "offer_builder")
    await run_opportunity_phase(workspace.opportunity_id, "icp_builder")
    icp = read_artifact(workspace.opportunity_id, "03-icp.md")
    assert "# Ideal Customer Profile" in icp
    assert "Disqualification" in icp
