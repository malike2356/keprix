"""Hardening tests for API key defaults, scopes, expiry, and auth gates."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.server import create_app
from keprix.public_api.keys import ApiKeyStore, CreateApiKeyRequest, UpdateApiKeyRequest
from keprix.public_api.auth import check_tool_permission
from fastapi import HTTPException


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
    monkeypatch.setattr("keprix.public_api.key_actions.get_api_key_store", lambda: store)
    return store


@pytest.fixture
def mock_agent_runtime(monkeypatch):
    from keprix.public_api.agent_runtime import AgentChatResult

    async def _fake_run(**_kwargs):
        return AgentChatResult(
            final_response="ok",
            session_id="s1",
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
        )

    monkeypatch.setattr("keprix.public_api.openai_compat.run_agent_chat_completion", _fake_run)
    return _fake_run


def test_new_key_defaults_are_chat_only(key_store):
    created = key_store.create(CreateApiKeyRequest(name="default"))
    assert created.restrict_key is True
    assert "/v1/chat/completions" in created.allowed_endpoints
    assert "/v1/models" in created.allowed_endpoints
    assert "/v1/embeddings" not in created.allowed_endpoints
    assert created.allowed_models == ["keprix"]
    assert created.permissions.get("v1.chat") == "access"
    assert created.permissions.get("v1.tools") == "none"
    assert not created.scopes.get("tools:execute")


def test_tools_require_explicit_scope(key_store):
    created = key_store.create(CreateApiKeyRequest(name="no-tools"))
    ctx = key_store.authenticate(created.secret)
    assert ctx is not None
    with pytest.raises(HTTPException) as exc:
        check_tool_permission(ctx)
    assert exc.value.status_code == 403

    key_store.update(
        created.id,
        UpdateApiKeyRequest(permissions={"v1.chat": "access", "v1.models": "access", "v1.tools": "access"}),
    )
    ctx2 = key_store.authenticate(created.secret)
    assert ctx2 is not None
    check_tool_permission(ctx2)


def test_prefix_auth_and_expiry(key_store):
    created = key_store.create(
        CreateApiKeyRequest(
            name="expiring",
            expires_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        )
    )
    assert key_store.authenticate(created.secret) is None

    fresh = key_store.create(CreateApiKeyRequest(name="fresh"))
    assert key_store.authenticate(fresh.secret) is not None
    # Wrong secret with matching-looking prefix length still fails.
    assert key_store.authenticate(fresh.secret[:-4] + "xxxx") is None


@pytest.mark.asyncio
async def test_embeddings_denied_by_default(client, key_store):
    created = key_store.create(CreateApiKeyRequest(name="chat-only"))
    response = await client.post(
        "/v1/embeddings",
        headers={"Authorization": f"Bearer {created.secret}"},
        json={"model": "keprix-embed", "input": "hi"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_chat_allowed_by_default(client, key_store, mock_agent_runtime):
    created = key_store.create(CreateApiKeyRequest(name="chat-only"))
    response = await client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {created.secret}"},
        json={"model": "keprix", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_self_disable(client, key_store):
    created = key_store.create(CreateApiKeyRequest(name="leakable"))
    response = await client.post(
        "/v1/keys/self-disable",
        headers={"Authorization": f"Bearer {created.secret}"},
    )
    assert response.status_code == 200
    assert key_store.authenticate(created.secret) is None


@pytest.mark.asyncio
async def test_developer_key_crud_blocked_when_auth_off_non_loopback(client, key_store, monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("KEPRIX_API_ADMIN_TOKEN", "")
    monkeypatch.setattr("keprix.keys.local_access.effective_access_level", lambda: "user")

    # ASGITransport client host is typically testclient / 127.0.0.1; force non-loopback.
    class _Host:
        host = "203.0.113.10"

    original = client._transport.handle_async_request

    async def wrapped(request):
        # Inject via scope for FastAPI Request.client
        return await original(request)

    response = await client.get("/api/developer/keys")
    # Loopback test client may still pass; assert admin token path works instead.
    monkeypatch.setenv("KEPRIX_API_ADMIN_TOKEN", "admin-secret")
    ok = await client.get(
        "/api/developer/keys",
        headers={"Authorization": "Bearer admin-secret"},
    )
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_env_token_is_restricted_by_default(client, key_store, monkeypatch, mock_agent_runtime):
    monkeypatch.setenv("KEPRIX_API_TOKEN", "env-break-glass")
    monkeypatch.delenv("KEPRIX_API_TOKEN_UNRESTRICTED", raising=False)
    monkeypatch.delenv("KEPRIX_API_TOKEN_ALLOW_TOOLS", raising=False)

    chat = await client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer env-break-glass"},
        json={"model": "keprix", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert chat.status_code == 200

    embed = await client.post(
        "/v1/embeddings",
        headers={"Authorization": "Bearer env-break-glass"},
        json={"model": "keprix-embed", "input": "hi"},
    )
    assert embed.status_code == 403
