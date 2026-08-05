"""Tests for quotas/quota_store.py."""

from __future__ import annotations

import pytest

from keprix.quotas.quota_config import ProductQuota, QuotaConfig, ResourceType
from keprix.quotas.quota_store import QuotaStore, _period_bounds
from datetime import datetime, timezone


def _make_store(product_id: str = "aiva", limit: int = 1_000_000) -> QuotaStore:
    config = QuotaConfig()
    config.register(ProductQuota(
        product_id=product_id,
        period="monthly",
        limits={ResourceType.LLM_TOKENS_IN: limit},
    ))
    return QuotaStore(quota_config=config)


@pytest.mark.asyncio
async def test_increment_returns_updated_usage():
    store = _make_store()
    usage = await store.increment("aiva", ResourceType.LLM_TOKENS_IN, 500)
    assert usage.used(ResourceType.LLM_TOKENS_IN) == 500


@pytest.mark.asyncio
async def test_multiple_increments_accumulate():
    store = _make_store()
    await store.increment("aiva", ResourceType.LLM_TOKENS_IN, 300)
    await store.increment("aiva", ResourceType.LLM_TOKENS_IN, 200)
    usage = await store.get_usage("aiva")
    assert usage.used(ResourceType.LLM_TOKENS_IN) == 500


@pytest.mark.asyncio
async def test_different_products_isolated():
    config = QuotaConfig()
    config.register(ProductQuota("aiva", limits={ResourceType.LLM_TOKENS_IN: 1_000_000}))
    config.register(ProductQuota("abbis", limits={ResourceType.LLM_TOKENS_IN: 1_000_000}))
    store = QuotaStore(quota_config=config)

    await store.increment("aiva", ResourceType.LLM_TOKENS_IN, 1000)
    await store.increment("abbis", ResourceType.LLM_TOKENS_IN, 500)

    aiva = await store.get_usage("aiva")
    abbis = await store.get_usage("abbis")

    assert aiva.used(ResourceType.LLM_TOKENS_IN) == 1000
    assert abbis.used(ResourceType.LLM_TOKENS_IN) == 500


@pytest.mark.asyncio
async def test_reset_period_clears_usage():
    store = _make_store()
    await store.increment("aiva", ResourceType.LLM_TOKENS_IN, 5000)
    await store.reset_period("aiva")
    usage = await store.get_usage("aiva")
    assert usage.used(ResourceType.LLM_TOKENS_IN) == 0


@pytest.mark.asyncio
async def test_set_concurrent_sessions():
    store = _make_store()
    await store.set_concurrent_sessions("aiva", 4)
    usage = await store.get_usage("aiva")
    assert usage.used(ResourceType.CONCURRENT_SESSIONS) == 4


@pytest.mark.asyncio
async def test_increment_concurrent_sessions():
    store = _make_store()
    count = await store.increment_concurrent_sessions("aiva", 1)
    assert count == 1
    count = await store.increment_concurrent_sessions("aiva", 1)
    assert count == 2
    count = await store.increment_concurrent_sessions("aiva", -1)
    assert count == 1


@pytest.mark.asyncio
async def test_concurrent_sessions_floor_at_zero():
    store = _make_store()
    count = await store.increment_concurrent_sessions("aiva", -5)
    assert count == 0


@pytest.mark.asyncio
async def test_remaining_decreases_with_usage():
    store = _make_store(limit=1000)
    await store.increment("aiva", ResourceType.LLM_TOKENS_IN, 400)
    usage = await store.get_usage("aiva")
    assert usage.remaining(ResourceType.LLM_TOKENS_IN) == 600


@pytest.mark.asyncio
async def test_is_exhausted_false_initially():
    store = _make_store(limit=1000)
    usage = await store.get_usage("aiva")
    assert not usage.is_exhausted(ResourceType.LLM_TOKENS_IN)


@pytest.mark.asyncio
async def test_is_exhausted_true_at_limit():
    store = _make_store(limit=100)
    await store.increment("aiva", ResourceType.LLM_TOKENS_IN, 100)
    usage = await store.get_usage("aiva")
    assert usage.is_exhausted(ResourceType.LLM_TOKENS_IN)


def test_period_bounds_monthly():
    now = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    start, end = _period_bounds("monthly", now)
    assert start.day == 1
    assert start.month == 7
    assert end.month == 8
    assert end.day == 1


def test_period_bounds_daily():
    now = datetime(2026, 7, 15, 14, 30, 0, tzinfo=timezone.utc)
    start, end = _period_bounds("daily", now)
    assert start.hour == 0
    assert (end - start).days == 1


def test_period_bounds_hourly():
    now = datetime(2026, 7, 15, 14, 30, 0, tzinfo=timezone.utc)
    start, end = _period_bounds("hourly", now)
    assert start.minute == 0
    assert (end - start).seconds == 3600
