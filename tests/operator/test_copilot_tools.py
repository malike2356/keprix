"""Tests for operator copilot tools and messaging (Prompt 212)."""

from __future__ import annotations

import json
import textwrap

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user
from keprix.operator import copilot_tools as tools
from keprix.operator.copilot import compose_operator_reply, stream_operator_copilot_message
from keprix.operator.context_bundle import build_operator_context


_VALID_TOOL = textwrap.dedent(
    '''
    from tools.registry import registry, tool_result

    def demo_tool_handler(args, **kwargs):
        return tool_result(success=True)

    registry.register(
        name="demo_tool",
        toolset="generated",
        schema={"name": "demo_tool", "description": "Demo", "parameters": {"type": "object", "properties": {}}},
        handler=demo_tool_handler,
    )
    '''
).strip() + "\n"


@pytest.fixture
def mutation_store(tmp_path, monkeypatch):
    from keprix.mutation.config import get_mutation_settings
    from keprix.mutation.store import MutationStore

    get_mutation_settings.cache_clear()
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.mutation.store.get_session_factory", lambda: None)
    monkeypatch.setenv("KEPRIX_TOOL_SIGNING_KEY", str(tmp_path / "signing.pem"))
    monkeypatch.setenv("KEPRIX_TOOL_VERIFY_KEY", str(tmp_path / "verify.pem"))
    monkeypatch.setenv("KEPRIX_MUTATION_GENERATED_TOOLS_DIR", str(tmp_path / "generated"))
    store = MutationStore(sqlite_path=tmp_path / "mutation.db")
    monkeypatch.setattr("keprix.mutation.store._store", store)
    monkeypatch.setattr("keprix.mutation.store.get_mutation_store", lambda: store)
    return store


@pytest.fixture
def auth_client(monkeypatch):
    app = create_app()

    async def _user() -> dict:
        return {"id": "test-user", "username": "test", "role": "admin"}

    app.dependency_overrides[get_current_user] = _user
    monkeypatch.setattr("keprix.mutation.routes.effective_access_level", lambda: "admin")
    return TestClient(app)


def test_read_only_tools_do_not_mutate(mutation_store) -> None:
    record = mutation_store.save_generated_tool(
        workspace_id="default",
        tool_name="demo_tool",
        description="Demo",
        source_code=_VALID_TOOL,
        trigger="test",
        confidence=0.7,
        auto_approve_threshold=0.85,
    )
    staged = tools.list_staged_mutations("default")
    assert len(staged) == 1
    assert staged[0]["id"] == record.id
    assert mutation_store.get_generated_tool(record.id).status == "staged"


def test_approve_mutation_requires_confirmation(mutation_store) -> None:
    record = mutation_store.save_generated_tool(
        workspace_id="default",
        tool_name="demo_tool",
        description="Demo",
        source_code=_VALID_TOOL,
        trigger="test",
        confidence=0.7,
        auto_approve_threshold=0.85,
    )
    pending = tools.approve_mutation(record.id, confirmed=False)
    assert pending["status"] == "approval_required"
    assert mutation_store.get_generated_tool(record.id).status == "staged"


@pytest.mark.asyncio
async def test_copilot_answers_approval_question(mutation_store) -> None:
    mutation_store.save_generated_tool(
        workspace_id="default",
        tool_name="demo_tool",
        description="Demo",
        source_code=_VALID_TOOL,
        trigger="test",
        confidence=0.7,
        auto_approve_threshold=0.85,
    )
    context = await build_operator_context("default")
    reply, events = await compose_operator_reply("What needs my approval?", context)
    assert "1 staged mutation" in reply
    assert any(event.get("name") == "list_staged_mutations" for event in events)


@pytest.mark.asyncio
async def test_stream_emits_approval_for_mutating_action(mutation_store) -> None:
    record = mutation_store.save_generated_tool(
        workspace_id="default",
        tool_name="demo_tool",
        description="Demo",
        source_code=_VALID_TOOL,
        trigger="test",
        confidence=0.7,
        auto_approve_threshold=0.85,
    )
    events = []
    async for event in stream_operator_copilot_message(f"approve mutation {record.id}"):
        events.append(event)
    assert any(event.get("event") == "approval" for event in events)
    assert mutation_store.get_generated_tool(record.id).status == "staged"


def test_copilot_message_route_streams_ndjson(auth_client, mutation_store) -> None:
    mutation_store.save_generated_tool(
        workspace_id="default",
        tool_name="demo_tool",
        description="Demo",
        source_code=_VALID_TOOL,
        trigger="test",
        confidence=0.7,
        auto_approve_threshold=0.85,
    )
    with auth_client.stream(
        "POST",
        "/api/operator/copilot/message",
        json={"message": "What needs my approval?", "workspace_id": "default"},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    lines = [json.loads(line) for line in body.splitlines() if line.strip()]
    text = "".join(str(item.get("content") or "") for item in lines if item.get("event") == "text_delta")
    assert "1 staged mutation" in text
