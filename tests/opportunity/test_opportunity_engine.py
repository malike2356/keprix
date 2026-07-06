"""Opportunity Engine tests."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.opportunity.approvals import check_action_allowed, is_risky_action, request_approval
from keprix.opportunity.models import ARTIFACT_FILENAMES, PHASE_ORDER, OpportunityRequest
from keprix.opportunity.orchestrator import run_opportunity_phase, run_opportunity_pipeline
from keprix.opportunity.registry import reset_opportunity_registry
from keprix.opportunity.safety import SafetyViolation, check_no_login_scraping
from keprix.opportunity.workspace import (
    create_opportunity_workspace,
    opportunities_root,
    read_artifact,
    read_opportunity_json,
)
from keprix.security.rate_limiter import reset_rate_limits
from keprix.security.validation import ValidationError


@pytest.fixture
def opp_env(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(data_dir))
    reset_rate_limits()
    reset_opportunity_registry(base_dir=data_dir / "workspace" / "opportunities")
    return {"data_dir": data_dir, "root": data_dir / "workspace" / "opportunities"}


@pytest.fixture
def opp_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    reset_rate_limits()
    reset_opportunity_registry(base_dir=tmp_path / "workspace" / "opportunities")

    auth = AuthManager(str(tmp_path / "auth.json"))
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)

    client = TestClient(create_app())
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    token = login.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_create_workspace_artifacts(opp_env):
    request = OpportunityRequest(
        title="AI Compliance SaaS",
        niche="regtech",
        goal="Validate demand for SMB compliance automation",
        source="test",
    )
    workspace = create_opportunity_workspace(request)
    opp_dir = opportunities_root() / workspace.opportunity_id
    assert opp_dir.is_dir()
    for filename in ARTIFACT_FILENAMES:
        assert (opp_dir / filename).exists()


def test_safe_path_rejects_traversal(opp_env):
    request = OpportunityRequest(title="Safe Test", source="test")
    workspace = create_opportunity_workspace(request)
    with pytest.raises(ValidationError):
        read_artifact(workspace.opportunity_id, "../secrets.txt")
    with pytest.raises(ValidationError):
        read_artifact(workspace.opportunity_id, "../../etc/passwd")


@pytest.mark.asyncio
async def test_phase_order_and_artifacts(opp_env):
    request = OpportunityRequest(title="Phase Order Test", niche="fintech", source="test")
    workspace = create_opportunity_workspace(request)
    opp_id = workspace.opportunity_id

    await run_opportunity_phase(opp_id, "market_demand")
    content = read_artifact(opp_id, "01-market-demand.md")
    assert "Market Demand" in content

    meta = read_opportunity_json(opp_id)
    assert "market_demand" in meta["completed_phases"]

    for phase in PHASE_ORDER:
        await run_opportunity_phase(opp_id, phase)

    meta = read_opportunity_json(opp_id)
    assert meta["completed_phases"] == list(PHASE_ORDER)
    assert read_artifact(opp_id, "05-offer-doc.md")
    assert read_artifact(opp_id, "11-launch-plan.md")


@pytest.mark.asyncio
async def test_pipeline_runs_all_phases(opp_env):
    request = OpportunityRequest(title="Pipeline Test", niche="healthtech", source="test")
    workspace = create_opportunity_workspace(request)
    result = await run_opportunity_pipeline(workspace.opportunity_id)
    assert len(result["phases"]) == len(PHASE_ORDER)


def test_approval_gates_block_risky_actions(opp_env):
    request = OpportunityRequest(title="Approval Test", workspace_id="default", source="test")
    workspace = create_opportunity_workspace(request)
    assert is_risky_action("create_ad")
    allowed, reason = check_action_allowed(opportunity_id=workspace.opportunity_id, action="create_ad")
    assert allowed is False
    assert reason

    approval = request_approval(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        action="create_ad",
        requested_by="test",
    )
    assert approval.status == "pending"
    meta = read_opportunity_json(workspace.opportunity_id)
    assert meta["status"] == "approval_required"


def test_citations_added_during_research_phase(opp_env):
    request = OpportunityRequest(title="Citation Test", niche="edtech", source="test")
    workspace = create_opportunity_workspace(request)
    asyncio.run(run_opportunity_phase(workspace.opportunity_id, "market_demand"))
    meta = read_opportunity_json(workspace.opportunity_id)
    assert len(meta.get("citations", [])) >= 1


def test_safety_blocks_login_scraping():
    with pytest.raises(SafetyViolation):
        check_no_login_scraping("https://example.com/login")


def test_api_create_and_list(opp_client):
    created = opp_client.post(
        "/api/opportunities",
        json={"title": "API Opportunity", "niche": "proptech", "goal": "Launch validation"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["opportunity_id"].startswith("opp-")

    listed = opp_client.get("/api/opportunities")
    assert listed.status_code == 200
    ids = [row["opportunity_id"] for row in listed.json()["opportunities"]]
    assert body["opportunity_id"] in ids


def test_api_get_artifact(opp_client):
    created = opp_client.post("/api/opportunities", json={"title": "Artifact API Test"})
    opp_id = created.json()["opportunity_id"]
    response = opp_client.get(f"/api/opportunities/{opp_id}/artifacts/01-market-demand.md")
    assert response.status_code == 200
    assert "content" in response.json()


def test_api_requires_auth(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    reset_rate_limits()
    reset_opportunity_registry(base_dir=tmp_path / "workspace" / "opportunities")

    auth = AuthManager(str(tmp_path / "auth.json"))
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)

    client = TestClient(create_app())
    response = client.get("/api/opportunities")
    assert response.status_code in {401, 403}
