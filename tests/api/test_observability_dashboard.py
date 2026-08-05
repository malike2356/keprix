"""Observability dashboard API tests for data-ops P0."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.backend.evals.trace import AgentRunTrace
from keprix.backend.observability.agent_trace import capture_trace, get_trace_store
from keprix.security.rate_limiter import reset_rate_limits


@pytest.fixture
def obs_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("KEPRIX_MULTI_USER", "true")
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.observability.metrics.get_session_factory", lambda: None)
    reset_rate_limits()

    auth = AuthManager(str(tmp_path / "auth.json"))
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)

    get_trace_store().clear()
    app = create_app()
    client = TestClient(app)
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    client.headers.update({"Authorization": f"Bearer {login.json()['token']}"})
    return client


def test_observability_dashboard_runtime_health(obs_client):
    trace = AgentRunTrace.start(workspace_id="default", user_request="hello", agent_roles=["support"])
    trace.finish("success")
    capture_trace(trace)

    response = obs_client.get("/api/observability/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert "runtime" in body
    assert body["runtime"]["trace_volume"] >= 1
    assert "error_rate" in body["runtime"]
    assert "otel_configured" in body


def test_observability_traces_filter_and_spans(obs_client):
    ok = AgentRunTrace.start(workspace_id="default", user_request="ok path", agent_roles=["alpha"])
    ok.tool_calls.append({"name": "search"})
    ok.finish("success")
    capture_trace(ok)

    bad = AgentRunTrace.start(workspace_id="default", user_request="boom", agent_roles=["beta"])
    bad.errors.append("failed")
    bad.finish("error")
    capture_trace(bad)

    listed = obs_client.get("/api/observability/traces?status=error&limit=20")
    assert listed.status_code == 200
    traces = listed.json()["traces"]
    assert len(traces) >= 1
    assert all(t.get("status") == "error" for t in traces)

    agented = obs_client.get("/api/observability/traces?agent=alpha")
    assert agented.status_code == 200
    assert any(t.get("run_id") == ok.run_id for t in agented.json()["traces"])

    detail = obs_client.get(f"/api/observability/traces/{ok.run_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert "spans" in payload
    assert any(span.get("kind") == "tool" for span in payload["spans"])
