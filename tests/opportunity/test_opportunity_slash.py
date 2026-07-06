"""Tests for Opportunity slash command parsing and execution."""

from __future__ import annotations

import pytest

from keprix.opportunity.models import OpportunityRequest
from keprix.opportunity.registry import reset_opportunity_registry
from keprix.opportunity.slash import execute_opportunity_slash, parse_opportunity_slash
from keprix.security.rate_limiter import reset_rate_limits


@pytest.fixture
def opp_env(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(data_dir))
    reset_rate_limits()
    reset_opportunity_registry(base_dir=data_dir / "workspace" / "opportunities")
    return data_dir


def test_parse_find_demand():
    intent = parse_opportunity_slash(
        "find demand for AI automation in UK estate agencies",
    )
    assert intent.action == "find_demand"
    assert "estate" in intent.niche.lower()
    assert intent.dry_run is True


def test_parse_run_phase_alias():
    intent = parse_opportunity_slash("run market-demand for property maintenance SaaS")
    assert intent.action == "run_phase"
    assert intent.phase == "market_demand"


def test_parse_prepare_launch_dry_run():
    intent = parse_opportunity_slash("prepare launch plan but do not publish")
    assert intent.action == "prepare_launch"
    assert intent.dry_run is True


def test_parse_needs_clarification():
    intent = parse_opportunity_slash("find demand")
    assert intent.needs_clarification is True


@pytest.mark.asyncio
async def test_slash_execution_creates_workspace(opp_env):
    result = await execute_opportunity_slash(
        parse_opportunity_slash("find demand for legal tech SaaS"),
        workspace_id="default",
        user_id="slash-user",
    )
    assert "opp-" in result.summary
    assert result.payload.get("opportunity_id")


@pytest.mark.asyncio
async def test_slash_reuses_existing_opportunity(opp_env):
    from keprix.opportunity.registry import get_opportunity_registry

    registry = get_opportunity_registry()
    workspace = registry.create(
        user_id="slash-user",
        request=OpportunityRequest(title="Existing", niche="saas", source="test"),
    )

    result = await execute_opportunity_slash(
        parse_opportunity_slash(f"status {workspace.opportunity_id}"),
        workspace_id="default",
        user_id="slash-user",
    )
    assert workspace.opportunity_id in result.summary
