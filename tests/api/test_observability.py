"""Tests for Prompt 18: API surface and observability."""

from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.server import create_app
from keprix.config.constants import EDITION, PRODUCT_VERSION


@pytest.fixture(autouse=True)
def disable_database(monkeypatch):
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.observability.metrics.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.observability.request_log.get_session_factory", lambda: None)


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


@pytest.mark.asyncio
async def test_health_returns_ok_under_100ms(client):
    import time

    started = time.perf_counter()
    response = await client.get("/api/health")
    elapsed_ms = (time.perf_counter() - started) * 1000
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["version"] == PRODUCT_VERSION
    assert payload["edition"] == EDITION
    assert elapsed_ms < 100


@pytest.mark.asyncio
async def test_openapi_json_available(client):
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema.get("openapi", "").startswith("3.")
    paths = schema.get("paths", {})
    assert "/api/health" in paths
    assert "/v1/chat" in paths


@pytest.mark.asyncio
async def test_detailed_health_requires_admin(client, monkeypatch):
    monkeypatch.delenv("KEPRIX_API_ADMIN_TOKEN", raising=False)
    # Disable localhost developer bypass so missing admin token is rejected.
    monkeypatch.setattr("keprix.api.auth.effective_access_level", lambda: "standard")
    response = await client.get("/api/health/detailed")
    assert response.status_code in {401, 403}


@pytest.mark.asyncio
async def test_detailed_health_with_admin_token(client, monkeypatch):
    monkeypatch.setenv("KEPRIX_API_ADMIN_TOKEN", "test-admin-token")
    monkeypatch.setattr("keprix.api.auth.effective_access_level", lambda: "standard")

    class _FakeMonitor:
        async def _run_all_checks(self) -> None:
            return None

        def get_all(self) -> dict:
            return {}

    monkeypatch.setattr(
        "keprix.config.health_monitor.ConfigHealthMonitor",
        _FakeMonitor,
    )

    response = await client.get(
        "/api/health/detailed",
        headers={"Authorization": "Bearer test-admin-token"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "database" in payload
    assert "redis" in payload
    assert "uptime_seconds" in payload


@pytest.mark.asyncio
async def test_analytics_usage_requires_auth(client, monkeypatch):
    monkeypatch.setattr("keprix.api.auth.effective_access_level", lambda: "standard")
    response = await client.get("/api/analytics/usage")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_analytics_usage_with_token(client, monkeypatch):
    monkeypatch.setenv("KEPRIX_API_TOKEN", "test-api-token")
    monkeypatch.setattr("keprix.api.auth.effective_access_level", lambda: "standard")
    response = await client.get(
        "/api/analytics/usage",
        headers={"Authorization": "Bearer test-api-token"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "daily_tokens" in payload
    assert "daily_messages" in payload


@pytest.mark.asyncio
async def test_diagnostics_with_admin(client, monkeypatch):
    monkeypatch.setenv("KEPRIX_API_ADMIN_TOKEN", "admin-token")
    monkeypatch.setattr("keprix.api.auth.effective_access_level", lambda: "standard")
    response = await client.get(
        "/api/diagnostics",
        headers={"Authorization": "Bearer admin-token"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "checks" in payload
    assert isinstance(payload["checks"], list)
    assert payload["passed"] + payload["failed"] == len(payload["checks"])


@pytest.mark.asyncio
async def test_public_chat_with_api_token(client, monkeypatch):
    from keprix.public_api.agent_runtime import AgentChatResult

    async def _fake_run(**_kwargs):
        return AgentChatResult(
            final_response="hello from agent",
            session_id="sess-abc",
            prompt_tokens=2,
            completion_tokens=3,
            total_tokens=5,
        )

    monkeypatch.setattr("keprix.api.public_v1_routes.run_agent_chat_completion", _fake_run)
    monkeypatch.setenv("KEPRIX_API_TOKEN", "chat-token")
    monkeypatch.setattr("keprix.api.auth.effective_access_level", lambda: "standard")
    response = await client.post(
        "/v1/chat",
        headers={"Authorization": "Bearer chat-token"},
        json={"message": "hello keprix"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"]
    assert payload["response"] == "hello from agent"
    assert payload["tokens_used"] >= 1


@pytest.mark.asyncio
async def test_error_handler_json_shape(client, monkeypatch):
    monkeypatch.setattr("keprix.api.auth.effective_access_level", lambda: "standard")
    response = await client.get("/api/analytics/usage")
    assert response.status_code == 401
    payload = response.json()
    assert "error" in payload
    assert "code" in payload


def test_trajectory_exporter_reads_session_file(tmp_path, monkeypatch):
    logs = tmp_path / "logs"
    logs.mkdir()
    session_file = logs / "session_20260705_abcd1234.json"
    session_file.write_text(
        json.dumps(
            {
                "conversations": [{"role": "user", "content": "hi"}],
                "model": "test-model",
                "completed": True,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "keprix.observability.trajectory_exporter._logs_dir",
        lambda: logs,
    )
    from keprix.observability.trajectory_exporter import load_trajectory, summarize_trajectory

    data = load_trajectory("abcd1234")
    assert data is not None
    assert data["model"] == "test-model"
    summary = summarize_trajectory("abcd1234")
    assert summary["found"] is True


@pytest.mark.asyncio
async def test_admin_trajectory_routes(client, monkeypatch):
    monkeypatch.setenv("KEPRIX_API_ADMIN_TOKEN", "admin-token")
    missing = await client.get(
        "/api/admin/sessions/missing-id/trajectory",
        headers={"Authorization": "Bearer admin-token"},
    )
    assert missing.status_code == 404

    summary = await client.get(
        "/api/admin/sessions/abcd1234/trajectory/summary",
        headers={"Authorization": "Bearer admin-token"},
    )
    assert summary.status_code == 200
    assert summary.json()["found"] is False


@pytest.mark.asyncio
async def test_public_chat_stream_sse(client, monkeypatch):
    from keprix.public_api.agent_runtime import AgentChatResult

    async def _fake_run(**_kwargs):
        callback = _kwargs.get("stream_delta_callback")
        if callback:
            callback("hello ")
            callback("world")
        return AgentChatResult(
            final_response="hello world",
            session_id="sess-stream",
            prompt_tokens=1,
            completion_tokens=2,
            total_tokens=3,
        )

    monkeypatch.setattr("keprix.api.public_v1_routes.run_agent_chat_completion", _fake_run)
    monkeypatch.setenv("KEPRIX_API_TOKEN", "chat-token")
    async with client.stream(
        "POST",
        "/v1/chat/stream",
        headers={"Authorization": "Bearer chat-token"},
        json={"message": "stream please"},
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        body = ""
        async for chunk in response.aiter_text():
            body += chunk
    assert '"chunk": "hello "' in body or '"chunk":"hello "' in body
    assert '"done": true' in body.lower() or '"done":true' in body.lower()
