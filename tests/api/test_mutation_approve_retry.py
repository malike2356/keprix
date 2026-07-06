"""API tests for mutation approve retry flow (Prompt 141)."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from keprix.agent.keprix.mutation import MutationEngine
from keprix.agent.keprix.store import GeneratedToolStore
from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.governance.policy_receiver import get_policy_registry
from keprix.security.rate_limiter import reset_rate_limits
from keprix.workspace.repository import WorkspaceRepository


@pytest.fixture
def approve_client(tmp_path, monkeypatch):
    tools_dir = tmp_path / "generated" / "tools"
    skills_dir = tmp_path / "generated" / "skills"
    store_dir = tmp_path / "mutation"
    tools_dir.mkdir(parents=True)
    skills_dir.mkdir(parents=True)

    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_MUTATION_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_MUTATION_REQUIRED_CHANNELS", "web_ui")
    monkeypatch.setenv("KEPRIX_GENERATED_TOOLS_DIR", str(tools_dir))
    monkeypatch.setenv("KEPRIX_GENERATED_SKILLS_DIR", str(skills_dir))
    monkeypatch.setenv("KEPRIX_TOOL_SIGNING_KEY", str(tmp_path / "signing.pem"))
    monkeypatch.setenv("KEPRIX_TOOL_VERIFY_KEY", str(tmp_path / "verify.pem"))
    reset_rate_limits()
    get_policy_registry().reload_from_store([])

    store = GeneratedToolStore(path=store_dir / "generated_tools.json")
    monkeypatch.setattr("keprix.agent.keprix.store.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.mutation.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.approval.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.auditor.get_generated_tool_store", lambda: store)
    monkeypatch.setattr("keprix.agent.keprix.mutation._engine", None)
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.observability.metrics.get_session_factory", lambda: None)

    auth = AuthManager(str(tmp_path / "auth.json"))
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)

    repo = WorkspaceRepository()
    monkeypatch.setattr("keprix.workspace.repository.workspace_repo", repo)
    monkeypatch.setattr("keprix.api.conversation_routes.workspace_repo", repo)

    client = TestClient(create_app())
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    token = login.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, repo, store, tools_dir


def _stock_tool_code() -> str:
    return '''
"""Generated tool: fetch_stock_price"""
from tools.registry import registry, tool_result, tool_error

_MOCK_PRICES = {"AAPL": 213.42}

def fetch_stock_price_handler(args, **kwargs):
    ticker = str(args.get("ticker", "")).upper().strip()
    if not ticker:
        return tool_error("ticker is required")
    return tool_result(success=True, ticker=ticker, price=_MOCK_PRICES.get(ticker, 0.0))

registry.register(
    name="fetch_stock_price",
    toolset="generated",
    schema={
        "name": "fetch_stock_price",
        "description": "Fetch stock price",
        "parameters": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        },
    },
    handler=fetch_stock_price_handler,
    emoji="🧬",
)
'''.strip()


def _track_time_tool_code() -> str:
    return '''
"""Generated tool: track_time"""
from tools.registry import registry, tool_result, tool_error

def track_time_handler(args, **kwargs):
    project = str(args.get("project", "")).strip()
    if not project:
        return tool_error("project is required")
    action = str(args.get("action", "start")).strip().lower()
    return tool_result(success=True, project=project, action=action)

registry.register(
    name="track_time",
    toolset="generated",
    schema={
        "name": "track_time",
        "description": "Track project time",
        "parameters": {
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "action": {"type": "string"},
            },
            "required": ["project"],
        },
    },
    handler=track_time_handler,
    emoji="🧬",
)
'''.strip()


def _create_pending_record(
    store: GeneratedToolStore,
    *,
    task: str,
    tool_name: str,
    tool_code: str,
    session_id: str,
) -> str:
    record = store.create(
        task_that_triggered=task,
        tool_name=tool_name,
        tool_code=tool_code,
        skill_yaml=f"name: {tool_name}",
        description=f"Generated {tool_name}",
        gap_description="gap",
        static_analysis={"safe": True, "violations": []},
        sandbox_result={"passed": True, "output": "ok", "exit_code": 0},
        session_id=session_id,
        metadata={"original_task": task, "session_id": session_id},
    )
    return record.id


def test_approve_stock_mutation_persists_retry_message(approve_client):
    client, _repo, store, _tools_dir = approve_client
    session_id = client.post("/api/conversations", json={"title": "Retry chat"}).json()["id"]
    record_id = _create_pending_record(
        store,
        task="fetch AAPL stock price",
        tool_name="fetch_stock_price",
        tool_code=_stock_tool_code(),
        session_id=session_id,
    )

    response = client.post(f"/api/mutations/{record_id}/approve?session_id={session_id}&channel=web_ui")
    assert response.status_code == 200
    body = response.json()
    assert body["retry_message"]
    assert "213.42" in body["retry_message"] or "AAPL" in body["retry_message"]
    assert body["message"]["role"] == "assistant"

    fetched = client.get(f"/api/conversations/{session_id}").json()
    assistant_messages = [message for message in fetched["messages"] if message["role"] == "assistant"]
    assert assistant_messages
    text_blocks = [
        block
        for message in assistant_messages
        for block in message.get("content", [])
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    assert any(body["retry_message"] in str(block.get("content", "")) for block in text_blocks)


def test_approve_track_time_retry_mentions_project(approve_client):
    client, _repo, store, _tools_dir = approve_client
    session_id = client.post("/api/conversations", json={"title": "Time chat"}).json()["id"]
    record_id = _create_pending_record(
        store,
        task="Track my time on this project",
        tool_name="track_time",
        tool_code=_track_time_tool_code(),
        session_id=session_id,
    )

    response = client.post(f"/api/mutations/{record_id}/approve?session_id={session_id}&channel=web_ui")
    assert response.status_code == 200
    body = response.json()
    assert body["retry_message"]
    assert "project" in body["retry_message"].lower() or "timer" in body["retry_message"].lower()
