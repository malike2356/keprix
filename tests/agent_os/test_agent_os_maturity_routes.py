"""Prompt 274 maturity API route tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user


def test_agent_os_maturity_routes_run_get_list_export(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    workspace = tmp_path / "workspace"
    (workspace / "context").mkdir(parents=True)
    (workspace / "context" / "about-business.md").write_text("We sell systems. ICP founders.", encoding="utf-8")
    (workspace / "context" / "about-me.md").write_text("bottlenecks", encoding="utf-8")
    (workspace / "context" / "priorities.md").write_text("90 day priorities", encoding="utf-8")
    (workspace / "context" / "writing-samples.md").write_text("sample", encoding="utf-8")
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    run = client.post("/api/agent-os/maturity/run", json={"workspace_id": "demo", "workspace_path": str(workspace)})
    assert run.status_code == 200
    audit = run.json()["audit"]
    assert audit["total_score"] == sum(score["score"] for score in audit["scores"])

    detail = client.get(f"/api/agent-os/maturity/{audit['audit_id']}")
    assert detail.status_code == 200

    history = client.get("/api/agent-os/maturity")
    assert history.status_code == 200
    assert history.json()["audits"][0]["audit_id"] == audit["audit_id"]

    exported = client.post(f"/api/agent-os/maturity/{audit['audit_id']}/export-to-level-up")
    assert exported.status_code == 200
    assert exported.json()["schema"] == "keprix.level_up.input.v1"

    progress = client.get("/api/agent-os/onboarding")
    assert progress.json()["steps"]["l2_four_cs_audit"] is True
