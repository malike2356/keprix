"""Prompt 275 level-up API route tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user


def test_level_up_routes_generate_complete_and_reaudit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    audit = client.post("/api/agent-os/maturity/run", json={"workspace_id": "demo", "workspace_path": str(workspace)}).json()["audit"]
    generated = client.post("/api/agent-os/level-up/generate", json={"audit_id": audit["audit_id"], "workspace_path": str(workspace)})
    assert generated.status_code == 200
    plan = generated.json()["plan"]
    assert len(plan["actions"]) >= 3

    completed = client.post(f"/api/agent-os/level-up/{plan['plan_id']}/actions/{plan['actions'][0]['id']}/complete")
    assert completed.status_code == 200
    assert completed.json()["plan"]["actions"][0]["completed"] is True

    stubs = client.post(f"/api/agent-os/level-up/{plan['plan_id']}/apply-safe-stubs")
    assert stubs.status_code == 200

    re_audit = client.post(f"/api/agent-os/level-up/{plan['plan_id']}/re-audit")
    assert re_audit.status_code == 200
    assert re_audit.json()["audit"]["total_score"] >= audit["total_score"]
