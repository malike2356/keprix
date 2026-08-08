"""CRM HTTP API + Soft Wall gate tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.crm.routes import router as crm_router
from keprix.crm.store import reset_crm_store_for_tests
from keprix.outreach.ops import OutreachOpsStore
from keprix.outreach.store import reset_outreach_store_for_tests


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    reset_crm_store_for_tests(tmp_path / "crm.sqlite")
    reset_outreach_store_for_tests(tmp_path / "outreach.sqlite")
    import keprix.outreach.ops as ops_mod

    ops_mod._ops = OutreachOpsStore(path=tmp_path / "outreach.sqlite")

    app = FastAPI()
    app.include_router(crm_router)

    async def fake_user():
        return {"id": "api-user", "username": "api-user", "role": "admin"}

    from keprix.auth import dependencies as deps

    app.dependency_overrides[deps.get_current_user] = fake_user
    return TestClient(app)


def test_lead_list_create_membership_and_soft_wall_enroll(client: TestClient) -> None:
    created = client.post(
        "/api/crm/leads",
        json={"name": "Acme lead", "email": "lead@acme.example", "source": "csv"},
        params={"workspace_id": "ws1"},
    )
    assert created.status_code == 201, created.text
    lead = created.json()["lead"]
    assert lead["emails"][0]["address"] == "lead@acme.example"

    listed = client.get("/api/crm/leads", params={"workspace_id": "ws1", "q": "acme"})
    assert listed.status_code == 200
    assert listed.json()["count"] >= 1

    lst = client.post(
        "/api/crm/lists",
        json={"name": "Batch A"},
        params={"workspace_id": "ws1"},
    )
    assert lst.status_code == 201
    list_id = lst.json()["list"]["id"]

    member = client.post(
        f"/api/crm/lists/{list_id}/members",
        json={"member_type": "lead", "member_id": lead["id"]},
        params={"workspace_id": "ws1"},
    )
    assert member.status_code == 201

    blocked = client.post(
        f"/api/crm/lists/{list_id}/approve-enroll",
        json={"sequence_id": "seq1"},
        params={"workspace_id": "ws1"},
    )
    assert blocked.status_code == 200
    payload = blocked.json()
    assert payload["blocked"] is True
    assert payload["error_code"] == "soft_wall_required"
    assert payload["approval"]["id"]
    assert payload["approval"]["deep_link"].startswith("/crm")

    approval_id = payload["approval"]["id"]
    approved = client.post(
        f"/api/crm/approvals/{approval_id}/approve",
        params={"workspace_id": "ws1"},
    )
    assert approved.status_code == 200

    allowed = client.post(
        f"/api/crm/lists/{list_id}/approve-enroll",
        json={"sequence_id": "seq1", "approval_id": approval_id},
        params={"workspace_id": "ws1"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["blocked"] is False
    assert allowed.json()["enroll_ready"] is True


def test_operator_endpoints_exist(client: TestClient) -> None:
    for path in (
        "/api/crm/jobs",
        "/api/crm/outbox",
        "/api/crm/merges",
        "/api/crm/contactability",
        "/api/crm/deliverability",
        "/api/crm/kill-switches",
        "/api/crm/suppressions",
        "/api/crm/enrichments",
    ):
        res = client.get(path, params={"workspace_id": "ws1"})
        assert res.status_code == 200, path


def test_auth_required_when_enabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    reset_crm_store_for_tests(tmp_path / "crm.sqlite")
    app = FastAPI()
    app.include_router(crm_router)
    monkeypatch.setenv("KEPRIX_AUTH_ENABLED", "1")

    # Clear guest/dev bypasses if present by forcing auth_enabled True and no overrides.
    from keprix.auth import config as auth_config

    monkeypatch.setattr(auth_config, "auth_enabled", lambda: True)

    client = TestClient(app)
    res = client.get("/api/crm/leads", params={"workspace_id": "ws1"})
    assert res.status_code in (401, 403)


def test_cross_workspace_isolation_via_api(client: TestClient) -> None:
    created = client.post(
        "/api/crm/leads",
        json={"name": "Secret", "email": "secret@example.com"},
        params={"workspace_id": "ws_a"},
    )
    lead_id = created.json()["lead"]["id"]
    missing = client.get(f"/api/crm/leads/{lead_id}", params={"workspace_id": "ws_b"})
    assert missing.status_code == 404
