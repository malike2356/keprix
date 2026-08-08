"""Tests for K04 Aiva analytics engine."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.aiva_analytics.cron_seed import ANALYTICS_CRON_JOBS
from keprix.aiva_analytics.metrics import (
    AIVA_AGENT_CALLS,
    AIVA_OUTREACH_SENT,
    record_agent_call,
    record_outreach_email_sent,
    record_outreach_reply,
    record_worker_escalation,
    record_worker_message,
)
from keprix.aiva_analytics.service import AnalyticsService, reset_analytics_service_for_tests
from keprix.aiva_analytics.store import reset_analytics_store_for_tests


@pytest.fixture()
def analytics(tmp_path: Path) -> AnalyticsService:
    store = reset_analytics_store_for_tests(tmp_path / "analytics.sqlite")
    return reset_analytics_service_for_tests(store)


def test_record_and_overview_isolation(analytics: AnalyticsService) -> None:
    record_agent_call(
        workspace_id="ws_a",
        worker_id="w1",
        model="m1",
        duration_seconds=1.5,
        prompt_tokens=100,
        completion_tokens=50,
        cost_usd=0.01,
        store=analytics.store,
    )
    record_agent_call(
        workspace_id="ws_b",
        worker_id="w2",
        model="m1",
        duration_seconds=2.0,
        prompt_tokens=200,
        completion_tokens=20,
        cost_usd=0.02,
        store=analytics.store,
    )
    a = analytics.overview("ws_a", days=30)
    b = analytics.overview("ws_b", days=30)
    assert a["agent"]["calls"] == 1
    assert a["agent"]["tokens"] == 150
    assert b["agent"]["calls"] == 1
    assert b["agent"]["tokens"] == 220
    assert a["agent"]["estimated_cost_usd"] == 0.01


def test_outreach_funnel(analytics: AnalyticsService) -> None:
    record_outreach_email_sent("ws_1", campaign_id="c1", store=analytics.store)
    record_outreach_email_sent("ws_1", campaign_id="c1", store=analytics.store)
    record_outreach_reply("ws_1", classification="interested", store=analytics.store)
    record_outreach_reply("ws_1", classification="booking_intent", store=analytics.store)
    out = analytics.outreach("ws_1", campaign_id="c1", days=30)
    assert out["funnel"]["emails_sent"] == 2
    assert out["funnel"]["replies"] == 2
    assert out["funnel"]["bookings"] == 1
    assert out["funnel"]["reply_rate"] == 1.0


def test_worker_and_usage_series(analytics: AnalyticsService) -> None:
    record_worker_message("ws_1", "worker_a", channel="carina", store=analytics.store)
    record_worker_escalation("ws_1", "worker_a", store=analytics.store)
    record_agent_call(
        workspace_id="ws_1",
        worker_id="worker_a",
        model="m",
        duration_seconds=0.5,
        prompt_tokens=10,
        completion_tokens=5,
        cost_usd=0.001,
        store=analytics.store,
    )
    worker = analytics.worker("ws_1", worker_id="worker_a", days=30)
    assert worker["messages"] == 1
    assert worker["escalations"] == 1
    assert worker["agent_calls"] == 1
    usage = analytics.usage("ws_1", days=30)
    assert usage["totals"]["agent_calls"] == 1
    assert usage["totals"]["tokens"] == 15
    assert len(usage["series"]) >= 1


def test_daily_aggregate(analytics: AnalyticsService) -> None:
    record_agent_call(
        workspace_id="ws_1",
        worker_id="w",
        model="m",
        duration_seconds=1.0,
        prompt_tokens=1,
        completion_tokens=1,
        store=analytics.store,
    )
    result = analytics.aggregate_daily(lookback_days=2)
    assert result["workspaces"] == 1
    assert result["rows_upserted"] >= 1
    daily = analytics.store.list_daily("ws_1")
    assert any(r["metric_name"] == AIVA_AGENT_CALLS for r in daily)


def test_cron_seed_spec() -> None:
    assert ANALYTICS_CRON_JOBS[0]["name"] == "aiva-analytics-daily-aggregate"
    assert ANALYTICS_CRON_JOBS[0]["schedule"] == "0 8 * * *"
    assert "analytics" in ANALYTICS_CRON_JOBS[0]["enabled_toolsets"]


def test_api_routes(analytics: AnalyticsService, tmp_path: Path) -> None:
    reset_analytics_service_for_tests(analytics.store)
    record_outreach_email_sent("ws_api", campaign_id="c", store=analytics.store)
    assert analytics.store.sum_metric("ws_api", AIVA_OUTREACH_SENT) == 1

    from keprix.aiva_analytics.routes import router

    app = FastAPI()
    app.include_router(router, prefix="/carina")
    client = TestClient(app)

    r = client.get("/carina/analytics/overview", headers={"X-Workspace-Id": "ws_api"})
    assert r.status_code == 200
    assert r.json()["outreach"]["emails_sent"] == 1

    r2 = client.get(
        "/carina/analytics/outreach",
        params={"campaign_id": "c"},
        headers={"X-Workspace-Id": "ws_api"},
    )
    assert r2.status_code == 200
    assert r2.json()["funnel"]["emails_sent"] == 1

    r3 = client.get("/carina/analytics/worker", headers={"X-Workspace-Id": "ws_api"})
    assert r3.status_code == 200

    r4 = client.get("/carina/analytics/usage", params={"days": 7}, headers={"X-Workspace-Id": "ws_api"})
    assert r4.status_code == 200
    assert r4.json()["workspace_id"] == "ws_api"

    bad = client.get("/carina/analytics/overview")
    assert bad.status_code == 400


def test_tools_register(analytics: AnalyticsService) -> None:
    reset_analytics_service_for_tests(analytics.store)
    import tools.analytics_tools as analytics_tools  # noqa: F401
    from tools.registry import registry

    assert registry.get_entry("analytics_overview") is not None
    assert registry.get_entry("analytics_aggregate_daily") is not None
    out = analytics_tools.analytics_overview({"workspace_id": "ws_t", "days": 7})
    assert "workspace_id" in out


def test_bridge_records_metrics(analytics: AnalyticsService, monkeypatch: pytest.MonkeyPatch) -> None:
    reset_analytics_service_for_tests(analytics.store)
    from keprix.agent import carina_bridge as bridge_mod

    called: dict[str, object] = {}

    def fake_record_agent_call(**kwargs):
        called.update(kwargs)

    def fake_record_worker_message(*args, **kwargs):
        called["worker_msg"] = True

    monkeypatch.setattr(
        "keprix.aiva_analytics.metrics.record_agent_call",
        fake_record_agent_call,
    )
    monkeypatch.setattr(
        "keprix.aiva_analytics.metrics.record_worker_message",
        fake_record_worker_message,
    )

    # Avoid real LLM usage recorder side effects
    class _Rec:
        def record_sync(self, **kwargs):
            called["usage_recorded"] = True
            return "id"

    monkeypatch.setattr(
        "keprix.usage.recorder.get_llm_usage_recorder",
        lambda: _Rec(),
    )

    bridge_mod._record_run_analytics(
        workspace_id="ws_bridge",
        worker_id="w1",
        model="test-model",
        duration_seconds=0.42,
        usage={"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
        error_type=None,
    )
    assert called.get("workspace_id") == "ws_bridge"
    assert called.get("prompt_tokens") == 11
    assert called.get("worker_msg") is True
