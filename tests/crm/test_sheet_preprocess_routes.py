"""Sheet preprocess HTTP API: upload -> propose -> Soft Wall apply / reject."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.crm.store import get_crm_store, reset_crm_store_for_tests
from keprix.outreach.ops import OutreachOpsStore
from keprix.outreach.store import reset_outreach_store_for_tests
from keprix.sheet_preprocess.routes import router as sheets_router


FIXTURES = Path(__file__).resolve().parents[1] / "sheet_preprocess" / "fixtures"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    reset_crm_store_for_tests(tmp_path / "crm.sqlite")
    reset_outreach_store_for_tests(tmp_path / "outreach.sqlite")
    import keprix.outreach.ops as ops_mod

    ops_mod._ops = OutreachOpsStore(path=tmp_path / "outreach.sqlite")
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "1")
    monkeypatch.setenv("KEPRIX_SHEET_PREPROCESS_DIR", str(tmp_path / "sheets"))
    monkeypatch.setenv("KEPRIX_SHEET_EMAIL_INGEST", "0")

    app = FastAPI()
    app.include_router(sheets_router)

    # Approvals live on CRM router.
    from keprix.crm.routes import router as crm_router

    app.include_router(crm_router)

    async def fake_user():
        return {"id": "api-user", "username": "api-user", "role": "admin"}

    from keprix.auth import dependencies as deps

    app.dependency_overrides[deps.get_current_user] = fake_user
    return TestClient(app)


def _upload_leads(client: TestClient, workspace_id: str = "ws1") -> str:
    path = FIXTURES / "leads.csv"
    res = client.post(
        "/api/crm/sheets/upload",
        params={"workspace_id": workspace_id},
        files={"file": ("leads.csv", path.read_bytes(), "text/csv")},
    )
    assert res.status_code == 201, res.text
    return res.json()["upload"]["upload_id"]


def test_happy_path_upload_propose_soft_wall_apply_creates_leads(client: TestClient) -> None:
    upload_id = _upload_leads(client)
    proposed = client.post(
        "/api/crm/sheets/propose",
        params={"workspace_id": "ws1"},
        json={
            "upload_id": upload_id,
            "build_crm_plan": True,
            "domain_pack": "generic",
        },
    )
    assert proposed.status_code == 201, proposed.text
    job = proposed.json()["enrichment_job"]
    job_id = job["id"]
    assert job["status"] in {"proposed", "partial"}
    assert job["metrics"]["blank_cells"] >= 1
    assert job["deep_link"] == f"/crm/enrich?job={job_id}"

    store = get_crm_store()
    before = len(store.list_leads("ws1"))

    blocked = client.post(
        f"/api/crm/sheets/{job_id}/apply",
        params={"workspace_id": "ws1"},
        json={"upsert_crm": True},
    )
    assert blocked.status_code == 200, blocked.text
    payload = blocked.json()
    assert payload["blocked"] is True
    assert payload["error_code"] == "soft_wall_required"
    assert payload["approval"]["id"]
    assert "/crm/enrich?job=" in (payload["approval"].get("object_deep_link") or payload["approval"].get("deep_link") or "")

    # Store unchanged while blocked.
    assert len(store.list_leads("ws1")) == before
    mid = store.get_enrichment_job("ws1", job_id)
    assert mid and mid["status"] in {"proposed", "partial"}

    approval_id = payload["approval"]["id"]
    approved = client.post(
        f"/api/crm/approvals/{approval_id}/approve",
        params={"workspace_id": "ws1"},
    )
    assert approved.status_code == 200, approved.text

    applied = client.post(
        f"/api/crm/sheets/{job_id}/apply",
        params={"workspace_id": "ws1"},
        json={"approval_id": approval_id, "upsert_crm": True},
    )
    assert applied.status_code == 200, applied.text
    body = applied.json()
    assert body["blocked"] is False
    assert body["enrichment_job"]["status"] == "applied"
    assert body.get("leads_deep_link") == "/crm/leads"
    assert len(store.list_leads("ws1")) > before
    assert body.get("list_id")
    assert body.get("list_deep_link", "").startswith("/crm/lists/")

    download = client.get(
        f"/api/crm/sheets/{job_id}/download",
        params={"workspace_id": "ws1", "format": "csv"},
    )
    assert download.status_code == 200
    assert "Acme" in download.text or "company" in download.text.lower()


def test_reject_leaves_store_unchanged(client: TestClient) -> None:
    upload_id = _upload_leads(client, workspace_id="ws_reject")
    proposed = client.post(
        "/api/crm/sheets/propose",
        params={"workspace_id": "ws_reject"},
        json={"upload_id": upload_id, "build_crm_plan": True},
    )
    job_id = proposed.json()["enrichment_job"]["id"]
    store = get_crm_store()
    before_leads = len(store.list_leads("ws_reject"))
    before_job = store.get_enrichment_job("ws_reject", job_id)

    blocked = client.post(
        f"/api/crm/sheets/{job_id}/apply",
        params={"workspace_id": "ws_reject"},
        json={"upsert_crm": True},
    )
    approval_id = blocked.json()["approval"]["id"]

    rejected = client.post(
        f"/api/crm/approvals/{approval_id}/reject",
        params={"workspace_id": "ws_reject"},
    )
    assert rejected.status_code == 200, rejected.text

    # Attempt apply with rejected approval must not mutate.
    again = client.post(
        f"/api/crm/sheets/{job_id}/apply",
        params={"workspace_id": "ws_reject"},
        json={"approval_id": approval_id, "upsert_crm": True},
    )
    assert again.status_code == 200
    assert again.json().get("blocked") is True

    after_job = store.get_enrichment_job("ws_reject", job_id)
    assert after_job["status"] == before_job["status"]
    assert after_job.get("output_path") in (None, "", before_job.get("output_path"))
    assert len(store.list_leads("ws_reject")) == before_leads


def test_email_ingest_disabled_by_default(client: TestClient) -> None:
    res = client.get("/api/crm/sheets/email-ingest/status")
    assert res.status_code == 200
    assert res.json()["enabled"] is False
    assert res.json()["default"] == "0"

    from keprix.sheet_preprocess.email_ingest import poll_once

    polled = poll_once(workspace_id="ws1")
    assert polled["skipped"] is True
    assert polled["reason"] == "email_ingest_disabled"


def test_cross_workspace_job_hidden(client: TestClient) -> None:
    upload_id = _upload_leads(client, workspace_id="ws_a")
    proposed = client.post(
        "/api/crm/sheets/propose",
        params={"workspace_id": "ws_a"},
        json={"upload_id": upload_id},
    )
    job_id = proposed.json()["enrichment_job"]["id"]
    missing = client.get(f"/api/crm/sheets/{job_id}", params={"workspace_id": "ws_b"})
    assert missing.status_code == 404


def test_agent_tools_registered_and_deep_link(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    reset_crm_store_for_tests(tmp_path / "crm.sqlite")
    reset_outreach_store_for_tests(tmp_path / "outreach.sqlite")
    import keprix.outreach.ops as ops_mod

    ops_mod._ops = OutreachOpsStore(path=tmp_path / "outreach.sqlite")
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "1")
    monkeypatch.setenv("KEPRIX_SHEET_PREPROCESS_DIR", str(tmp_path / "sheets"))

    import keprix.tools.sheet_preprocess_tools as tools
    from tools.registry import registry

    assert "sheet_preprocess_propose" in registry._tools
    assert "sheet_preprocess_apply" in registry._tools

    import json

    raw = tools.sheet_preprocess_propose(
        {
            "workspace_id": "ws_tools",
            "source_path": str(FIXTURES / "leads.csv"),
            "build_crm_plan": True,
        }
    )
    payload = json.loads(raw)
    assert payload["deep_link"].startswith("/crm/enrich?job=")
    job_id = payload["enrichment_job"]["id"]

    blocked = json.loads(
        tools.sheet_preprocess_apply({"workspace_id": "ws_tools", "job_id": job_id})
    )
    assert blocked["blocked"] is True
    assert blocked["deep_link"] == f"/crm/enrich?job={job_id}"


def test_applied_sheet_downloads_as_excel_or_csv(client: TestClient) -> None:
    upload_id = _upload_leads(client, workspace_id="ws_export")
    proposed = client.post(
        "/api/crm/sheets/propose",
        params={"workspace_id": "ws_export"},
        json={"upload_id": upload_id},
    )
    job_id = proposed.json()["enrichment_job"]["id"]
    applied = client.post(
        f"/api/crm/sheets/{job_id}/apply",
        params={"workspace_id": "ws_export"},
        json={"force": True, "upsert_crm": False},
    )
    assert applied.status_code == 200, applied.text

    excel = client.get(
        f"/api/crm/sheets/{job_id}/download",
        params={"workspace_id": "ws_export", "format": "xlsx"},
    )
    assert excel.status_code == 200
    assert excel.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert excel.content.startswith(b"PK")

    csv_export = client.get(
        f"/api/crm/sheets/{job_id}/download",
        params={"workspace_id": "ws_export", "format": "csv"},
    )
    assert csv_export.status_code == 200
    assert csv_export.headers["content-type"].startswith("text/csv")


def test_google_sheet_import_uses_canonical_upload(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "keprix.integrations.google_workspace.bridge.GoogleWorkspaceBridge.sheets_read",
        lambda _self, _spreadsheet_id, _range_name: {
            "values": [["company", "email"], ["Acme", "hello@acme.test"]]
        },
    )
    response = client.post(
        "/api/crm/sheets/import/google-sheet",
        params={"workspace_id": "ws_google"},
        json={"spreadsheet_id": "sheet-123", "title": "Lead tracker"},
    )
    assert response.status_code == 201, response.text
    upload = response.json()["upload"]
    assert upload["filename"] == "Lead tracker.csv"
    assert upload["source"]["kind"] == "google_sheet"
    assert Path(upload["path"]).read_text(encoding="utf-8").startswith("company,email")
    metadata = Path(upload["path"] + ".meta.json").read_text(encoding="utf-8")
    assert '"spreadsheet_id": "sheet-123"' in metadata


def test_applied_sheet_can_publish_to_google_sheet(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    upload_id = _upload_leads(client, workspace_id="ws_publish")
    proposed = client.post(
        "/api/crm/sheets/propose",
        params={"workspace_id": "ws_publish"},
        json={"upload_id": upload_id},
    )
    job_id = proposed.json()["enrichment_job"]["id"]
    applied = client.post(
        f"/api/crm/sheets/{job_id}/apply",
        params={"workspace_id": "ws_publish"},
        json={"force": True, "upsert_crm": False},
    )
    assert applied.status_code == 200, applied.text

    captured: dict = {}

    def fake_call(_self, tool: str, args: dict) -> dict:
        captured.update({"tool": tool, "args": args})
        return {
            "spreadsheet_id": "published-123",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/published-123",
        }

    monkeypatch.setattr("keprix.integrations.google_workspace.bridge.GoogleWorkspaceBridge.call", fake_call)
    response = client.post(
        f"/api/crm/sheets/{job_id}/publish/google-sheet",
        params={"workspace_id": "ws_publish"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["spreadsheet_id"] == "published-123"
    assert captured["tool"] == "gws_sheets_create"
    assert captured["args"]["values"][0]
