"""Prompt 265 Agent OS onboarding event hook tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from keprix.agent_os.onboarding_events import record_onboarding_event
from keprix.agent_os.onboarding_progress import OnboardingProgressStore
from keprix.agent_os.workflow_audit_service import WorkflowAuditService
from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user


def test_events_complete_only_mapped_steps(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))

    record_onboarding_event("u1", "audit.completed")
    progress = OnboardingProgressStore().load("u1")

    assert progress.steps["l1_audit"] is True
    assert progress.steps["l2_connect_one"] is False
    assert progress.steps["l2_four_cs_audit"] is False
    assert progress.completed_at is None


def test_unknown_event_creates_no_false_completion(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))

    record_onboarding_event("u1", "connections.domain_live")
    progress = OnboardingProgressStore().load("u1")

    assert progress.steps["l2_connect_one"] is True
    assert progress.steps["l2_four_cs_audit"] is False
    assert progress.steps["l4_kit"] is False


def test_audit_complete_route_records_onboarding_event(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / ".keprix"
    root.mkdir()
    monkeypatch.setenv("KEPRIX_HOME", str(root))
    monkeypatch.setenv("KEPRIX_AGENT_OS_ENABLED", "1")

    service = WorkflowAuditService()
    audit = service.start("manual", {"id": "user-1"})
    service.update_manual_tasks(
        audit.audit_id,
        [{"domain": "ops", "description": "Review support queue", "propose_skill": True}],
    )

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "user-1", "role": "user"}
    client = TestClient(app)

    completed = client.post(f"/api/agent-os/audit/{audit.audit_id}/complete")
    assert completed.status_code == 200

    progress = client.get("/api/agent-os/onboarding")
    assert progress.status_code == 200
    payload = progress.json()
    assert payload["steps"]["l1_audit"] is True
    assert payload["steps"]["l2_connect_one"] is False
