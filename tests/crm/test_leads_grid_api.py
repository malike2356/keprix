"""Spreadsheet CRM leads grid APIs (Prompt 623)."""

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


def _seed_leads(client: TestClient, n: int = 5, workspace_id: str = "ws1") -> list[dict]:
    leads = []
    for i in range(n):
        res = client.post(
            "/api/crm/leads",
            json={
                "name": f"Contact {i}",
                "company_name": f"Co {i}",
                "email": f"c{i}@example.com",
                "source": "csv" if i % 2 == 0 else "manual",
                "priority": "high" if i == 0 else "medium",
                "stage": "discovered",
                "tags": ["alpha"] if i < 2 else [],
            },
            params={"workspace_id": workspace_id},
        )
        assert res.status_code == 201, res.text
        leads.append(res.json()["lead"])
    return leads


def test_keyset_pagination_and_filters(client: TestClient) -> None:
    _seed_leads(client, 8)
    first = client.get(
        "/api/crm/leads",
        params={"workspace_id": "ws1", "limit": 3, "sort": "updated_at", "order": "desc"},
    )
    assert first.status_code == 200
    body = first.json()
    assert len(body["items"]) == 3
    assert body["total"] == 8
    assert body["next_cursor"]
    assert body["count"] == 8

    second = client.get(
        "/api/crm/leads",
        params={
            "workspace_id": "ws1",
            "limit": 3,
            "cursor": body["next_cursor"],
            "sort": "updated_at",
            "order": "desc",
        },
    )
    assert second.status_code == 200
    ids1 = {r["id"] for r in body["items"]}
    ids2 = {r["id"] for r in second.json()["items"]}
    assert ids1.isdisjoint(ids2)

    filtered = client.get(
        "/api/crm/leads",
        params={"workspace_id": "ws1", "source": "csv", "priority": "high"},
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] >= 1
    assert all(r["source"] == "csv" for r in filtered.json()["items"])


def test_bulk_patch_soft_wall_for_paying_stage(client: TestClient) -> None:
    leads = _seed_leads(client, 2)
    ids = [leads[0]["id"], leads[1]["id"]]
    blocked = client.post(
        "/api/crm/leads/bulk-patch",
        json={"ids": ids, "patch": {"stage": "customer", "pipeline_stage": "customer"}},
        params={"workspace_id": "ws1"},
    )
    assert blocked.status_code == 200
    payload = blocked.json()
    assert payload.get("blocked") is True
    assert payload.get("error_code") == "soft_wall_required"
    assert payload.get("approval", {}).get("id")
    assert payload["updated"] == []

    approval_id = payload["approval"]["id"]
    approved = client.post(
        f"/api/crm/approvals/{approval_id}/approve",
        params={"workspace_id": "ws1"},
    )
    assert approved.status_code == 200

    applied = client.post(
        "/api/crm/leads/bulk-patch",
        json={
            "ids": ids,
            "patch": {"stage": "customer", "pipeline_stage": "customer"},
            "approval_id": approval_id,
        },
        params={"workspace_id": "ws1"},
    )
    assert applied.status_code == 200
    assert len(applied.json()["updated"]) == 2
    assert all(r["stage"] == "customer" for r in applied.json()["updated"])


def test_provenance_and_export_and_ingest_preview(client: TestClient, tmp_path: Path) -> None:
    from keprix.crm.ingestion.service import IngestOptions, ingest_row_array
    from keprix.crm.store import get_crm_store

    store = get_crm_store()
    ingest_row_array(
        "ws1",
        [
            {
                "Company": "Acme",
                "Email": "ada@acme.example",
                "Contact Name": "Ada",
                "Niche": "Dental",
            }
        ],
        store=store,
        options=IngestOptions(source_name="test", actor_id="t"),
    )
    leads = client.get("/api/crm/leads", params={"workspace_id": "ws1", "q": "acme"}).json()["items"]
    assert leads
    lead_id = leads[0]["id"]

    prov = client.get(f"/api/crm/leads/{lead_id}/provenance", params={"workspace_id": "ws1"})
    assert prov.status_code == 200
    assert prov.json()["count"] >= 0

    acts = client.get(f"/api/crm/leads/{lead_id}/activities", params={"workspace_id": "ws1"})
    assert acts.status_code == 200

    export = client.post(
        "/api/crm/leads/export-workbook",
        json={"ids": [lead_id], "format": "csv"},
        params={"workspace_id": "ws1"},
    )
    assert export.status_code == 200
    assert "text/csv" in export.headers.get("content-type", "")
    assert b"Company" in export.content or b"Acme" in export.content

    preview = client.post(
        "/api/crm/leads/ingest-preview",
        json={
            "rows": [
                {"Company": "Beta", "Email": "b@beta.example", "Contact Name": "Bee"},
            ]
        },
        params={"workspace_id": "ws1"},
    )
    assert preview.status_code == 200
    assert "header_map" in preview.json()
    assert preview.json()["row_count"] == 1


def test_saved_views_isolation(client: TestClient) -> None:
    created = client.post(
        "/api/crm/views",
        json={
            "name": "Mine",
            "visibility": "private",
            "config": {"filters": {"stage": "discovered"}, "density": "compact"},
        },
        params={"workspace_id": "ws_a"},
    )
    assert created.status_code == 201
    view_id = created.json()["view"]["id"]

    listed_a = client.get("/api/crm/views", params={"workspace_id": "ws_a"})
    assert listed_a.status_code == 200
    assert any(v["id"] == view_id for v in listed_a.json()["items"])

    listed_b = client.get("/api/crm/views", params={"workspace_id": "ws_b"})
    assert listed_b.status_code == 200
    assert all(v["id"] != view_id for v in listed_b.json()["items"])

    other = FastAPI()
    other.include_router(crm_router)

    async def other_user():
        return {"id": "other-user", "username": "other-user", "role": "admin"}

    from keprix.auth import dependencies as deps

    other.dependency_overrides[deps.get_current_user] = other_user
    other_client = TestClient(other)

    denied = other_client.patch(
        f"/api/crm/views/{view_id}",
        json={"name": "Hijacked"},
        params={"workspace_id": "ws_a"},
    )
    assert denied.status_code == 403


def test_bulk_archive_sets_archived_at(client: TestClient) -> None:
    leads = _seed_leads(client, 1)
    lead_id = leads[0]["id"]
    res = client.post(
        "/api/crm/leads/bulk-archive",
        json={"ids": [lead_id]},
        params={"workspace_id": "ws1"},
    )
    assert res.status_code == 200
    updated = res.json()["updated"]
    assert len(updated) == 1
    assert updated[0].get("archived_at")

    listed = client.get("/api/crm/leads", params={"workspace_id": "ws1"})
    assert all(r["id"] != lead_id for r in listed.json()["items"])
