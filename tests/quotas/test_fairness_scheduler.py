"""Tests for quotas/fairness_scheduler.py."""

from __future__ import annotations

import asyncio
import pytest

from keprix.quotas.fairness_scheduler import FairnessScheduler, SchedulerToken


@pytest.fixture
def scheduler():
    return FairnessScheduler(max_slots=3, max_per_product=2)


@pytest.mark.asyncio
async def test_acquire_slot_returns_token(scheduler):
    token = await scheduler.acquire_slot("aiva")
    assert isinstance(token, SchedulerToken)
    assert token.product_id == "aiva"
    await scheduler.release_slot(token)


@pytest.mark.asyncio
async def test_fast_path_when_slots_available(scheduler):
    token = await scheduler.acquire_slot("aiva")
    stats = scheduler.stats()
    assert stats["active_slots"] == 1
    await scheduler.release_slot(token)


@pytest.mark.asyncio
async def test_release_decrements_active_slots(scheduler):
    token = await scheduler.acquire_slot("aiva")
    await scheduler.release_slot(token)
    assert scheduler.stats()["active_slots"] == 0


@pytest.mark.asyncio
async def test_multiple_products_share_slots(scheduler):
    t1 = await scheduler.acquire_slot("aiva")
    t2 = await scheduler.acquire_slot("abbis")
    assert scheduler.stats()["active_slots"] == 2
    await scheduler.release_slot(t1)
    await scheduler.release_slot(t2)


@pytest.mark.asyncio
async def test_per_product_cap():
    sched = FairnessScheduler(max_slots=10, max_per_product=1)
    t1 = await sched.acquire_slot("aiva")
    # Second acquire for same product should queue (not instant)
    # We don't wait for it; just check stats
    release_done = asyncio.Event()

    async def release_soon():
        await asyncio.sleep(0.01)
        await sched.release_slot(t1)
        release_done.set()

    task = asyncio.create_task(release_soon())
    t2 = await sched.acquire_slot("aiva")  # should wait until t1 released
    release_done_result = release_done.is_set()
    await sched.release_slot(t2)
    await task
    assert release_done_result


@pytest.mark.asyncio
async def test_global_cap_queues_requests():
    sched = FairnessScheduler(max_slots=2, max_per_product=5)
    t1 = await sched.acquire_slot("aiva")
    t2 = await sched.acquire_slot("aiva")
    assert sched.stats()["active_slots"] == 2

    async def release_after_delay():
        await asyncio.sleep(0.01)
        await sched.release_slot(t1)

    task = asyncio.create_task(release_after_delay())
    t3 = await sched.acquire_slot("abbis")  # must wait for a slot
    await sched.release_slot(t2)
    await sched.release_slot(t3)
    await task


@pytest.mark.asyncio
async def test_stats_initial_state(scheduler):
    stats = scheduler.stats()
    assert stats["active_slots"] == 0
    assert stats["max_slots"] == 3
    assert stats["queued_requests"] == 0


@pytest.mark.asyncio
async def test_token_has_product_id(scheduler):
    token = await scheduler.acquire_slot("petraclus")
    assert token.product_id == "petraclus"
    await scheduler.release_slot(token)


@pytest.mark.asyncio
async def test_token_held_seconds(scheduler):
    token = await scheduler.acquire_slot("aiva")
    assert token.held_seconds >= 0.0
    await scheduler.release_slot(token)
