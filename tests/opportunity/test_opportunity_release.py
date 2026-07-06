"""Release readiness and evaluation fixture tests for Opportunity Engine."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from keprix.opportunity.models import PHASE_ORDER
from keprix.opportunity.orchestrator import run_opportunity_phase, run_opportunity_pipeline
from keprix.opportunity.playbooks.launch_orchestrator import run_launch_plan
from keprix.opportunity.playbooks.offer_builder import detect_regulated_industry
from keprix.opportunity.workspace import create_opportunity_workspace, read_artifact, read_opportunity_json

ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs"
FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "opportunity"

EXPECTED_WALKTHROUGH_ARTIFACTS = [
    "01-market-demand.md",
    "02-pain-mining.md",
    "03-icp.md",
    "05-offer-doc.md",
    "06-pricing.md",
    "07-funnel.md",
    "08-content-assets.md",
    "09-ads.md",
    "10-sales-deck.md",
    "11-launch-plan.md",
    "12-validation-score.md",
    "14-growth-loop.md",
    "13-approval-log.md",
]

FIXTURE_FILES = [
    "estate-agents-request.json",
    "borehole-drilling-ghana-request.json",
    "cybersecurity-consultancy-request.json",
    "weak-demand-example.json",
    "regulated-healthcare-example.json",
]


def load_opportunity_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def opportunity_request_from_fixture(payload: dict):
    from keprix.opportunity.models import OpportunityRequest

    return OpportunityRequest(
        title=payload["title"],
        niche=payload.get("niche"),
        market=payload.get("market"),
        goal=payload.get("goal"),
        geography=payload.get("geography"),
        buyer_type=payload.get("buyer_type"),
        research_depth=payload.get("research_depth", "standard"),
        source="fixture",
    )


@pytest.mark.parametrize("filename", FIXTURE_FILES)
def test_evaluation_fixtures_exist(filename):
    assert (FIXTURES_DIR / filename).is_file()


@pytest.mark.parametrize("filename", FIXTURE_FILES)
def test_evaluation_fixtures_parse(filename):
    payload = load_opportunity_fixture(filename)
    request = opportunity_request_from_fixture(payload)
    assert request.title


@pytest.mark.asyncio
async def test_estate_agents_dry_run_walkthrough(opp_env):
    payload = load_opportunity_fixture("estate-agents-request.json")
    workspace = create_opportunity_workspace(opportunity_request_from_fixture(payload))
    opp_id = workspace.opportunity_id

    await run_opportunity_pipeline(opp_id)

    for filename in EXPECTED_WALKTHROUGH_ARTIFACTS:
        assert read_artifact(opp_id, filename)

    launch_plan = read_artifact(opp_id, "11-launch-plan.md")
    assert "Launch Plan" in launch_plan
    assert "approval" in launch_plan.lower()

    log = read_artifact(opp_id, "13-approval-log.md")
    assert "Risk level" in log or "create_ad" in log or "publish_landing_page" in log

    meta = read_opportunity_json(opp_id)
    assert meta.get("launch_plan", {}).get("dry_run") is True or "dry run" in launch_plan.lower()


@pytest.mark.asyncio
async def test_african_market_fixture_runs_market_demand(opp_env):
    payload = load_opportunity_fixture("borehole-drilling-ghana-request.json")
    workspace = create_opportunity_workspace(opportunity_request_from_fixture(payload))
    await run_opportunity_phase(workspace.opportunity_id, "market_demand")
    content = read_artifact(workspace.opportunity_id, "01-market-demand.md")
    assert "Ghana" in content or "borehole" in content.lower()


@pytest.mark.asyncio
async def test_cybersecurity_fixture_runs_pain_mining(opp_env):
    payload = load_opportunity_fixture("cybersecurity-consultancy-request.json")
    workspace = create_opportunity_workspace(opportunity_request_from_fixture(payload))
    await run_opportunity_phase(workspace.opportunity_id, "market_demand")
    await run_opportunity_phase(workspace.opportunity_id, "pain_mining")
    content = read_artifact(workspace.opportunity_id, "02-pain-mining.md")
    assert "Pain" in content


@pytest.mark.asyncio
async def test_weak_demand_blocks_asset_factory(opp_env):
    payload = load_opportunity_fixture("weak-demand-example.json")
    workspace = create_opportunity_workspace(opportunity_request_from_fixture(payload))
    for phase in ("market_demand", "pain_mining", "offer_builder", "icp_builder", "competitor_intelligence", "validation_score", "offer_doc"):
        await run_opportunity_phase(workspace.opportunity_id, phase)
    result = await run_opportunity_phase(workspace.opportunity_id, "asset_factory")
    assert result.get("blocked") is True


def test_regulated_healthcare_fixture_flags_industry():
    payload = load_opportunity_fixture("regulated-healthcare-example.json")
    assert detect_regulated_industry(payload["niche"] + " " + payload.get("market", ""))


@pytest.mark.asyncio
async def test_approval_logging_after_launch_dry_run(opp_env):
    payload = load_opportunity_fixture("cybersecurity-consultancy-request.json")
    workspace = create_opportunity_workspace(opportunity_request_from_fixture(payload))
    for phase in ("market_demand", "offer_builder", "validation_score", "offer_doc"):
        await run_opportunity_phase(workspace.opportunity_id, phase)
    await run_launch_plan(workspace.opportunity_id, dry_run=True)
    log = read_artifact(workspace.opportunity_id, "13-approval-log.md")
    assert "|" in log
    assert "Detail" in log or "pending" in log.lower()


def test_release_docs_exist():
    required = [
        "opportunity-engine.md",
        "opportunity-engine-approval-policy.md",
        "opportunity-engine-integrations.md",
        "opportunity-engine-examples.md",
        "opportunity-engine-release-checklist.md",
    ]
    for name in required:
        assert (DOCS_DIR / name).is_file(), name


def test_release_docs_use_playbook_not_recipe():
    for name in (
        "opportunity-engine.md",
        "opportunity-engine-examples.md",
        "opportunity-engine-release-checklist.md",
    ):
        text = (DOCS_DIR / name).read_text(encoding="utf-8").lower()
        assert "playbook" in text
        assert "recipe" not in text


def test_release_docs_no_em_or_en_dashes():
    for path in DOCS_DIR.glob("opportunity-engine*.md"):
        body = path.read_text(encoding="utf-8")
        assert "\u2014" not in body
        assert "\u2013" not in body


def test_coverage_matrix_modules_importable():
    modules = [
        "tests.opportunity.test_opportunity_engine",
        "tests.opportunity.test_market_demand",
        "tests.opportunity.test_pain_mining",
        "tests.opportunity.test_offer_builder",
        "tests.opportunity.test_icp_builder",
        "tests.opportunity.test_competitor_intelligence",
        "tests.opportunity.test_validation_score",
        "tests.opportunity.test_asset_factory",
        "tests.opportunity.test_launch_orchestrator",
        "tests.opportunity.test_growth_loop",
        "tests.opportunity.test_opportunity_cli",
        "tests.opportunity.test_opportunity_slash",
        "tests.frontend.test_opportunity_surfaces",
    ]
    for module in modules:
        __import__(module)
