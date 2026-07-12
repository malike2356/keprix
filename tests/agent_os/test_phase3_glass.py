"""Prompt 270 Phase 3: glass dashboard, agent tokens, Memory Galaxy API."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user
from keprix.usage.filters import UsageQueryFilters
from keprix.usage.schemas import LlmUsageRecord
from keprix.usage.store import LlmUsageStore
from keprix.vault.capture import ensure_default_vault
from keprix.vault.config import get_configured_provider


@pytest.fixture
def keprix_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / ".keprix"
    home.mkdir()
    monkeypatch.setenv("KEPRIX_HOME", str(home))
    monkeypatch.setenv("KEPRIX_AGENT_OS_ENABLED", "1")
    monkeypatch.delenv("KEPRIX_VAULT_ROOT", raising=False)
    monkeypatch.setenv("KEPRIX_LLM_USAGE_SQLITE_FALLBACK", "1")
    return home


@pytest.mark.asyncio
async def test_agent_usage_breakdown_from_metadata(keprix_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = LlmUsageStore(sqlite_path=keprix_home / "llm_usage.db")
    monkeypatch.setattr("keprix.usage.store.get_llm_usage_store", lambda: store)
    monkeypatch.setattr("keprix.usage.analytics.get_llm_usage_store", lambda: store)

    store.insert_sync(
        LlmUsageRecord(
            channel="web_ui",
            provider="deepseek",
            model="deepseek-chat",
            total_tokens=1000,
            cost_usd=__import__("decimal").Decimal("0.02"),
            cost_status="estimated",
            cost_source="test",
            metadata={"agent_id": "content-series"},
        )
    )
    store.insert_sync(
        LlmUsageRecord(
            channel="cli",
            provider="deepseek",
            model="deepseek-chat",
            total_tokens=200,
            cost_usd=__import__("decimal").Decimal("0.01"),
            cost_status="estimated",
            cost_source="test",
            metadata={"app_name": "crm-import"},
        )
    )

    from keprix.usage.analytics import LlmUsageAnalytics

    rows = await LlmUsageAnalytics().breakdown(UsageQueryFilters.from_params(days=30), dimension="agent")
    keys = {row["key"] for row in rows}
    assert "content-series" in keys
    assert "crm-import" in keys


@pytest.mark.asyncio
async def test_glass_dashboard_payload(keprix_home: Path) -> None:
    from keprix.agent_os.glass_dashboard import build_glass_dashboard
    from keprix.agent_os.workflow_kanban import enqueue_workflow_steps

    ensure_default_vault()
    provider = get_configured_provider()
    await provider.write_file("wiki/a.md", "Links [[b]]")
    await provider.write_file("wiki/b.md", "Target")
    enqueue_workflow_steps(
        workflow="content-series",
        title="Glass demo",
        steps=[{"id": "review", "title": "Review", "status": "todo"}],
        push_kanban=False,
    )

    payload = await build_glass_dashboard(days=7)
    assert payload["ok"] is True
    assert payload["memory"]["graph_nodes"] >= 2
    assert payload["tasks"]["board_count"] >= 1
    assert "memory_galaxy" in payload["links"]


def test_glass_and_usage_agent_routes(keprix_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = LlmUsageStore(sqlite_path=keprix_home / "llm_usage.db")
    monkeypatch.setattr("keprix.usage.store.get_llm_usage_store", lambda: store)
    monkeypatch.setattr("keprix.usage.analytics.get_llm_usage_store", lambda: store)
    store.insert_sync(
        LlmUsageRecord(
            channel="agent",
            provider="x",
            model="y",
            total_tokens=10,
            metadata={"agent": "hello-agent"},
            cost_status="unknown",
            cost_source="none",
        )
    )

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "admin"}
    client = TestClient(app)

    glass = client.get("/api/agent-os/glass")
    assert glass.status_code == 200
    body = glass.json()
    assert body["ok"] is True
    assert "agents" in body and "memory" in body and "tokens" in body

    breakdown = client.get("/api/usage/breakdown/agent?days=30")
    assert breakdown.status_code == 200
    assert any(item["key"] == "hello-agent" for item in breakdown.json()["items"])


@pytest.mark.asyncio
async def test_vault_graph_for_galaxy(keprix_home: Path) -> None:
    ensure_default_vault()
    provider = get_configured_provider()
    await provider.write_file("notes/alpha.md", "See [[beta]]")
    await provider.write_file("notes/beta.md", "Back")
    graph = await provider.get_graph()
    assert len(graph["nodes"]) >= 2
    assert any(edge["source"].endswith("alpha.md") for edge in graph["edges"])
