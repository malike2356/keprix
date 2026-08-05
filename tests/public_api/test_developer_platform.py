"""Tests for the OpenAI-compatible public API and developer platform."""

from __future__ import annotations

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.server import create_app
from keprix.public_api.keys import ApiKeyStore, CreateApiKeyRequest
from keprix.public_api.logs import redact_request_body
from keprix.public_api.webhooks import sign_payload, verify_signature


@pytest.fixture(autouse=True)
def disable_database(monkeypatch):
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.observability.metrics.get_session_factory", lambda: None)


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


@pytest.fixture
def key_store(tmp_path, monkeypatch):
    store = ApiKeyStore(path=tmp_path / "api_keys.json")
    monkeypatch.setattr("keprix.public_api.keys.get_api_key_store", lambda: store)
    monkeypatch.setattr("keprix.public_api.auth.get_api_key_store", lambda: store)
    monkeypatch.setattr("keprix.public_api.developer_routes.get_api_key_store", lambda: store)
    monkeypatch.setattr("keprix.public_api.usage.get_api_key_store", lambda: store)
    return store


@pytest.fixture
def mock_agent_runtime(monkeypatch):
    from keprix.public_api.agent_runtime import AgentChatResult

    async def _fake_run(**_kwargs):
        return AgentChatResult(
            final_response="Agent runtime response",
            session_id="session-test-1",
            prompt_tokens=4,
            completion_tokens=6,
            total_tokens=10,
        )

    monkeypatch.setattr("keprix.public_api.openai_compat.run_agent_chat_completion", _fake_run)
    monkeypatch.setattr("keprix.public_api.responses.run_agent_chat_completion", _fake_run)
    monkeypatch.setattr("keprix.api.public_v1_routes.run_agent_chat_completion", _fake_run)
    return _fake_run


@pytest.mark.asyncio
async def test_openai_chat_completion_shape(client, key_store, mock_agent_runtime):
    created = key_store.create(CreateApiKeyRequest(name="test"))
    response = await client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {created.secret}"},
        json={
            "model": "keprix",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "chat.completion"
    assert payload["choices"][0]["message"]["role"] == "assistant"
    assert payload["choices"][0]["message"]["content"] == "Agent runtime response"
    assert payload["usage"]["total_tokens"] > 0


@pytest.mark.asyncio
async def test_openai_chat_completion_rejects_missing_user_message(client, key_store):
    created = key_store.create(CreateApiKeyRequest(name="bad-body"))
    response = await client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {created.secret}"},
        json={"model": "keprix", "messages": [{"role": "assistant", "content": "only assistant"}]},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_invalid_api_key_rejected(client, key_store):
    response = await client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer kp_invalid"},
        json={"model": "keprix", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_deleted_api_key_stops_working(client, key_store):
    created = key_store.create(CreateApiKeyRequest(name="revoke-me"))
    key_store.revoke(created.id)
    response = await client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {created.secret}"},
        json={"model": "keprix", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_usage_recorded_on_completion(client, key_store, mock_agent_runtime):
    created = key_store.create(CreateApiKeyRequest(name="usage"))
    await client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {created.secret}"},
        json={"model": "keprix", "messages": [{"role": "user", "content": "count tokens"}]},
    )
    keys = key_store.list_keys()
    match = next(key for key in keys if key.id == created.id)
    assert match.usage_this_month >= 1


@pytest.mark.asyncio
async def test_rate_limit_blocks_excessive_calls(client, key_store, monkeypatch, mock_agent_runtime):
    from keprix.security.rate_limit import InMemoryRateLimiter, RateLimitRule

    limiter = InMemoryRateLimiter()
    rule = RateLimitRule(name="agent_chat", limit=2, window_seconds=60, key_prefix="rl:test")

    class _FakeLimiter:
        def check(self, identifier, _rule):
            return limiter.hit(identifier, rule)

    monkeypatch.setattr("keprix.public_api.rate_limits.get_rate_limiter", lambda: _FakeLimiter())
    monkeypatch.setattr("keprix.security.rate_limit.get_rate_limiter", lambda: _FakeLimiter())

    created = key_store.create(CreateApiKeyRequest(name="rl"))
    headers = {"Authorization": f"Bearer {created.secret}"}
    body = {"model": "keprix", "messages": [{"role": "user", "content": "x"}]}
    assert (await client.post("/v1/chat/completions", headers=headers, json=body)).status_code == 200
    assert (await client.post("/v1/chat/completions", headers=headers, json=body)).status_code == 200
    blocked = await client.post("/v1/chat/completions", headers=headers, json=body)
    assert blocked.status_code == 429


def test_webhook_signature_valid():
    secret = "whsec_test"
    payload = b'{"event":"test"}'
    signature = sign_payload(secret, payload)
    assert verify_signature(secret, payload, signature)


def test_logs_redact_secrets():
    body = "Authorization: Bearer sk-abcdefghijklmnopqrstuvwxyz1234"
    redacted = redact_request_body(body)
    assert "sk-abcdefghijklmnopqrstuvwxyz1234" not in redacted


@pytest.mark.asyncio
async def test_models_endpoint(client, key_store):
    created = key_store.create(CreateApiKeyRequest(name="models"))
    response = await client.get(
        "/v1/models",
        headers={"Authorization": f"Bearer {created.secret}"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert any(item["id"] == "keprix" for item in data)


@pytest.mark.asyncio
async def test_embeddings_returns_vectors(client, key_store):
    from keprix.memory.embeddings import EMBEDDING_DIM

    created = key_store.create(
        CreateApiKeyRequest(
            name="embed",
            permissions={
                "v1.chat": "access",
                "v1.models": "access",
                "v1.embeddings": "access",
            },
            allowed_endpoints=["/v1/embeddings", "/v1/models"],
            allowed_models=["keprix", "keprix-embed"],
        )
    )
    response = await client.post(
        "/v1/embeddings",
        headers={"Authorization": f"Bearer {created.secret}"},
        json={"model": "keprix-embed", "input": ["alpha", "beta"]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 2
    assert len(payload["data"][0]["embedding"]) == EMBEDDING_DIM


@pytest.mark.asyncio
async def test_developer_create_and_list_keys(client, key_store, monkeypatch):
    monkeypatch.setenv("KEPRIX_API_ADMIN_TOKEN", "admin")
    created = await client.post(
        "/api/developer/keys",
        headers={"Authorization": "Bearer admin"},
        json={"name": "dashboard-key"},
    )
    assert created.status_code == 200
    body = created.json()
    secret = body["secret"]
    assert secret.startswith("kp_")
    assert body.get("restrict_key") is True
    assert "/v1/chat/completions" in body.get("allowed_endpoints", [])

    listed = await client.get(
        "/api/developer/keys",
        headers={"Authorization": "Bearer admin"},
    )
    assert listed.status_code == 200
    assert any(key["name"] == "dashboard-key" for key in listed.json()["keys"])


@pytest.mark.asyncio
async def test_responses_api_shape(client, key_store, mock_agent_runtime):
    created = key_store.create(
        CreateApiKeyRequest(
            name="responses",
            permissions={
                "v1.chat": "access",
                "v1.models": "access",
                "v1.responses": "access",
            },
            allowed_endpoints=["/v1/responses", "/v1/models"],
            allowed_models=["keprix"],
        )
    )
    response = await client.post(
        "/v1/responses",
        headers={"Authorization": f"Bearer {created.secret}"},
        json={"model": "keprix", "input": "hello responses"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "response"
    assert payload["output_text"] == "Agent runtime response"
    assert payload["usage"]["total_tokens"] > 0


@pytest.mark.asyncio
async def test_developer_dashboard_payload(client, key_store, monkeypatch):
    monkeypatch.setenv("KEPRIX_API_ADMIN_TOKEN", "admin")
    response = await client.get(
        "/api/developer/dashboard",
        headers={"Authorization": "Bearer admin"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["openapi_url"] == "/openapi.json"
    assert "enabled_tools" in payload
    assert "sdk_snippets" in payload
    assert "webhooks" in payload
    assert "scope_catalog" in payload
    assert payload["scope_catalog"]["defaults"]["restrict_key"] is True


@pytest.mark.asyncio
async def test_developer_dashboard_allows_session_token(client, key_store, monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_API_ADMIN_TOKEN", "")
    monkeypatch.setattr(
        "keprix.public_api.auth.auth_manager.validate_token",
        lambda token: {"id": "user-1", "role": "admin"} if token == "session-token" else None,
    )
    monkeypatch.setattr("keprix.keys.developer_identity.verify_developer_identity", lambda: False)

    response = await client.get(
        "/api/developer/dashboard",
        headers={"Authorization": "Bearer session-token"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_developer_dashboard_forbidden_detail_is_object(client, key_store, monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_API_ADMIN_TOKEN", "")
    monkeypatch.setattr("keprix.public_api.auth.auth_manager.validate_token", lambda _token: None)
    monkeypatch.setattr("keprix.keys.local_access.verify_developer_identity", lambda: False)

    response = await client.get("/api/developer/dashboard")
    assert response.status_code == 403
    payload = response.json()
    assert payload["detail"]["error"] == "Developer access required"


@pytest.mark.asyncio
async def test_webhook_dispatch_on_chat_completion(client, key_store, mock_agent_runtime, tmp_path, monkeypatch):
    from keprix.public_api.webhooks import WebhookCreateRequest, WebhookStore

    hook_store = WebhookStore(path=tmp_path / "webhooks.json")
    monkeypatch.setattr("keprix.public_api.webhooks.get_webhook_store", lambda: hook_store)

    deliveries: list[dict] = []

    async def capture_dispatch(workspace_id, event, payload):
        deliveries.append({"workspace_id": workspace_id, "event": event, "payload": payload})
        return [{"ok": True}]

    monkeypatch.setattr("keprix.public_api.openai_compat.dispatch_webhook_event", capture_dispatch)

    hook_store.create(
        WebhookCreateRequest(url="https://example.test/hook", events=["chat.completed"]),
    )
    created = key_store.create(CreateApiKeyRequest(name="hook"))
    response = await client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {created.secret}"},
        json={"model": "keprix", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert response.status_code == 200
    for _ in range(20):
        if deliveries:
            break
        await asyncio.sleep(0.02)
    assert deliveries
    assert deliveries[0]["event"] == "chat.completed"
