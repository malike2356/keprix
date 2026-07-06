"""Memory API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app


@pytest.fixture(autouse=True)
def _deterministic_memory(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("KEPRIX_EMBEDDING_DETERMINISTIC", "true")


@pytest.fixture
def client():
    return TestClient(create_app())


def test_memory_list_empty_for_new_user(client):
    response = client.get("/api/memory/list", headers={"X-User-Id": "new-user"})
    assert response.status_code == 200
    assert response.json() == {"memories": []}


def test_memory_save_and_list(client):
    save = client.post(
        "/api/memory/save",
        json={"content": "User prefers morning meetings", "tags": ["preference"]},
        headers={"X-User-Id": "user-a"},
    )
    assert save.status_code == 200
    assert save.json()["ok"] is True

    listed = client.get("/api/memory/list", headers={"X-User-Id": "user-a"})
    assert listed.status_code == 200
    assert len(listed.json()["memories"]) == 1


def test_memory_search(client):
    client.post(
        "/api/memory/save",
        json={"content": "Favorite editor is Neovim"},
        headers={"X-User-Id": "user-b"},
    )
    client.post(
        "/api/memory/save",
        json={"content": "Project deadline is Friday"},
        headers={"X-User-Id": "user-b"},
    )
    response = client.post(
        "/api/memory/search",
        json={"query": "editor"},
        headers={"X-User-Id": "user-b"},
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert results
    assert "Neovim" in results[0]["content"]
