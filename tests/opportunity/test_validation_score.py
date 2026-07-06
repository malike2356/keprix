"""Tests for the Validation Score playbook."""

from __future__ import annotations

import pytest

from keprix.opportunity.models import OpportunityRequest
from keprix.opportunity.orchestrator import run_opportunity_phase
from keprix.opportunity.playbooks.offer_builder import OfferBuilderInput, run_offer_builder_playbook
from keprix.opportunity.playbooks.offer_doc_generator import run_offer_doc_generator_playbook
from keprix.opportunity.playbooks.validation_score import (
    CategoryScore,
    ValidationScoreInput,
    compute_validation_result,
    compute_weighted_overall,
    recommendation_from_score,
    run_validation_score_playbook,
    should_block_asset_generation,
)
from keprix.opportunity.registry import reset_opportunity_registry
from keprix.opportunity.workspace import (
    create_opportunity_workspace,
    read_artifact,
    read_opportunity_json,
    update_opportunity_json,
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


def test_weighted_scoring_uses_weights():
    categories = [
        CategoryScore(
            category="demand_strength",
            label="Demand strength",
            score=100.0,
            weight=15,
            evidence="e",
            improvement="i",
        ),
        CategoryScore(
            category="pain_urgency",
            label="Pain urgency",
            score=0.0,
            weight=15,
            evidence="e",
            improvement="i",
        ),
    ]
    overall = compute_weighted_overall(categories)
    assert overall == 15.0


def test_threshold_decisions():
    assert recommendation_from_score(85) == "Proceed"
    assert recommendation_from_score(70) == "Revise offer"
    assert recommendation_from_score(50) == "Gather more evidence"
    assert recommendation_from_score(30) == "Do not launch"


def test_blocks_asset_generation_below_65():
    assert should_block_asset_generation(64.9) is True
    assert should_block_asset_generation(65.0) is False
    assert should_block_asset_generation(40.0, user_override=True) is False


def test_malformed_inputs_low_score():
    result = compute_validation_result(meta={}, artifacts={})
    assert result.overall_score < 45
    assert result.evidence_gaps
    assert result.recommendation == "Do not launch"


@pytest.mark.asyncio
async def test_validation_playbook_writes_report(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Validation", niche="saas", source="test"),
    )
    await run_validation_score_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
    )
    report = read_artifact(workspace.opportunity_id, "12-validation-score.md")
    meta = read_opportunity_json(workspace.opportunity_id)
    assert "## Overall Score" in report
    assert "## Recommendation" in report
    assert meta["validation"]["overall_score"] >= 0
    assert meta["validation"]["recommendation"]


@pytest.mark.asyncio
async def test_override_logging(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Override", niche="saas", source="test"),
    )
    await run_validation_score_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=ValidationScoreInput(user_override=True, override_by="tester", override_reason="manual"),
    )
    meta = read_opportunity_json(workspace.opportunity_id)
    assert meta["validation"]["override_applied"] is True
    assert meta["validation"]["asset_generation_blocked"] is False


@pytest.mark.asyncio
async def test_asset_factory_blocked_without_override(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Block Test", niche="x", source="test"),
    )
    await run_offer_builder_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=OfferBuilderInput(niche="x", title="Block Test", goal="test"),
    )
    await run_validation_score_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
    )
    await run_offer_doc_generator_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
    )
    result = await run_opportunity_phase(workspace.opportunity_id, "asset_factory")
    assert result.get("blocked") is True


@pytest.mark.asyncio
async def test_asset_factory_allowed_with_override(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Override Assets", niche="x", source="test"),
    )
    await run_offer_builder_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=OfferBuilderInput(niche="x", title="Override Assets", goal="test"),
    )
    await run_validation_score_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=ValidationScoreInput(user_override=True, override_by="tester"),
    )
    await run_offer_doc_generator_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
    )
    update_opportunity_json(
        workspace.opportunity_id,
        {"validation_override": True},
    )
    result = await run_opportunity_phase(
        workspace.opportunity_id,
        "asset_factory",
        {"validation_override": True},
    )
    assert not result.get("blocked")
