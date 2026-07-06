"""Tests for Launch Orchestrator playbook."""

from __future__ import annotations

import pytest

from keprix.opportunity.models import OpportunityRequest
from keprix.opportunity.orchestrator import run_opportunity_phase
from keprix.opportunity.playbooks.asset_factory import run_asset_factory_playbook
from keprix.opportunity.playbooks.launch_orchestrator import (
    LaunchBlockedError,
    render_rollback_plan,
    run_launch_plan,
    run_launch_orchestrator_playbook,
)
from keprix.opportunity.playbooks.offer_builder import OfferBuilderInput, run_offer_builder_playbook
from keprix.opportunity.playbooks.offer_doc_generator import run_offer_doc_generator_playbook
from keprix.opportunity.playbooks.validation_score import run_validation_score_playbook
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


async def _prepare_launch_ready(opp_id: str, workspace_id: str = "default") -> None:
    await run_offer_builder_playbook(
        workspace_id=workspace_id,
        opportunity_id=opp_id,
        request=OfferBuilderInput(niche="saas", title="Launch Ready", goal="soft launch"),
    )
    await run_validation_score_playbook(workspace_id=workspace_id, opportunity_id=opp_id)
    await run_offer_doc_generator_playbook(workspace_id=workspace_id, opportunity_id=opp_id)
    update_opportunity_json(opp_id, {"validation_override": True})
    await run_asset_factory_playbook(workspace_id=workspace_id, opportunity_id=opp_id)


@pytest.mark.asyncio
async def test_dry_run_returns_planned_actions(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Dry Run", niche="saas", goal="validate launch", source="test"),
    )
    await _prepare_launch_ready(workspace.opportunity_id, workspace.workspace_id)

    result = await run_launch_plan(workspace.opportunity_id, dry_run=True)

    assert result.dry_run is True
    assert len(result.actions) >= 8
    assert all(row.status in {"dry_run", "pending_connector"} for row in result.actions)
    assert "Launch Plan" in result.launch_plan_md
    assert "## Rollback Plan" in result.launch_plan_md
    assert result.approvals_requested


@pytest.mark.asyncio
async def test_missing_connector_fallback(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Missing Connectors", niche="saas", source="test"),
    )
    await _prepare_launch_ready(workspace.opportunity_id, workspace.workspace_id)

    result = await run_launch_plan(workspace.opportunity_id, dry_run=True)

    assert result.integration_report.missing
    assert result.integration_report.pending_tasks
    assert any(row.status == "pending_connector" for row in result.actions)
    assert "Missing Integrations" in result.launch_plan_md
    plan = await run_launch_orchestrator_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
    )
    assert "Pending connector task" in plan or "Connect" in plan


@pytest.mark.asyncio
async def test_approval_required_blocks_execution(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Approval Block", niche="saas", source="test"),
    )
    await _prepare_launch_ready(workspace.opportunity_id, workspace.workspace_id)
    update_opportunity_json(
        workspace.opportunity_id,
        {"integrations_config": {"email": True, "crm": True, "ads": True, "website": True, "stripe": True, "social": True}},
    )

    with pytest.raises(LaunchBlockedError):
        await run_launch_plan(workspace.opportunity_id, dry_run=False)


@pytest.mark.asyncio
async def test_rollback_plan_generation():
    from keprix.opportunity.playbooks.offer_doc_generator import build_canonical_offer_from_meta

    doc = build_canonical_offer_from_meta({"title": "Rollback Test", "niche": "saas"})
    rollback = render_rollback_plan(doc=doc)
    assert "Pause" in rollback
    assert "Stripe" in rollback


@pytest.mark.asyncio
async def test_approval_log_written(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Approval Log", niche="saas", source="test"),
    )
    await _prepare_launch_ready(workspace.opportunity_id, workspace.workspace_id)

    await run_opportunity_phase(workspace.opportunity_id, "launch_orchestrator")
    log = read_artifact(workspace.opportunity_id, "13-approval-log.md")
    assert "publish_landing_page" in log or "create_ad" in log
    assert "Risk level" in log
    assert read_artifact(workspace.opportunity_id, "11-launch-plan.md")
