"""Rate limiting with Redis or in-memory fallback."""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)

_memory_counters: dict[str, list[float]] = defaultdict(list)
_memory_lock = Lock()


def rate_limit(key: str, identifier: str, *, limit: int, window_seconds: int) -> bool:
    redis_url = os.getenv("REDIS_URL", "")
    if redis_url:
        try:
            return _rate_limit_redis(key, identifier, limit=limit, window_seconds=window_seconds, redis_url=redis_url)
        except Exception as exc:
            logger.debug("Redis rate limit fallback: %s", exc)
    return _rate_limit_memory(key, identifier, limit=limit, window_seconds=window_seconds)


def _rate_limit_memory(key: str, identifier: str, *, limit: int, window_seconds: int) -> bool:
    now = time.time()
    bucket_key = f"{key}:{identifier}"
    with _memory_lock:
        timestamps = [ts for ts in _memory_counters[bucket_key] if now - ts < window_seconds]
        if len(timestamps) >= limit:
            _memory_counters[bucket_key] = timestamps
            return False
        timestamps.append(now)
        _memory_counters[bucket_key] = timestamps
        return True


def _rate_limit_redis(key: str, identifier: str, *, limit: int, window_seconds: int, redis_url: str) -> bool:
    import redis

    client = redis.from_url(redis_url)
    bucket = f"keprix:rate:{key}:{identifier}"
    count = client.incr(bucket)
    if count == 1:
        client.expire(bucket, window_seconds)
    return count <= limit


def reset_rate_limits() -> None:
    with _memory_lock:
        _memory_counters.clear()
