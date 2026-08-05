"""Tests for ops/prompt_cache.py."""

from __future__ import annotations

import asyncio

import pytest

from keprix.providers.ops.prompt_cache import PromptCache


@pytest.fixture
def cache():
    return PromptCache(ttl=60, max_size=10)


def _msgs(text="Hello"):
    return [{"role": "user", "content": text}]


@pytest.mark.asyncio
async def test_cache_miss_returns_none(cache):
    key = cache.make_key(_msgs())
    assert await cache.get(key) is None


@pytest.mark.asyncio
async def test_cache_hit_returns_entry(cache):
    msgs = _msgs("summarise")
    key = cache.make_key(msgs)
    await cache.put(key, msgs, {"answer": "yes"}, tokens_saved=500)
    entry = await cache.get(key)
    assert entry is not None
    assert entry.response == {"answer": "yes"}


@pytest.mark.asyncio
async def test_cache_hit_increments_hits(cache):
    msgs = _msgs("x")
    key = cache.make_key(msgs)
    await cache.put(key, msgs, "response")
    await cache.get(key)
    await cache.get(key)
    entry = await cache.get(key)
    assert entry.hits == 3


@pytest.mark.asyncio
async def test_cache_expiry(monkeypatch):
    c = PromptCache(ttl=0.05)
    msgs = _msgs("expiring")
    key = c.make_key(msgs)
    await c.put(key, msgs, "old")
    await asyncio.sleep(0.1)
    assert await c.get(key) is None


@pytest.mark.asyncio
async def test_invalidate(cache):
    msgs = _msgs("inv")
    key = cache.make_key(msgs)
    await cache.put(key, msgs, "resp")
    await cache.invalidate(key)
    assert await cache.get(key) is None


@pytest.mark.asyncio
async def test_max_size_evicts_oldest(cache):
    for i in range(10):
        msgs = _msgs(f"msg-{i}")
        key = cache.make_key(msgs)
        await cache.put(key, msgs, f"resp-{i}")
    # 11th put should evict the oldest
    msgs = _msgs("msg-10")
    key = cache.make_key(msgs)
    await cache.put(key, msgs, "resp-10")
    stats = await cache.stats()
    assert stats["size"] <= 10


@pytest.mark.asyncio
async def test_same_messages_same_key(cache):
    m1 = [{"role": "user", "content": "hello"}]
    m2 = [{"role": "user", "content": "hello"}]
    assert cache.make_key(m1) == cache.make_key(m2)


@pytest.mark.asyncio
async def test_different_messages_different_key(cache):
    k1 = cache.make_key(_msgs("a"))
    k2 = cache.make_key(_msgs("b"))
    assert k1 != k2


@pytest.mark.asyncio
async def test_stats(cache):
    msgs = _msgs("stats-test")
    key = cache.make_key(msgs)
    await cache.put(key, msgs, "r", tokens_saved=100)
    await cache.get(key)
    stats = await cache.stats()
    assert stats["size"] == 1
    assert stats["total_tokens_saved"] == 100
