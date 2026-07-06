"""Admin LLM usage and budget alert tests (Prompt 148)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.security.rate_limiter import reset_rate_limits
from keprix.usage.budget import get_llm_usage_budget_store
from keprix.usage.budget_alerts import check_workspace_budget_alert
from keprix.usage.schemas import LlmUsageRecord
from keprix.usage.store import LlmUsageStore, get_llm_usage_store


@pytest.fixture
def admin_usage_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("KEPRIX_MULTI_USER", "true")
    monkeypatch.setenv("KEPRIX_LLM_USAGE_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_LLM_USAGE_SQLITE_FALLBACK", "true")
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.observability.metrics.get_session_factory", lambda: None)
    reset_rate_limits()

    auth = AuthManager(str(tmp_path / "auth.json"))
    auth.create_user("alice", "alice-pass", role="user")
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)

    store = LlmUsageStore(sqlite_path=tmp_path / "llm_usage.db")
    monkeypatch.setattr("keprix.usage.store._store", store)
    monkeypatch.setattr("keprix.usage.budget._budget_store", None)

    now = datetime.now(timezone.utc)
    for index in range(6):
        store.insert_sync(
            LlmUsageRecord(
                recorded_at=now - timedelta(hours=index),
                user_id="alice-id",
                channel="web_ui",
                provider="anthropic",
                model="claude-sonnet-4-6",
                input_tokens=2000,
                output_tokens=400,
                total_tokens=2400,
                cost_usd=Decimal("0.05"),
                cost_status="estimated",
            )
        )

    app = create_app()
    admin_client = TestClient(app)
    login = admin_client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    admin_client.headers.update({"Authorization": f"Bearer {login.json()['token']}"})

    user_login = admin_client.post("/api/auth/login", json={"username": "alice", "password": "alice-pass"})
    user_client = TestClient(app)
    user_client.headers.update({"Authorization": f"Bearer {user_login.json()['token']}"})
    return admin_client, user_client, store, tmp_path


def test_admin_can_set_budget_non_admin_forbidden(admin_usage_client):
    admin, user, _store, _tmp = admin_usage_client
    put = admin.put("/api/usage/budget", json={"monthly_budget_usd": 10.0, "alert_threshold_percent": 80})
    assert put.status_code == 200
    denied = user.put("/api/usage/budget", json={"monthly_budget_usd": 5.0, "alert_threshold_percent": 80})
    assert denied.status_code == 403


def test_dashboard_stats_include_llm_spend(admin_usage_client):
    admin, _user, _store, _tmp = admin_usage_client
    response = admin.get("/api/stats/llm/summary?days=30")
    assert response.status_code == 200
    body = response.json()
    assert body["llmSpend30d"] > 0
    assert body["llmTokens30d"] > 0
    assert body["llmRequestCount30d"] >= 6


def test_budget_alert_creates_notification_once(admin_usage_client, monkeypatch):
    admin, _user, store, tmp_path = admin_usage_client
    budget_store = get_llm_usage_budget_store()
    monkeypatch.setattr("keprix.usage.budget._budget_store", budget_store)

    put = admin.put("/api/usage/budget", json={"monthly_budget_usd": 0.10, "alert_threshold_percent": 50})
    assert put.status_code == 200

    import asyncio

    sent_first = asyncio.run(check_workspace_budget_alert("default"))
    assert sent_first is True

    from keprix.backend.notifications.store import get_notification_store

    notifications = get_notification_store().list_notifications("default")
    assert any(row.get("notification_type") == "llm_budget_alert" for row in notifications)

    sent_second = asyncio.run(check_workspace_budget_alert("default"))
    assert sent_second is False

    notifications_after = get_notification_store().list_notifications("default")
    alert_count = sum(1 for row in notifications_after if row.get("notification_type") == "llm_budget_alert")
    assert alert_count == 1
