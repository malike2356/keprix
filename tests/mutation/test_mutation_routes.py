"""Tests for mutation pipeline REST API (Prompt 151)."""

from __future__ import annotations

import textwrap

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.mutation.config import get_mutation_settings
from keprix.mutation.store import MutationStore
from keprix.mutation.tool_synthesizer import SynthesisResult
from keprix.public_api.auth import require_developer_session

_VALID_TOOL = textwrap.dedent(
    '''
    from tools.registry import registry, tool_result, tool_error

    def demo_tool_handler(args, **kwargs):
        return tool_result(success=True)

    registry.register(
        name="demo_tool",
        toolset="generated",
        schema={
            "name": "demo_tool",
            "description": "Demo tool",
            "parameters": {"type": "object", "properties": {}},
        },
        handler=demo_tool_handler,
    )
    '''
).strip() + "\n"


@pytest.fixture
def mutation_store(tmp_path, monkeypatch):
    get_mutation_settings.cache_clear()
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.mutation.store.get_session_factory", lambda: None)
    monkeypatch.setenv("KEPRIX_TOOL_SIGNING_KEY", str(tmp_path / "signing.pem"))
    monkeypatch.setenv("KEPRIX_TOOL_VERIFY_KEY", str(tmp_path / "verify.pem"))
    monkeypatch.setenv("KEPRIX_MUTATION_GENERATED_TOOLS_DIR", str(tmp_path / "generated"))
    store = MutationStore(sqlite_path=tmp_path / "mutation.db")
    monkeypatch.setattr("keprix.mutation.store._store", store)
    monkeypatch.setattr("keprix.mutation.store.get_mutation_store", lambda: store)
    return store, tmp_path


@pytest.fixture
def client(mutation_store, monkeypatch):
    app = create_app()

    async def _auth() -> str:
        return "dev"

    app.dependency_overrides[require_developer_session] = _auth
    monkeypatch.setattr(
        "keprix.mutation.routes.effective_access_level",
        lambda: "admin",
    )
    return TestClient(app)


def test_list_generated_tools_returns_paginated(client, mutation_store):
    store, _tmp = mutation_store
    store.save_generated_tool(
        workspace_id="default",
        tool_name="demo_tool",
        description="Demo",
        source_code=_VALID_TOOL,
        trigger="test",
        confidence=0.7,
        auto_approve_threshold=0.85,
    )
    response = client.get("/api/mutation/tools?status=staged")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["page"] == 1
    assert payload["items"][0]["name"] == "demo_tool"


def test_approve_staged_tool_writes_to_disk_and_loads(client, mutation_store):
    store, tmp_path = mutation_store
    record = store.save_generated_tool(
        workspace_id="default",
        tool_name="demo_tool",
        description="Demo",
        source_code=_VALID_TOOL,
        trigger="test",
        confidence=0.7,
        auto_approve_threshold=0.85,
    )
    response = client.post(f"/api/mutation/tools/{record.id}/approve")
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert (tmp_path / "generated" / "demo_tool.py").exists()
    from tools.registry import registry

    assert registry.get_tool("demo_tool") is not None


def test_reject_staged_tool_sets_rejected(client, mutation_store):
    store, _tmp = mutation_store
    record = store.save_generated_tool(
        workspace_id="default",
        tool_name="demo_tool",
        description="Demo",
        source_code=_VALID_TOOL,
        trigger="test",
        confidence=0.7,
        auto_approve_threshold=0.85,
    )
    response = client.post(
        f"/api/mutation/tools/{record.id}/reject",
        json={"reason": "not needed"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    from tools.registry import registry

    assert registry.get_tool("demo_tool") is None


def test_rollback_approved_tool_deregisters(client, mutation_store):
    store, tmp_path = mutation_store
    record = store.save_generated_tool(
        workspace_id="default",
        tool_name="demo_tool",
        description="Demo",
        source_code=_VALID_TOOL,
        trigger="test",
        confidence=0.9,
        auto_approve_threshold=0.85,
    )
    store.approve_mutation(record.id, approved_by="test")
    from tools.registry import registry

    assert registry.get_tool("demo_tool") is not None
    response = client.post(f"/api/mutation/tools/{record.id}/rollback")
    assert response.status_code == 200
    assert registry.get_tool("demo_tool") is None
    assert not (tmp_path / "generated" / "demo_tool.py").exists()


def test_synthesize_endpoint_returns_202(client, monkeypatch):
    async def fake_synthesize(proposal, workspace_id, **kwargs):
        return SynthesisResult(
            success=True,
            tool_name="manual_tool",
            source_code=_VALID_TOOL.replace("demo_tool", "manual_tool"),
            inferred_schema=None,
            sandbox_result=None,
            error=None,
            attempts=1,
            tokens_used=1,
        )

    monkeypatch.setattr("keprix.mutation.routes.synthesize_tool", fake_synthesize)
    response = client.post(
        "/api/mutation/synthesize",
        json={"tool_name": "manual_tool", "description": "Manual synthesis"},
    )
    assert response.status_code == 202
    assert response.json()["name"] == "manual_tool"


def test_stats_endpoint_returns_counts(client, mutation_store):
    store, _tmp = mutation_store
    store.save_generated_tool(
        workspace_id="default",
        tool_name="demo_tool",
        description="Demo",
        source_code=_VALID_TOOL,
        trigger="test",
        confidence=0.7,
        auto_approve_threshold=0.85,
    )
    response = client.get("/api/mutation/stats")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["counts"]["tool"]["staged"] == 1


def test_unauthorized_cannot_access_mutation_api(mutation_store, monkeypatch):
    app = create_app()
    monkeypatch.setattr(
        "keprix.mutation.routes.effective_access_level",
        lambda: "viewer",
    )

    async def _auth() -> str:
        return "dev"

    app.dependency_overrides[require_developer_session] = _auth
    client = TestClient(app)
    store, _tmp = mutation_store
    record = store.save_generated_tool(
        workspace_id="default",
        tool_name="demo_tool",
        description="Demo",
        source_code=_VALID_TOOL,
        trigger="test",
        confidence=0.7,
        auto_approve_threshold=0.85,
    )
    response = client.post(f"/api/mutation/tools/{record.id}/approve")
    assert response.status_code == 403
