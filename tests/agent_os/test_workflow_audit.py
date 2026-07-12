"""Tests for workflow audit wizard (prompt 256)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from keprix.agent_os.audit_store import AuditStore, AuditTask
from keprix.agent_os.cli_commands import _dispatch_audit
from keprix.agent_os.session_scan import scan_sessions
from keprix.agent_os.workflow_audit_service import WorkflowAuditService
from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user


@pytest.fixture
def audit_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / ".keprix"
    root.mkdir()
    monkeypatch.setenv("KEPRIX_HOME", str(root))
    monkeypatch.setenv("KEPRIX_AGENT_OS_ENABLED", "1")
    return root


def test_manual_audit_complete_and_export(audit_env: Path) -> None:
    service = WorkflowAuditService()
    user = {"id": "user-1"}
    audit = service.start("manual", user)
    service.update_manual_tasks(
        audit.audit_id,
        [
            {
                "domain": "content",
                "description": "Write daily brief from calendar and tasks",
                "frequency": "daily",
                "desired_output": "One-page brief",
                "propose_skill": True,
                "propose_automation": True,
            }
        ],
    )
    completed = service.complete(audit.audit_id)
    assert completed.status == "completed"
    assert completed.proposed_skills
    assert completed.proposed_automations
    exported = service.export_to_proposals(audit.audit_id)
    assert exported == 1
    queue = json.loads((audit_env / "agent-os" / "skill-proposals-pending.json").read_text(encoding="utf-8"))
    assert queue[0]["source"] == "audit"
    assert queue[0]["origin"] == "workflow_audit"
    assert "description" in queue[0]
    assert "evidence_sessions" in queue[0]


def test_audit_store_roundtrip(audit_env: Path) -> None:
    store = AuditStore()
    audit = store.create("interview", user_id="u1")
    audit.tasks = [AuditTask(id="t1", domain="ops", description="Triage inbox")]
    store.save(audit)
    loaded = store.load(audit.audit_id)
    assert loaded is not None
    assert loaded.tasks[0].description == "Triage inbox"
    listed = store.list_audits(user_id="u1")
    assert len(listed) == 1


def test_session_scan_reads_workspace_sessions(audit_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sessions = [{"id": "s1"}, {"id": "s2"}, {"id": "s3"}]

    def list_sessions(user, limit, offset):
        assert user["id"] == "user-1"
        assert limit == 10
        assert offset == 0
        return sessions

    def get_session(user, session_id):
        return {
            "messages": [
                {"role": "user", "content": "Draft weekly client update from CRM notes"},
                {"role": "assistant", "tool_calls": [{"name": "search_docs"}]},
            ]
        }

    monkeypatch.setattr("keprix.agent_os.session_scan.workspace_repo.list_sessions", list_sessions)
    monkeypatch.setattr("keprix.agent_os.session_scan.workspace_repo.get_session", get_session)

    tasks, session_ids = scan_sessions({"id": "user-1"}, session_count=10)

    assert session_ids == ["s1", "s2", "s3"]
    assert tasks[0].description == "Draft weekly client update from CRM notes"
    assert tasks[0].frequency == "weekly"
    assert tasks[0].tools_hint == ["search_docs"]


@pytest.mark.asyncio
async def test_interview_mode_captures_tasks_on_done(audit_env: Path) -> None:
    service = WorkflowAuditService()
    audit = service.start("interview", {"id": "user-1"})

    audit, _reply, done = await service.continue_interview(
        audit.audit_id,
        "Every Monday I prepare a partner pipeline summary from inbox and CRM notes.",
    )
    assert done is False

    audit, _reply, done = await service.continue_interview(audit.audit_id, "done")
    assert done is True
    assert audit.tasks
    assert "partner pipeline summary" in audit.tasks[0].description


def test_api_routes_auth_and_export(audit_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "user-1", "role": "user"}
    client = TestClient(app)

    created = client.post("/api/agent-os/audit/start", json={"mode": "manual"})
    assert created.status_code == 200
    audit_id = created.json()["audit"]["audit_id"]

    updated = client.put(
        f"/api/agent-os/audit/{audit_id}/tasks",
        json={"tasks": [{"domain": "ops", "description": "Review support queue every morning", "propose_skill": True}]},
    )
    assert updated.status_code == 200

    listed = client.get("/api/agent-os/audits")
    assert listed.status_code == 200
    assert listed.json()["audits"][0]["audit_id"] == audit_id

    completed = client.post(f"/api/agent-os/audit/{audit_id}/complete")
    assert completed.status_code == 200
    exported = client.post(f"/api/agent-os/audit/{audit_id}/export-to-proposals")
    assert exported.json() == {"exported": 1}


def test_api_requires_auth_when_enabled(audit_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    client = TestClient(create_app())
    response = client.post("/api/agent-os/audit/start", json={"mode": "manual"}, headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401


def test_agent_os_feature_flag_blocks_routes(audit_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_AGENT_OS_ENABLED", "0")
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "user-1", "role": "user"}
    client = TestClient(app)
    response = client.post("/api/agent-os/audit/start", json={"mode": "manual"})
    assert response.status_code == 403


def test_cli_accepts_session_scan_alias(audit_env: Path, capsys: pytest.CaptureFixture[str]) -> None:
    import argparse

    args = argparse.Namespace(audit_command="start", mode="session-scan", sessions=5)
    assert _dispatch_audit(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "session_scan"
