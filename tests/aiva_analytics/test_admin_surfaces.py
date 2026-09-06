from __future__ import annotations

from pathlib import Path

from keprix.aiva_analytics import metrics
from keprix.aiva_analytics.routes import _worker_index
from keprix.aiva_analytics.store import AnalyticsStore
from keprix.billing.wallet.store import AiCreditStore


def test_worker_index_aggregates_channels_and_usage(tmp_path: Path, monkeypatch) -> None:
    analytics = AnalyticsStore(tmp_path / "analytics.sqlite")
    metrics.record_worker_message("ws-1", "worker-1", channel="telegram", store=analytics)
    metrics.record_agent_call(
        workspace_id="ws-1",
        worker_id="worker-1",
        model="openai:gpt-4.1-mini",
        duration_seconds=1,
        prompt_tokens=10,
        completion_tokens=5,
        cost_usd=0.02,
        store=analytics,
    )
    monkeypatch.setattr("keprix.aiva_analytics.routes.get_analytics_store", lambda: analytics)

    rows = _worker_index(workspace_filter="ws-1")
    assert len(rows) == 1
    assert rows[0]["worker_id"] == "worker-1"
    assert rows[0]["channels"] == ["telegram"]
    assert rows[0]["tokens"] == 15
    assert rows[0]["cost_usd"] == 0.02


def test_credit_batch_marker_is_stable(tmp_path: Path) -> None:
    store = AiCreditStore(tmp_path / "wallet.db")
    marker = "bulk-grant:batch-1:user-1"
    assert store.has_ledger_marker("user-1", marker) is False
    store.append_entry(
        workspace_id="user-1",
        entry_type="grant",
        credits=10,
        metadata={"idempotency_key": marker},
    )
    assert store.has_ledger_marker("user-1", marker) is True
