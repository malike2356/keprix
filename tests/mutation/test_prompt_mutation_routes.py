"""Tests for prompt/persona mutation API routes (Prompt 152)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.mutation.config import get_mutation_settings
from keprix.mutation.prompt_store import PromptStore
from keprix.mutation.store import MutationStore
from keprix.public_api.auth import require_developer_session


@pytest.fixture
def stores(tmp_path, monkeypatch):
    get_mutation_settings.cache_clear()
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.mutation.store.get_session_factory", lambda: None)
    mutation_store = MutationStore(sqlite_path=tmp_path / "mutation.db")
    prompt_store = PromptStore(sqlite_path=tmp_path / "mutation.db", mutation_store=mutation_store)
    monkeypatch.setattr("keprix.mutation.store._store", mutation_store)
    monkeypatch.setattr("keprix.mutation.store.get_mutation_store", lambda: mutation_store)
    monkeypatch.setattr("keprix.mutation.prompt_store._store", prompt_store)
    monkeypatch.setattr("keprix.mutation.prompt_store.get_prompt_store", lambda: prompt_store)
    return prompt_store


@pytest.fixture
def client(stores, monkeypatch):
    app = create_app()

    async def _auth() -> str:
        return "dev"

    app.dependency_overrides[require_developer_session] = _auth
    monkeypatch.setattr(
        "keprix.mutation.routes.effective_access_level",
        lambda: "admin",
    )
    return TestClient(app)


def test_list_prompt_versions_paginated(client, stores):
    stores.stage_improvement(
        workspace_id="default",
        prompt_key="default",
        suggested_content="Prompt v1",
        rationale="test",
        confidence=0.70,
        auto_approve_threshold=0.85,
    )
    response = client.get("/api/mutation/prompts?prompt_key=default")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["prompt_key"] == "default"


def test_history_for_key_returns_ordered(client, stores):
    stores.stage_improvement(
        workspace_id="default",
        prompt_key="default",
        suggested_content="Prompt v1",
        rationale="test",
        confidence=0.70,
        auto_approve_threshold=0.85,
    )
    stores.stage_improvement(
        workspace_id="default",
        prompt_key="default",
        suggested_content="Prompt v2",
        rationale="test",
        confidence=0.70,
        auto_approve_threshold=0.85,
    )
    response = client.get("/api/mutation/prompts/default/history")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    assert items[0]["version"] > items[1]["version"]


def test_approve_staged_version_activates(client, stores):
    version = stores.stage_improvement(
        workspace_id="default",
        prompt_key="default",
        suggested_content="Prompt staged",
        rationale="test",
        confidence=0.70,
        auto_approve_threshold=0.85,
    )
    assert version.is_active is False
    response = client.post("/api/mutation/prompts/default/approve")
    assert response.status_code == 200
    assert response.json()["is_active"] is True
    assert stores.get_active_prompt("default", "default") == "Prompt staged"


def test_rollback_restores_previous(client, stores):
    stores.stage_improvement(
        workspace_id="default",
        prompt_key="default",
        suggested_content="Prompt v1",
        rationale="test",
        confidence=0.90,
        auto_approve_threshold=0.85,
    )
    stores.stage_improvement(
        workspace_id="default",
        prompt_key="default",
        suggested_content="Prompt v2",
        rationale="test",
        confidence=0.90,
        auto_approve_threshold=0.85,
    )
    response = client.post("/api/mutation/prompts/default/rollback")
    assert response.status_code == 200
    assert response.json()["content"] == "Prompt v1"
    assert stores.get_active_prompt("default", "default") == "Prompt v1"
