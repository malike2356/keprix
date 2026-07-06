"""Workspace API acceptance tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.security.rate_limiter import reset_rate_limits
from keprix.workspace.draft_store import draft_store
from keprix.workspace.repository import WorkspaceRepository, workspace_repo


@pytest.fixture
def workspace_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_EMBEDDING_DETERMINISTIC", "true")
    monkeypatch.setenv("KEPRIX_CALDAV_DETERMINISTIC", "true")
    reset_rate_limits()

    auth = AuthManager(str(tmp_path / "auth.json"))
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)

    repo = WorkspaceRepository()
    monkeypatch.setattr("keprix.workspace.repository.workspace_repo", repo)
    monkeypatch.setattr("keprix.workspace.routes.document_routes.workspace_repo", repo)
    monkeypatch.setattr("keprix.workspace.routes.editor_draft_routes.workspace_repo", repo)
    monkeypatch.setattr("keprix.workspace.routes.note_routes.workspace_repo", repo)
    monkeypatch.setattr("keprix.workspace.routes.task_routes.workspace_repo", repo)
    monkeypatch.setattr("keprix.workspace.routes.calendar_routes.workspace_repo", repo)
    monkeypatch.setattr("keprix.workspace.routes.session_routes.workspace_repo", repo)
    monkeypatch.setattr("keprix.workspace.routes.preset_routes.workspace_repo", repo)
    monkeypatch.setattr("keprix.workspace.routes.assistant_routes.workspace_repo", repo)
    monkeypatch.setattr("keprix.workspace.routes.personal_routes.workspace_repo", repo)
    monkeypatch.setattr("keprix.workspace.routes.admin_wipe_routes.workspace_repo", repo)

    client = TestClient(create_app())
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    token = login.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, repo, login.json()["user"]


def test_create_document_returns_id_and_word_count(workspace_client):
    client, _repo, _user = workspace_client
    response = client.post(
        "/api/workspace/documents",
        json={"title": "Hello", "content": "one two three", "format": "markdown"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["word_count"] == 3

    fetched = client.get(f"/api/workspace/documents/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["word_count"] == 3


def test_ai_edit_returns_modified_content(workspace_client):
    client, _repo, _user = workspace_client
    created = client.post(
        "/api/workspace/documents",
        json={"title": "Draft", "content": "# Title\n\nBody text.", "format": "markdown"},
    ).json()
    edited = client.post(
        f"/api/workspace/documents/{created['id']}/ai-edit",
        json={"instruction": "Add a summary"},
    )
    assert edited.status_code == 200
    assert "Add a summary" in edited.json()["content"]


def test_task_create_and_complete(workspace_client):
    client, _repo, _user = workspace_client
    created = client.post(
        "/api/workspace/tasks",
        json={"title": "Ship workspace API", "status": "todo"},
    )
    assert created.status_code == 201
    task_id = created.json()["id"]

    updated = client.put(
        f"/api/workspace/tasks/{task_id}",
        json={"status": "done"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "done"


def test_calendar_events_in_date_range(workspace_client):
    client, _repo, _user = workspace_client
    client.post(
        "/api/workspace/calendar/events",
        json={
            "title": "January meeting",
            "start_at": "2026-01-10T10:00:00Z",
            "end_at": "2026-01-10T11:00:00Z",
        },
    )
    client.post(
        "/api/workspace/calendar/events",
        json={
            "title": "February meeting",
            "start_at": "2026-02-10T10:00:00Z",
            "end_at": "2026-02-10T11:00:00Z",
        },
    )
    response = client.get(
        "/api/workspace/calendar/events",
        params={"start": "2026-01-01T00:00:00Z", "end": "2026-01-31T23:59:59Z"},
    )
    assert response.status_code == 200
    titles = [event["title"] for event in response.json()["items"]]
    assert titles == ["January meeting"]


def test_caldav_sync_with_env(workspace_client, monkeypatch):
    client, _repo, _user = workspace_client
    monkeypatch.setenv("CALDAV_URL", "https://caldav.example.com")
    response = client.post("/api/workspace/calendar/sync")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_draft_autosave_and_retrieve(workspace_client, monkeypatch):
    client, _repo, user = workspace_client
    user_id = str(user["id"])
    created = client.post(
        "/api/workspace/documents",
        json={"title": "Draft doc", "content": "initial", "format": "markdown"},
    ).json()
    doc_id = created["id"]

    saved = client.put(
        f"/api/workspace/documents/{doc_id}/draft",
        json={"content": "autosaved draft content"},
    )
    assert saved.status_code == 200

    draft = client.get(f"/api/workspace/documents/{doc_id}/draft")
    assert draft.status_code == 200
    assert draft.json()["content"] == "autosaved draft content"

    # Direct store check (in-memory fallback when Redis unavailable)
    assert draft_store.get(user_id, doc_id) == "autosaved draft content"
