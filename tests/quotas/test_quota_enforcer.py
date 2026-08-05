"""Tests for quotas/quota_enforcer.py."""

from __future__ import annotations

import pytest

from keprix.quotas.quota_config import ProductQuota, QuotaConfig, ResourceType
from keprix.quotas.quota_enforcer import QuotaEnforcer
from keprix.quotas.quota_store import QuotaStore


def _make_enforcer(
    product_id: str = "aiva",
    tokens_in_limit: int = 1_000_000,
    tool_calls_limit: int = 1_000,
    concurrent_limit: int = 5,
    on_exhaustion: dict | None = None,
    burst_allowance: float = 0.0,
):
    config = QuotaConfig()
    config.register(ProductQuota(
        product_id=product_id,
        limits={
            ResourceType.LLM_TOKENS_IN: tokens_in_limit,
            ResourceType.LLM_TOKENS_OUT: tokens_in_limit,
            ResourceType.TOOL_CALLS: tool_calls_limit,
            ResourceType.CONCURRENT_SESSIONS: concurrent_limit,
        },
        on_exhaustion=on_exhaustion or {
            ResourceType.LLM_TOKENS_IN: "block",
            ResourceType.TOOL_CALLS: "block",
        },
        burst_allowance=burst_allowance,
    ))
    store = QuotaStore(quota_config=config)
    return QuotaEnforcer(store=store, config=config), store


@pytest.mark.asyncio
async def test_check_allowed_when_quota_ok():
    enforcer, _ = _make_enforcer()
    result = await enforcer.check_before_llm_call("aiva")
    assert result.allowed
    assert result.reason == "ok"


@pytest.mark.asyncio
async def test_check_blocked_when_exhausted():
    enforcer, store = _make_enforcer(tokens_in_limit=100)
    await store.increment("aiva", ResourceType.LLM_TOKENS_IN, 100)
    result = await enforcer.check_before_llm_call("aiva")
    assert not result.allowed
    assert "exhausted" in result.reason
    assert result.action == "block"


@pytest.mark.asyncio
async def test_graceful_exhaustion_allows_but_injects_message():
    enforcer, store = _make_enforcer(
        tokens_in_limit=100,
        on_exhaustion={ResourceType.LLM_TOKENS_IN: "graceful"},
    )
    await store.increment("aiva", ResourceType.LLM_TOKENS_IN, 100)
    result = await enforcer.check_before_llm_call("aiva")
    assert result.allowed
    assert result.warning_message is not None
    assert "quota exhausted" in result.warning_message.lower()


@pytest.mark.asyncio
async def test_near_limit_warning_graceful():
    enforcer, store = _make_enforcer(
        tokens_in_limit=100,
        on_exhaustion={ResourceType.LLM_TOKENS_IN: "graceful"},
    )
    await store.increment("aiva", ResourceType.LLM_TOKENS_IN, 92)
    result = await enforcer.check_before_llm_call("aiva")
    assert result.allowed
    assert result.warning_message is not None
    assert "approaching" in result.warning_message.lower()


@pytest.mark.asyncio
async def test_no_warning_when_block_mode():
    enforcer, store = _make_enforcer(
        tokens_in_limit=100,
        on_exhaustion={ResourceType.LLM_TOKENS_IN: "block"},
    )
    await store.increment("aiva", ResourceType.LLM_TOKENS_IN, 92)
    result = await enforcer.check_before_llm_call("aiva")
    assert result.allowed
    assert result.warning_message is None  # no warning in block mode


@pytest.mark.asyncio
async def test_record_llm_usage_deducts_tokens():
    enforcer, store = _make_enforcer(tokens_in_limit=10_000)
    await enforcer.record_llm_usage("aiva", tokens_in=500, tokens_out=100)
    usage = await store.get_usage("aiva")
    assert usage.used(ResourceType.LLM_TOKENS_IN) == 500
    assert usage.used(ResourceType.LLM_TOKENS_OUT) == 100


@pytest.mark.asyncio
async def test_record_tool_call_increments():
    enforcer, store = _make_enforcer(tool_calls_limit=10)
    result = await enforcer.record_tool_call("aiva")
    assert result.allowed
    usage = await store.get_usage("aiva")
    assert usage.used(ResourceType.TOOL_CALLS) == 1


@pytest.mark.asyncio
async def test_record_tool_call_blocks_at_limit():
    enforcer, store = _make_enforcer(tool_calls_limit=1)
    await enforcer.record_tool_call("aiva")
    result = await enforcer.record_tool_call("aiva")
    assert not result.allowed
    assert "exhausted" in result.reason


@pytest.mark.asyncio
async def test_concurrent_sessions_check():
    enforcer, store = _make_enforcer(concurrent_limit=2)
    await store.set_concurrent_sessions("aiva", 2)
    result = await enforcer.check_concurrent_sessions("aiva")
    assert not result.allowed
    assert "exhausted" in result.reason


@pytest.mark.asyncio
async def test_concurrent_sessions_allowed_below_limit():
    enforcer, store = _make_enforcer(concurrent_limit=5)
    await store.set_concurrent_sessions("aiva", 3)
    result = await enforcer.check_concurrent_sessions("aiva")
    assert result.allowed
    assert result.remaining == 2


@pytest.mark.asyncio
async def test_burst_allowance_extends_limit():
    enforcer, store = _make_enforcer(tokens_in_limit=100, burst_allowance=0.10)
    await store.increment("aiva", ResourceType.LLM_TOKENS_IN, 105)
    result = await enforcer.check_before_llm_call("aiva")
    assert result.allowed   # 105 < 110 (100 + 10% burst)


@pytest.mark.asyncio
async def test_burst_allowance_blocks_over_hard_limit():
    enforcer, store = _make_enforcer(tokens_in_limit=100, burst_allowance=0.10)
    await store.increment("aiva", ResourceType.LLM_TOKENS_IN, 111)
    result = await enforcer.check_before_llm_call("aiva")
    assert not result.allowed   # 111 > 110 hard limit
