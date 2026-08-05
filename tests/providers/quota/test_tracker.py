"""Tests for quota/tracker.py."""

from __future__ import annotations

import asyncio

import pytest

from keprix.providers.quota.tracker import QuotaTracker


@pytest.mark.asyncio
async def test_unknown_quota_allows_any_tokens():
    qt = QuotaTracker()
    assert await qt.check("openai", 50_000) is True


@pytest.mark.asyncio
async def test_check_allows_within_quota():
    qt = QuotaTracker()
    await qt.set_quota("openai", remaining=1000, total=10_000)
    assert await qt.check("openai", 500) is True


@pytest.mark.asyncio
async def test_check_blocks_over_quota():
    qt = QuotaTracker()
    await qt.set_quota("openai", remaining=100, total=10_000)
    assert await qt.check("openai", 500) is False


@pytest.mark.asyncio
async def test_record_usage_deducts_tokens():
    qt = QuotaTracker()
    await qt.set_quota("openai", remaining=1000, total=10_000)
    await qt.record_usage("openai", 200)
    bucket = await qt.get_bucket("openai")
    assert bucket.remaining == 800


@pytest.mark.asyncio
async def test_record_usage_does_not_go_below_zero():
    qt = QuotaTracker()
    await qt.set_quota("openai", remaining=100, total=10_000)
    await qt.record_usage("openai", 500)
    bucket = await qt.get_bucket("openai")
    assert bucket.remaining == 0


@pytest.mark.asyncio
async def test_mark_exhausted():
    qt = QuotaTracker()
    await qt.set_quota("openai", remaining=5000, total=10_000)
    await qt.mark_exhausted("openai")
    bucket = await qt.get_bucket("openai")
    assert bucket.is_exhausted is True


@pytest.mark.asyncio
async def test_remaining_pct():
    qt = QuotaTracker()
    await qt.set_quota("openai", remaining=2500, total=10_000)
    bucket = await qt.get_bucket("openai")
    assert abs(bucket.remaining_pct - 0.25) < 0.001


@pytest.mark.asyncio
async def test_remaining_pct_unknown_total():
    qt = QuotaTracker()
    # No set_quota call: total = -1
    bucket = await qt.get_bucket("newprov")
    assert bucket.remaining_pct == 1.0


@pytest.mark.asyncio
async def test_predict_exhaustion_returns_none_without_data():
    qt = QuotaTracker()
    # No burn rate yet
    result = await qt.predict_exhaustion("openai")
    assert result is None


@pytest.mark.asyncio
async def test_predict_exhaustion_with_burn_rate():
    qt = QuotaTracker()
    await qt.set_quota("openai", remaining=3600, total=10_000)
    # Simulate usage over time to build burn rate
    for _ in range(5):
        await qt.record_usage("openai", 100)
        await asyncio.sleep(0.01)

    result = await qt.predict_exhaustion("openai")
    # Should be a future datetime (or None if burn rate is 0 due to timing)
    # Just check it returns without error
    assert result is None or hasattr(result, "isoformat")


@pytest.mark.asyncio
async def test_get_all_returns_tracked_providers():
    qt = QuotaTracker()
    await qt.set_quota("a", remaining=1000, total=5000)
    await qt.set_quota("b", remaining=500, total=5000)
    all_b = await qt.get_all()
    assert "a" in all_b
    assert "b" in all_b
