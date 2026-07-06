"""Tests for Prompt 136: agent conversation workspace API."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.security.rate_limiter import reset_rate_limits
from keprix.workspace.repository import WorkspaceRepository


@pytest.fixture
def conversation_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    reset_rate_limits()

    auth = AuthManager(str(tmp_path / "auth.json"))
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)

    repo = WorkspaceRepository()
    monkeypatch.setattr("keprix.workspace.repository.workspace_repo", repo)
    monkeypatch.setattr("keprix.api.conversation_routes.workspace_repo", repo)
    monkeypatch.setattr("keprix.api.dashboard_routes.workspace_repo", repo)

    client = TestClient(create_app())
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    token = login.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, repo


def test_models_available(conversation_client):
    client, _repo = conversation_client
    response = client.get("/api/models/available")
    assert response.status_code == 200
    models = response.json()["models"]
    assert len(models) >= 1
    assert {"id", "provider", "name"}.issubset(models[0].keys())


def test_create_list_and_get_conversation(conversation_client):
    client, _repo = conversation_client
    created = client.post("/api/conversations", json={"title": "Planning chat"})
    assert created.status_code == 200
    body = created.json()
    session_id = body["id"]
    assert body["title"] == "Planning chat"
    assert body["messages"] == []

    listed = client.get("/api/conversations?limit=10")
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert any(item["id"] == session_id for item in items)

    fetched = client.get(f"/api/conversations/{session_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == session_id


def test_send_message_streams_ndjson(conversation_client):
    client, _repo = conversation_client
    session_id = client.post("/api/conversations", json={"title": "Stream test"}).json()["id"]

    with client.stream(
        "POST",
        f"/api/conversations/{session_id}/messages",
        json={"content": "/status", "file_ids": [], "model": "ollama:llama3.2"},
    ) as response:
        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("application/x-ndjson")
        events: list[dict] = []
        for line in response.iter_lines():
            if not line:
                continue
            events.append(json.loads(line))

    assert any(event.get("event") == "text_delta" for event in events)
    assert any(event.get("event") == "message_done" for event in events)

    session = client.get(f"/api/conversations/{session_id}").json()
    roles = [message["role"] for message in session["messages"]]
    assert roles == ["user", "assistant"]


def test_rename_and_delete_conversation(conversation_client):
    client, _repo = conversation_client
    session_id = client.post("/api/conversations", json={"title": "Old title"}).json()["id"]

    renamed = client.put(f"/api/conversations/{session_id}", json={"title": "Renamed"})
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Renamed"

    deleted = client.delete(f"/api/conversations/{session_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/conversations/{session_id}").status_code == 404


def test_upload_file_returns_metadata(conversation_client):
    client, _repo = conversation_client
    response = client.post(
        "/api/files/upload",
        files={"file": ("notes.txt", b"hello workspace", "text/plain")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"]
    assert payload["filename"] == "notes.txt"
    assert payload["size"] == len(b"hello workspace")
