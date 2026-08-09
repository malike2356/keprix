"""Tests for Carina/Aiva agent contract: POST /carina/agent/run."""

from __future__ import annotations

import asyncio
import json
from json import dumps as json_module_dumps
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.agent.carina_bridge import (
    CarinaAgentBridge,
    CarinaToolRegistry,
    LlmTurn,
    ProviderPool,
    SessionStore,
)
from keprix.api import carina_agent_routes


class _StubResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code


class _StubHttpClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def post(self, endpoint: str, json: dict[str, Any], headers: dict[str, str]) -> _StubResponse:
        self.calls.append({"endpoint": endpoint, "json": json, "headers": headers})
        assert "search_contacts" in endpoint
        assert headers.get("Authorization", "").startswith("Bearer ")
        payload = {"contacts": [{"name": "Alex Investor"}], "count": 1}
        return _StubResponse(json_module_dumps(payload))

    async def aclose(self) -> None:
        return None


@pytest.fixture()
def shared_token(monkeypatch: pytest.MonkeyPatch) -> str:
    token = "test-carina-keprix-shared"
    monkeypatch.setenv("CARINA_KEPRIX_SHARED_TOKEN", token)
    return token


@pytest.fixture()
def client(shared_token: str, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    store = SessionStore()
    calls: list[dict[str, Any]] = []
    http_client = _StubHttpClient()

    async def fake_complete(**kwargs: Any) -> LlmTurn:
        calls.append(kwargs)
        n = len(calls)
        tools = kwargs.get("tools") or []
        tool_names = {
            (t.get("function") or {}).get("name")
            for t in tools
            if isinstance(t, dict)
        }
        if "search_contacts" in tool_names and n == 1:
            return LlmTurn(
                content=None,
                tool_calls=[
                    {
                        "id": "call_001",
                        "type": "function",
                        "function": {
                            "name": "search_contacts",
                            "arguments": json.dumps({"query": "Portsmouth"}),
                        },
                    }
                ],
                finish_reason="tool_calls",
                usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            )
        return LlmTurn(
            content="I found 12 property investors in Portsmouth.",
            tool_calls=[],
            finish_reason="stop",
            usage={"prompt_tokens": 20, "completion_tokens": 12, "total_tokens": 32},
        )

    registry = CarinaToolRegistry(
        native_dispatch=lambda name, args: json.dumps({"native": name, "args": args}),
        http_client=http_client,  # type: ignore[arg-type]
    )

    bridge = CarinaAgentBridge(
        tool_registry=registry,
        provider_pool=ProviderPool(complete_fn=fake_complete, fallbacks=[]),
        session_store=store,
    )
    monkeypatch.setattr(carina_agent_routes, "bridge", bridge)

    app = FastAPI()
    app.include_router(carina_agent_routes.router)
    app.state.test_calls = calls
    app.state.test_store = store
    app.state.http_client = http_client
    return TestClient(app)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _payload(**overrides: Any) -> dict[str, Any]:
    workspace_id = str(overrides.get("workspace_id") or "ws_abc123")
    body = {
        "workspace_id": workspace_id,
        "session_id": "sess_xyz789",
        "model": "deepseek-v4-pro",
        "temperature": 0.7,
        "system_prompt": "You are an Aiva worker.",
        "messages": [{"role": "user", "content": "Find me property investors in Portsmouth"}],
        "tools": [
            {
                "name": "search_contacts",
                "description": "Search CRM contacts by criteria",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
            }
        ],
        "carina_tools": [
            {
                "name": "search_contacts",
                "http_endpoint": "http://carina:80/api/carina/tools/search_contacts",
                "auth_header": "Bearer carina-shared",
                "workspace_id": workspace_id,
                "user_id": "42",
                "conversation_id": "99",
                "correlation_id": "corr_test",
            }
        ],
    }
    body.update(overrides)
    # Keep trusted callback metadata aligned with the request workspace.
    if "carina_tools" not in overrides:
        for tool in body.get("carina_tools") or []:
            if isinstance(tool, dict):
                tool["workspace_id"] = body["workspace_id"]
    return body


def test_agent_run_valid_auth_returns_response(client: TestClient, shared_token: str) -> None:
    response = client.post("/carina/agent/run", headers=_auth(shared_token), json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["finish_reason"] == "stop"
    assert body["session_id"] == "sess_xyz789"
    assert "property investors" in body["message"]["content"]
    assert body["usage"]["total_tokens"] >= 15
    assert body["tool_calls"] == []


def test_agent_run_invalid_auth_returns_401(client: TestClient) -> None:
    response = client.post(
        "/carina/agent/run",
        headers={"Authorization": "Bearer wrong"},
        json=_payload(),
    )
    assert response.status_code == 401


def test_agent_run_missing_auth_returns_401(client: TestClient) -> None:
    response = client.post("/carina/agent/run", json=_payload())
    assert response.status_code == 401


def test_carina_http_tool_routing(client: TestClient, shared_token: str) -> None:
    response = client.post("/carina/agent/run", headers=_auth(shared_token), json=_payload())
    assert response.status_code == 200
    assert len(client.app.state.test_calls) == 2
    http_calls = client.app.state.http_client.calls
    assert len(http_calls) == 1
    payload = http_calls[0]["json"]
    assert payload["query"] == "Portsmouth"
    assert payload["workspace_id"] == "ws_abc123"
    assert str(payload["user_id"]) == "42"
    assert str(payload["conversation_id"]) == "99"
    assert payload["correlation_id"] == "corr_test"
    headers = http_calls[0]["headers"]
    assert headers.get("X-Keprix-Trusted-Workspace-Id") == "ws_abc123"
    assert headers.get("X-Keprix-Trusted-Actor-Id") == "42"


def test_model_cannot_redirect_callback_to_other_tenant(
    client: TestClient, shared_token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even if the model emits workspace_id for tenant B, trusted A wins."""
    store = SessionStore()
    http_client = _StubHttpClient()

    async def fake_complete(**kwargs: Any) -> LlmTurn:
        if getattr(fake_complete, "done", False):
            return LlmTurn(
                content="done",
                tool_calls=[],
                finish_reason="stop",
                usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            )
        fake_complete.done = True  # type: ignore[attr-defined]
        tools = kwargs.get("tools") or []
        tool_names = {
            (t.get("function") or {}).get("name")
            for t in tools
            if isinstance(t, dict)
        }
        if "search_contacts" in tool_names:
            return LlmTurn(
                content=None,
                tool_calls=[
                    {
                        "id": "call_hijack",
                        "type": "function",
                        "function": {
                            "name": "search_contacts",
                            "arguments": json.dumps(
                                {"query": "x", "workspace_id": "tenant-B-evil", "user_id": "999"}
                            ),
                        },
                    }
                ],
                finish_reason="tool_calls",
                usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            )
        return LlmTurn(
            content="done",
            tool_calls=[],
            finish_reason="stop",
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        )

    bridge = CarinaAgentBridge(
        tool_registry=CarinaToolRegistry(http_client=http_client),  # type: ignore[arg-type]
        provider_pool=ProviderPool(complete_fn=fake_complete, fallbacks=[]),
        session_store=store,
    )
    monkeypatch.setattr(carina_agent_routes, "bridge", bridge)
    app = FastAPI()
    app.include_router(carina_agent_routes.router)
    local = TestClient(app)
    response = local.post("/carina/agent/run", headers=_auth(shared_token), json=_payload())
    assert response.status_code == 200
    assert len(http_client.calls) == 1
    body = http_client.calls[0]["json"]
    assert body["workspace_id"] == "ws_abc123"
    assert str(body["user_id"]) == "42"
    assert "tenant-B-evil" not in str(body)

def test_session_persists_across_calls(client: TestClient, shared_token: str) -> None:
    first = client.post("/carina/agent/run", headers=_auth(shared_token), json=_payload())
    assert first.status_code == 200

    second = client.post(
        "/carina/agent/run",
        headers=_auth(shared_token),
        json=_payload(
            tools=[],
            carina_tools=[],
            messages=[{"role": "user", "content": "Summarise what you found"}],
        ),
    )
    assert second.status_code == 200
    stored = client.app.state.test_store._sessions["ws_abc123::sess_xyz789"]
    assert any(m.get("role") == "assistant" for m in stored)


def test_workspace_isolation(client: TestClient, shared_token: str) -> None:
    assert (
        client.post(
            "/carina/agent/run",
            headers=_auth(shared_token),
            json=_payload(workspace_id="ws_a", session_id="sess_shared"),
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/carina/agent/run",
            headers=_auth(shared_token),
            json=_payload(workspace_id="ws_b", session_id="sess_shared"),
        ).status_code
        == 200
    )
    store: SessionStore = client.app.state.test_store
    assert "ws_a::sess_shared" in store._sessions
    assert "ws_b::sess_shared" in store._sessions
    assert store._sessions["ws_a::sess_shared"] is not store._sessions["ws_b::sess_shared"]


def test_unregistered_tool_returns_error(
    client: TestClient, shared_token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def tool_call_unknown(**kwargs: Any) -> LlmTurn:
        return LlmTurn(
            content=None,
            tool_calls=[
                {
                    "id": "call_x",
                    "type": "function",
                    "function": {"name": "ghost_tool", "arguments": "{}"},
                }
            ],
            finish_reason="tool_calls",
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        )

    monkeypatch.setattr(
        carina_agent_routes.bridge,
        "provider_pool",
        ProviderPool(complete_fn=tool_call_unknown, fallbacks=[]),
    )
    response = client.post(
        "/carina/agent/run",
        headers=_auth(shared_token),
        json=_payload(tools=[], carina_tools=[]),
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["tool"] == "ghost_tool"
    assert detail["error"] == "tool_not_registered"


def test_provider_failover() -> None:
    attempts: list[str] = []

    async def flaky(**kwargs: Any) -> LlmTurn:
        provider = kwargs["provider"]
        attempts.append(provider)
        if provider == "deepseek":
            raise RuntimeError("primary down")
        return LlmTurn(
            content="failover ok",
            tool_calls=[],
            finish_reason="stop",
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            provider=provider,
        )

    pool = ProviderPool(
        complete_fn=flaky,
        fallbacks=[("openai", "gpt-4.1-mini")],
    )
    bridge = CarinaAgentBridge(
        provider_pool=pool,
        session_store=SessionStore(),
        tool_registry=CarinaToolRegistry(native_dispatch=lambda n, a: "{}"),
    )

    result = asyncio.run(
        bridge.run(
            workspace_id="ws_1",
            session_id="s1",
            model="deepseek:deepseek-v4-pro",
            temperature=0.2,
            system_prompt="sys",
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
            carina_tools=[],
        )
    )
    assert result["message"]["content"] == "failover ok"
    assert attempts == ["deepseek", "openai"]


def test_native_tool_preferred_over_http(monkeypatch: pytest.MonkeyPatch) -> None:
    native_hits: list[str] = []

    def native_dispatch(name: str, args: dict[str, Any]) -> str:
        native_hits.append(name)
        return json.dumps({"ok": True, "args": args})

    async def complete_once(**kwargs: Any) -> LlmTurn:
        if not getattr(complete_once, "done", False):
            complete_once.done = True  # type: ignore[attr-defined]
            return LlmTurn(
                content=None,
                tool_calls=[
                    {
                        "id": "call_n",
                        "type": "function",
                        "function": {
                            "name": "native_echo",
                            "arguments": json.dumps({"x": 1}),
                        },
                    }
                ],
                finish_reason="tool_calls",
                usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            )
        return LlmTurn(
            content="native done",
            tool_calls=[],
            finish_reason="stop",
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        )

    def fake_exists(self: CarinaToolRegistry, name: str) -> bool:
        return name == "native_echo"

    monkeypatch.setattr(CarinaToolRegistry, "_native_exists", fake_exists)

    bridge = CarinaAgentBridge(
        tool_registry=CarinaToolRegistry(native_dispatch=native_dispatch),
        provider_pool=ProviderPool(complete_fn=complete_once, fallbacks=[]),
        session_store=SessionStore(),
    )

    result = asyncio.run(
        bridge.run(
            workspace_id="ws_1",
            session_id="s1",
            model="deepseek:x",
            temperature=0.1,
            system_prompt="sys",
            messages=[{"role": "user", "content": "go"}],
            tools=[{"name": "native_echo", "description": "echo", "parameters": {}}],
            carina_tools=[
                {
                    "name": "native_echo",
                    "http_endpoint": "http://carina/should-not-call",
                    "auth_header": "Bearer x",
                    "workspace_id": "ws_1",
                    "user_id": "1",
                }
            ],
        )
    )
    assert result["message"]["content"] == "native done"
    assert native_hits == ["native_echo"]
