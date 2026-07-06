"""Tests for LLM usage store (Prompt 145)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from keprix.usage.schemas import LlmUsageRecord
from keprix.usage.store import LlmUsageStore


@pytest.fixture
def usage_store(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_LLM_USAGE_SQLITE_FALLBACK", "true")
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    store = LlmUsageStore(sqlite_path=tmp_path / "llm_usage.db")
    return store


def test_insert_and_count(usage_store):
    record = LlmUsageRecord(
        channel="web_ui",
        provider="openai",
        model="gpt-4.1-mini",
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        cost_status="estimated",
        cost_source="official_docs_snapshot",
    )
    usage_store.insert_sync(record)
    assert usage_store.count_sync() == 1


def test_list_since_and_prune(usage_store):
    old = LlmUsageRecord(
        channel="api",
        provider="openai",
        model="gpt-4.1-mini",
        total_tokens=10,
        recorded_at=datetime.now(timezone.utc) - timedelta(days=120),
    )
    recent = LlmUsageRecord(
        channel="api",
        provider="openai",
        model="gpt-4.1-mini",
        total_tokens=20,
    )
    usage_store.insert_sync(old)
    usage_store.insert_sync(recent)
    assert usage_store.count_sync() == 2
    pruned = usage_store.prune_sync(retention_days=90)
    assert pruned == 1
    assert usage_store.count_sync() == 1
