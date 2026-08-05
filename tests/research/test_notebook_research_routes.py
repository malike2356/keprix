"""Prompt 268 notebook research route tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user


def test_notebook_research_routes_persist_list_and_export(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.delenv("NOTEBOOKLM_BRIDGE_CMD", raising=False)
    monkeypatch.delenv("NOTEBOOKLM_MCP_URL", raising=False)
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    config = client.get("/api/research/notebook/config")
    assert config.status_code == 200
    assert config.json()["external_enabled"] is False

    created = client.post(
        "/api/research/notebook",
        json={
            "query": "What changed?",
            "depth": "notebook",
            "sources": [
                {"kind": "text", "title": "One", "ref": "Alpha changed after source one."},
                {"kind": "text", "title": "Two", "ref": "Beta changed after source two."},
            ],
        },
    )
    assert created.status_code == 200
    job = created.json()["job"]
    assert job["status"] == "complete"
    assert "[S1]" in job["report_md"]

    listed = client.get("/api/research/notebook")
    assert listed.status_code == 200
    assert listed.json()["jobs"][0]["job_id"] == job["job_id"]

    detail = client.get(f"/api/research/notebook/{job['job_id']}")
    assert detail.status_code == 200
    assert detail.json()["job"]["citations"]

    export = client.post(f"/api/research/notebook/{job['job_id']}/export", json={})
    assert export.status_code == 200
    export_path = Path(export.json()["path"])
    assert export_path.is_file()
    assert "Notebook Research Report" in export_path.read_text(encoding="utf-8")


def test_notebook_external_depth_falls_back_when_unconfigured(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.delenv("NOTEBOOKLM_BRIDGE_CMD", raising=False)
    monkeypatch.delenv("NOTEBOOKLM_MCP_URL", raising=False)
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    response = client.post(
        "/api/research/notebook",
        json={
            "query": "Fallback?",
            "depth": "notebook-external",
            "sources": [
                {"kind": "text", "title": "One", "ref": "Alpha fallback source."},
                {"kind": "text", "title": "Two", "ref": "Beta fallback source."},
            ],
        },
    )

    assert response.status_code == 200
    assert "fallback" in response.json()["job"]["error"].lower()
