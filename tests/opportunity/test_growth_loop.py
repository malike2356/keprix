"""Tests for Growth Loop playbook."""

from __future__ import annotations

import pytest

from keprix.opportunity.models import OpportunityRequest
from keprix.opportunity.orchestrator import run_opportunity_phase
from keprix.opportunity.playbooks.growth_loop import (
    GrowthLoopInput,
    build_manual_import_template,
    rank_experiments,
    run_growth_loop_playbook,
    suggest_experiments,
    validate_growth_guardrails,
)
from keprix.opportunity.playbooks.offer_doc_generator import build_canonical_offer_from_meta
from keprix.opportunity.playbooks.offer_builder import OfferBuilderInput, run_offer_builder_playbook
from keprix.opportunity.playbooks.offer_doc_generator import run_offer_doc_generator_playbook
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


@pytest.mark.asyncio
async def test_missing_integrations_produce_manual_import(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Growth Manual", niche="saas", source="test"),
    )
    await run_offer_builder_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=OfferBuilderInput(niche="saas", title="Growth Manual", goal="monitor"),
    )
    await run_offer_doc_generator_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
    )

    result = await run_growth_loop_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
    )

    assert result.manual_import_required is True
    assert "Manual Data Import" in result.report_md
    assert "Visits" in result.report_md
    assert build_manual_import_template().count("| Metric |") >= 1


def test_experiment_ranking_orders_by_score():
    doc = build_canonical_offer_from_meta({"title": "Rank Test", "niche": "saas"})
    metrics = []
    experiments = suggest_experiments(doc=doc, metrics=metrics)
    ranked = rank_experiments(experiments)
    scores = [row.rank_score for row in ranked]
    assert scores == sorted(scores, reverse=True)
    assert ranked[0].rank_score >= ranked[-1].rank_score


@pytest.mark.asyncio
async def test_approval_gating_for_live_changes(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Growth Approvals", niche="saas", source="test"),
    )
    await run_offer_builder_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=OfferBuilderInput(niche="saas", title="Growth Approvals", goal="monitor"),
    )
    await run_offer_doc_generator_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
    )

    result = await run_growth_loop_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
    )

    assert result.approvals_requested
    assert any(row.approval_required for row in result.experiments)
    log = read_artifact(workspace.opportunity_id, "13-approval-log.md")
    assert "publish_landing_page" in log or "send_email_sequence" in log


@pytest.mark.asyncio
async def test_updates_opportunity_json_growth_status(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Growth Status", niche="saas", source="test"),
    )
    await run_offer_builder_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=OfferBuilderInput(niche="saas", title="Growth Status", goal="monitor"),
    )
    await run_offer_doc_generator_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
    )

    await run_opportunity_phase(workspace.opportunity_id, "growth_loop")
    meta = read_opportunity_json(workspace.opportunity_id)
    assert meta.get("growth_status") == "monitoring"
    assert meta.get("growth", {}).get("ranked_experiments")
    report = read_artifact(workspace.opportunity_id, "14-growth-loop.md")
    assert "## Recommended Experiments" in report
    assert "## Next Review Date" in report


def test_guardrails_flag_deceptive_targeting():
    violations = validate_growth_guardrails("Use deceptive targeting on lookalike audiences")
    assert violations
