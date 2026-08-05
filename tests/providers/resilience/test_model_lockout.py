"""Tests for resilience/model_lockout.py."""

from __future__ import annotations

import asyncio

import pytest

from keprix.providers.resilience.model_lockout import ModelLockout


@pytest.mark.asyncio
async def test_not_locked_by_default():
    lo = ModelLockout()
    assert not await lo.is_locked("openai")


@pytest.mark.asyncio
async def test_first_failure_locks_with_base_delay():
    lo = ModelLockout()
    delay = await lo.record_failure("openai", "timeout")
    assert delay >= 5.0
    assert await lo.is_locked("openai")


@pytest.mark.asyncio
async def test_exponential_backoff_increases():
    lo = ModelLockout()
    d1 = await lo.record_failure("p")
    await lo.record_success("p")  # reset
    d2 = await lo.record_failure("p")
    # After a reset the delay starts from base again
    assert d1 >= 5.0 and d2 >= 5.0


@pytest.mark.asyncio
async def test_consecutive_failures_increase_delay():
    lo = ModelLockout()
    d1 = await lo.record_failure("p")
    d2 = await lo.record_failure("p")
    d3 = await lo.record_failure("p")
    assert d3 >= d2 >= d1


@pytest.mark.asyncio
async def test_delay_capped_at_max():
    lo = ModelLockout()
    for _ in range(20):
        await lo.record_failure("p")
    state = lo._states["p"]
    assert state.next_delay() <= 300.0


@pytest.mark.asyncio
async def test_success_clears_lockout():
    lo = ModelLockout()
    await lo.record_failure("openai")
    assert await lo.is_locked("openai")
    await lo.record_success("openai")
    assert not await lo.is_locked("openai")


@pytest.mark.asyncio
async def test_release_lifts_lockout():
    lo = ModelLockout()
    await lo.record_failure("openai")
    await lo.release("openai")
    assert not await lo.is_locked("openai")


@pytest.mark.asyncio
async def test_snapshot_contains_provider():
    lo = ModelLockout()
    await lo.record_failure("openai", "err")
    snap = await lo.snapshot()
    assert "openai" in snap
    assert snap["openai"]["failures"] == 1
    assert snap["openai"]["is_locked"] is True


@pytest.mark.asyncio
async def test_different_providers_independent():
    lo = ModelLockout()
    await lo.record_failure("a")
    assert await lo.is_locked("a")
    assert not await lo.is_locked("b")
