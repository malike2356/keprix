from __future__ import annotations

import json
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
    store = reset_crm_store_for_tests(tmp_path / "crm.sqlite")
    reset_outreach_store_for_tests(tmp_path / "outreach.sqlite")
    import keprix.outreach.ops as ops_mod

    ops_mod._ops = OutreachOpsStore(path=tmp_path / "outreach.sqlite")
    app = FastAPI()
    app.include_router(crm_router)

    async def fake_user() -> dict[str, str]:
        return {"id": "api-user", "username": "api-user", "role": "admin"}

    from keprix.auth import dependencies as deps

    app.dependency_overrides[deps.get_current_user] = fake_user
    monkeypatch.setattr(
        "keprix.crm.routes.score_website",
        lambda _url: {"score": 8, "weakness": "none detected", "checks": []},
    )
    monkeypatch.setattr(
        "keprix.crm.routes.check_rank",
        lambda _domain, _keyword: {"ranks_top3": True, "position": 2},
    )
    store.create_lead(
        "ws1",
        name="Scored lead",
        company_name="Acme",
        website="https://acme.example",
        custom_fields={"website_score": 4},
    )
    store.create_lead("ws1", name="No website")
    return TestClient(app)


def test_single_score_persists_and_preserves_human_score(client: TestClient) -> None:
    leads = client.get("/api/crm/leads", params={"workspace_id": "ws1"}).json()["items"]
    scored = next(row for row in leads if row["name"] == "Scored lead")
    response = client.post(
        "/api/crm/website-score",
        params={"workspace_id": "ws1"},
        json={"lead_id": scored["id"], "keyword": "acme"},
    )
    assert response.status_code == 200, response.text
    reread = client.get(f"/api/crm/leads/{scored['id']}", params={"workspace_id": "ws1"}).json()["lead"]
    assert reread["custom_fields"] == {
        "website_score": 4,
        "weakness": "none detected",
        "ranks_top3": True,
    }
    assert reread["website_score"] == "8"
    assert reread["ranks_top3"] == "1"


def test_batch_skips_missing_website(client: TestClient) -> None:
    leads = client.get("/api/crm/leads", params={"workspace_id": "ws1"}).json()["items"]
    response = client.post(
        "/api/crm/website-score/batch",
        params={"workspace_id": "ws1"},
        json={"lead_ids": [row["id"] for row in leads]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["count"] == 2
    assert any(item.get("skipped") and item["reason"] == "website_missing" for item in body["items"])


def test_tool_persists_score(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store = reset_crm_store_for_tests(tmp_path / "tool-crm.sqlite")
    lead = store.create_lead("ws-tool", name="Tool lead", website="https://tool.example")
    monkeypatch.setattr("keprix.tools.crm_tools.score_website", lambda _url: {"score": 7, "weakness": "no contact", "checks": []})
    from keprix.tools.crm_tools import _crm_lead_score_website

    result = json.loads(_crm_lead_score_website({"workspace_id": "ws-tool", "lead_id": lead["id"]}))
    assert result["lead"]["custom_fields"]["website_score"] == 7
    assert store.get_lead("ws-tool", lead["id"])["custom_fields"]["weakness"] == "no contact"
