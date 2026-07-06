"""Redis client helpers for health monitoring and auto-repair."""

from __future__ import annotations

import asyncio
from typing import Any

from keprix.config.settings import get_settings

_redis_client: Any = None


def _connect_sync(url: str) -> Any:
    import redis

    return redis.from_url(url, decode_responses=True)


async def get_redis() -> Any:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        if not settings.redis_url:
            raise RuntimeError("redis URL is not configured")
        _redis_client = await asyncio.to_thread(_connect_sync, settings.redis_url)
    return _redis_client


async def reconnect_redis() -> Any:
    global _redis_client
    if _redis_client is not None:
        try:
            await asyncio.to_thread(_redis_client.close)
        except Exception:
            pass
        _redis_client = None
    client = await get_redis()
    await asyncio.to_thread(client.ping)
    return client


def reset_redis_client() -> None:
    global _redis_client
    _redis_client = None
