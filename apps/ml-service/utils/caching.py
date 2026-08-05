import hashlib
import json
from typing import Any

_redis: Any | None = None


async def init_cache(redis_url: str) -> None:
    global _redis
    try:
        import redis.asyncio as redis_async

        _redis = redis_async.from_url(redis_url, decode_responses=True)
        await _redis.ping()
    except Exception:
        _redis = None


async def close_cache() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
    _redis = None


def cache_key(prefix: str, payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    return f"keprix:ml:{prefix}:{digest}"


async def get_cached(prefix: str, payload: dict[str, Any]) -> Any | None:
    if _redis is None:
        return None
    raw = await _redis.get(cache_key(prefix, payload))
    return json.loads(raw) if raw else None


async def set_cached(prefix: str, payload: dict[str, Any], value: Any, ttl: int = 86400) -> None:
    if _redis is None:
        return
    await _redis.setex(cache_key(prefix, payload), ttl, json.dumps(value))
