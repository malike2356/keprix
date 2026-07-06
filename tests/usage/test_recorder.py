"""Tests for LLM usage recorder (Prompt 145)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.usage_pricing import CanonicalUsage, CostResult
from decimal import Decimal

from keprix.usage.recorder import LlmUsageRecorder, normalize_channel


@pytest.fixture
def recorder(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_LLM_USAGE_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_LLM_USAGE_SQLITE_FALLBACK", "true")
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.usage.store._store", None)
    return LlmUsageRecorder()


@pytest.mark.asyncio
async def test_record_persists_event(recorder, tmp_path):
    event_id = await recorder.record(
        usage=CanonicalUsage(input_tokens=100, output_tokens=40),
        provider="anthropic",
        model="claude-sonnet-4-6",
        channel="web_ui",
        user_id="user-1",
        session_id="sess-1",
    )
    assert event_id
    from keprix.usage.store import get_llm_usage_store

    assert get_llm_usage_store().count_sync() == 1


@pytest.mark.asyncio
async def test_disabled_skips_insert(recorder, monkeypatch):
    monkeypatch.setenv("KEPRIX_LLM_USAGE_ENABLED", "false")
    event_id = await recorder.record(
        usage=CanonicalUsage(input_tokens=10, output_tokens=5),
        provider="openai",
        model="gpt-4.1-mini",
        channel="web_ui",
    )
    assert event_id == ""
    from keprix.usage.store import get_llm_usage_store

    assert get_llm_usage_store().count_sync() == 0


@pytest.mark.asyncio
async def test_store_failure_does_not_raise(recorder, monkeypatch):
    mock_store = MagicMock()
    mock_store.insert_async = AsyncMock(side_effect=RuntimeError("db down"))
    monkeypatch.setattr("keprix.usage.recorder.get_llm_usage_store", lambda: mock_store)
    event_id = await recorder.record(
        usage=CanonicalUsage(input_tokens=1, output_tokens=1),
        provider="openai",
        model="gpt-4.1-mini",
        channel="web_ui",
    )
    assert event_id == ""


def test_normalize_channel_aliases():
    assert normalize_channel("web") == "web_ui"
    assert normalize_channel("TELEGRAM") == "telegram"
    assert normalize_channel("") == "agent"


@pytest.mark.asyncio
async def test_cost_result_passthrough(recorder, monkeypatch):
    captured = {}

    async def _capture_insert(record):
        captured["cost_status"] = record.cost_status
        return record.id

    mock_store = MagicMock()
    mock_store.insert_async = _capture_insert
    monkeypatch.setattr("keprix.usage.recorder.get_llm_usage_store", lambda: mock_store)

    cost = CostResult(
        amount_usd=Decimal("0.05"),
        status="estimated",
        source="official_docs_snapshot",
        label="test",
    )
    await recorder.record(
        usage=CanonicalUsage(input_tokens=1000, output_tokens=200),
        provider="anthropic",
        model="claude-sonnet-4-6",
        channel="agent",
        cost_result=cost,
    )
    assert captured["cost_status"] == "estimated"
