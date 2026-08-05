"""Tests for ops/spend_tracker.py."""

from __future__ import annotations

import pytest

from keprix.providers.ops.spend_tracker import SpendRecord, SpendTracker, estimate_cost


def test_estimate_cost_anthropic():
    cost = estimate_cost("anthropic", prompt_tokens=1000, completion_tokens=500)
    assert cost > 0


def test_estimate_cost_free_provider():
    cost = estimate_cost("ollama", prompt_tokens=10_000, completion_tokens=5_000)
    assert cost == 0.0


def test_estimate_cost_unknown_provider():
    cost = estimate_cost("unknown_provider", prompt_tokens=1000, completion_tokens=1000)
    assert cost > 0  # falls back to default pricing


@pytest.mark.asyncio
async def test_record_and_total_spend():
    tracker = SpendTracker()
    rec = SpendRecord(
        tenant_id="acme",
        provider="openai",
        prompt_tokens=500,
        completion_tokens=200,
        estimated_cost_usd=0.005,
    )
    await tracker.record(rec)
    total = await tracker.total_spend("acme")
    assert abs(total - 0.005) < 0.0001


@pytest.mark.asyncio
async def test_within_budget_true():
    tracker = SpendTracker()
    await tracker.record(SpendRecord(
        tenant_id="t1", provider="openai",
        prompt_tokens=100, completion_tokens=50, estimated_cost_usd=0.001
    ))
    assert await tracker.within_budget("t1", budget_usd=10.0)


@pytest.mark.asyncio
async def test_within_budget_false():
    tracker = SpendTracker()
    await tracker.record(SpendRecord(
        tenant_id="t1", provider="openai",
        prompt_tokens=100, completion_tokens=50, estimated_cost_usd=49.99
    ))
    assert not await tracker.within_budget("t1", budget_usd=10.0)


@pytest.mark.asyncio
async def test_record_call_auto_estimates_cost():
    tracker = SpendTracker()
    rec = await tracker.record_call("t1", "anthropic", 1000, 500)
    assert rec.estimated_cost_usd > 0
    total = await tracker.total_spend("t1")
    assert total == rec.estimated_cost_usd


@pytest.mark.asyncio
async def test_summary_structure():
    tracker = SpendTracker()
    await tracker.record_call("t1", "openai", 500, 200)
    await tracker.record_call("t1", "anthropic", 300, 100)
    s = await tracker.summary("t1")
    assert s["calls"] == 2
    assert "openai" in s["by_provider"]
    assert "anthropic" in s["by_provider"]


@pytest.mark.asyncio
async def test_empty_tenant_total_is_zero():
    tracker = SpendTracker()
    assert await tracker.total_spend("nobody") == 0.0


@pytest.mark.asyncio
async def test_all_tenants():
    tracker = SpendTracker()
    await tracker.record_call("a", "openai", 100, 50)
    await tracker.record_call("b", "groq", 100, 50)
    tenants = await tracker.all_tenants()
    assert set(tenants) == {"a", "b"}
