"""Prompt 265 Agent OS onboarding progress tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from keprix.agent_os.onboarding_progress import OnboardingProgressStore
from keprix.agent_os.onboarding_steps import all_step_ids
from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user


def test_new_user_starts_with_pending_steps_and_visible_banner(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    progress = OnboardingProgressStore().load("u1")

    payload = progress.to_dict()
    assert payload["total_count"] == len(all_step_ids())
    assert payload["pending_count"] == len(all_step_ids())
    assert payload["banner_visible"] is True
    assert payload["onboarding_completed"] is False


def test_manual_completion_sets_completed_at_and_hides_banner(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    store = OnboardingProgressStore()

    for step_id in all_step_ids():
        progress = store.complete_step("u1", step_id)

    payload = progress.to_dict()
    assert payload["completed_at"]
    assert payload["onboarding_completed"] is True
    assert payload["banner_visible"] is False


def test_onboarding_routes_complete_dismiss_and_reset(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.setenv("KEPRIX_AGENT_OS_ENABLED", "1")
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    initial = client.get("/api/agent-os/onboarding")
    assert initial.status_code == 200
    assert initial.json()["steps"]["l1_audit"] is False

    completed = client.post("/api/agent-os/onboarding/complete-step", json={"step_id": "l1_audit"})
    assert completed.status_code == 200
    assert completed.json()["steps"]["l1_audit"] is True
    assert completed.json()["steps"]["l2_connect_one"] is False

    dismissed = client.post("/api/agent-os/onboarding/dismiss", json={"dismissed": True})
    assert dismissed.status_code == 200
    assert dismissed.json()["banner_visible"] is False

    reset = client.post("/api/agent-os/onboarding/reset", json={})
    assert reset.status_code == 200
    assert reset.json()["steps"]["l1_audit"] is False
    assert reset.json()["banner_visible"] is True
