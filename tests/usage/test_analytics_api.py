"""API tests for LLM usage analytics (Prompt 146)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.security.rate_limiter import reset_rate_limits
from keprix.usage.schemas import LlmUsageRecord
from keprix.usage.store import LlmUsageStore, get_llm_usage_store


@pytest.fixture
def usage_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("KEPRIX_MULTI_USER", "true")
    monkeypatch.setenv("KEPRIX_LLM_USAGE_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_LLM_USAGE_SQLITE_FALLBACK", "true")
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.observability.metrics.get_session_factory", lambda: None)
    reset_rate_limits()

    auth = AuthManager(str(tmp_path / "auth.json"))
    alice = auth.create_user("alice", "alice-pass", role="user")
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)

    store = LlmUsageStore(sqlite_path=tmp_path / "llm_usage.db")
    monkeypatch.setattr("keprix.usage.store._store", store)
    monkeypatch.setattr("keprix.usage.budget._budget_store", None)

    _seed_usage(store, alice_id=alice["id"])

    app = create_app()
    admin_client = TestClient(app)
    login = admin_client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    admin_client.headers.update({"Authorization": f"Bearer {login.json()['token']}"})

    user_login = admin_client.post("/api/auth/login", json={"username": "alice", "password": "alice-pass"})
    user_client = TestClient(app)
    user_client.headers.update({"Authorization": f"Bearer {user_login.json()['token']}"})
    return admin_client, user_client, store, alice["id"]


def _seed_usage(store: LlmUsageStore, *, alice_id: str) -> None:
    now = datetime.now(timezone.utc)
    models = ["claude-sonnet-4-6", "gpt-4.1-mini", "claude-sonnet-4-6"]
    users = [alice_id, "bob-id"]
    for index in range(10):
        day_offset = index % 3
        store.insert_sync(
            LlmUsageRecord(
                recorded_at=now - timedelta(days=day_offset, hours=index),
                user_id=users[index % 2],
                channel="web_ui" if index % 2 == 0 else "api",
                provider="anthropic" if "claude" in models[index % 3] else "openai",
                model=models[index % 3],
                input_tokens=1000 + index,
                output_tokens=200 + index,
                total_tokens=1200 + (2 * index),
                cost_usd=0.01 * (index + 1),
                cost_status="estimated",
                cost_source="official_docs_snapshot",
            )
        )


def test_usage_summary(usage_client):
    admin, _user, _store, _alice_id = usage_client
    response = admin.get("/api/usage/summary?days=30")
    assert response.status_code == 200
    body = response.json()
    assert body["request_count"] == 10
    assert body["total_tokens"] > 0
    assert body["total_cost_usd"] > 0


def test_usage_timeseries_day_buckets(usage_client):
    admin, _user, _store, _alice_id = usage_client
    response = admin.get("/api/usage/timeseries?days=30&granularity=day")
    assert response.status_code == 200
    points = response.json()["points"]
    assert len(points) >= 1


def test_usage_breakdown_models_ordered_by_cost(usage_client):
    admin, _user, _store, _alice_id = usage_client
    response = admin.get("/api/usage/breakdown/models?days=30")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 2
    costs = [row["total_cost_usd"] for row in items]
    assert costs == sorted(costs, reverse=True)


def test_non_admin_forced_to_own_user_filter(usage_client):
    _admin, user, store, alice_id = usage_client
    store.insert_sync(
        LlmUsageRecord(
            user_id=alice_id,
            channel="web_ui",
            provider="openai",
            model="gpt-4.1-mini",
            input_tokens=50,
            output_tokens=10,
            total_tokens=60,
            cost_status="estimated",
            cost_source="none",
        )
    )
    denied = user.get("/api/usage/summary?days=30&user_id=bob-id")
    assert denied.status_code == 403
    allowed = user.get("/api/usage/summary?days=30")
    assert allowed.status_code == 200


def test_non_admin_can_list_own_events(usage_client):
    _admin, user, _store, alice_id = usage_client
    response = user.get("/api/usage/events?days=30&limit=10")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert all(item.get("user_id") in {alice_id, None} for item in body["items"])


def test_budget_set_and_alert(usage_client):
    admin, _user, _store, _alice_id = usage_client
    put = admin.put("/api/usage/budget", json={"monthly_budget_usd": 0.05, "alert_threshold_percent": 50})
    assert put.status_code == 200
    status = admin.get("/api/usage/budget")
    assert status.status_code == 200
    body = status.json()
    assert body["monthly_budget_usd"] == 0.05
    assert body["alert"] is True


def test_usage_export_csv(usage_client):
    admin, user, _store, _alice_id = usage_client
    response = admin.get("/api/usage/export?days=90")
    assert response.status_code == 200
    text = response.text
    assert "recorded_at,user_id,channel" in text.splitlines()[0]
    assert text.count("\n") >= 2

    scoped = user.get("/api/usage/export?days=90&format=csv")
    assert scoped.status_code == 200
    assert "recorded_at,user_id,channel" in scoped.text.splitlines()[0]

    as_json = user.get("/api/usage/export?days=90&format=json")
    assert as_json.status_code == 200
    payload = as_json.json()
    assert "items" in payload
    assert isinstance(payload["items"], list)


def test_usage_status_endpoint(usage_client):
    _admin, user, _store, _alice_id = usage_client
    response = user.get("/api/usage/status")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert "enable_hint" in body


def test_pricing_models_catalog(usage_client):
    admin, user, _store, _alice_id = usage_client
    for client in (admin, user):
        response = client.get("/api/usage/pricing/models")
        assert response.status_code == 200
        assert len(response.json()["models"]) >= 1
