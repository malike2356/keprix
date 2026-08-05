"""Sliding-window rate limiting."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from keprix.config.settings import get_settings

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None  # type: ignore[assignment]


@dataclass(frozen=True)
class RateLimitRule:
    name: str
    limit: int
    window_seconds: int
    key_prefix: str


DEFAULT_RULES: dict[str, RateLimitRule] = {
    "general": RateLimitRule("general", 300, 60, "rl:general"),
    "agent_chat": RateLimitRule("agent_chat", 60, 60, "rl:agent"),
    "key_activation": RateLimitRule("key_activation", 5, 3600, "rl:key"),
    "risky_tools": RateLimitRule("risky_tools", 100, 3600, "rl:risky"),
    "auth": RateLimitRule("auth", 10, 900, "rl:auth"),
    "audio_transcribe": RateLimitRule("audio_transcribe", 30, 3600, "rl:audio"),
}


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def hit(self, key: str, rule: RateLimitRule) -> tuple[bool, int, int]:
        now = time.time()
        cutoff = now - rule.window_seconds
        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= rule.limit:
                reset_at = int(bucket[0] + rule.window_seconds)
                return False, 0, reset_at
            bucket.append(now)
            remaining = max(rule.limit - len(bucket), 0)
            reset_at = int(now + rule.window_seconds)
            return True, remaining, reset_at


class RedisRateLimiter:
    def __init__(self, url: str) -> None:
        if redis is None:
            raise RuntimeError("redis package is required for RedisRateLimiter")
        self._client = redis.from_url(url, decode_responses=True)

    def hit(self, key: str, rule: RateLimitRule) -> tuple[bool, int, int]:
        now = time.time()
        pipe = self._client.pipeline()
        pipe.zremrangebyscore(key, 0, now - rule.window_seconds)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, rule.window_seconds + 1)
        _, _, count, _ = pipe.execute()
        if count > rule.limit:
            oldest = self._client.zrange(key, 0, 0, withscores=True)
            reset_at = int(oldest[0][1] + rule.window_seconds) if oldest else int(now + rule.window_seconds)
            self._client.zrem(key, str(now))
            return False, 0, reset_at
        remaining = max(rule.limit - count, 0)
        return True, remaining, int(now + rule.window_seconds)


class RateLimiter:
    def __init__(self) -> None:
        settings = get_settings()
        self._memory = InMemoryRateLimiter()
        self._redis: RedisRateLimiter | None = None
        if settings.redis_url and redis is not None:
            try:
                self._redis = RedisRateLimiter(settings.redis_url)
            except Exception:
                self._redis = None

    def check(self, identifier: str, rule: RateLimitRule) -> tuple[bool, int, int]:
        key = f"{rule.key_prefix}:{identifier}"
        backend = self._redis or self._memory
        return backend.hit(key, rule)


_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter()
    return _limiter


def reset_rate_limiter() -> None:
    """Clear the shared limiter (for tests)."""
    global _limiter
    if _limiter is not None and getattr(_limiter, "_redis", None) is not None:
        try:
            client = _limiter._redis._client
            for key in client.scan_iter("rl:*"):
                client.delete(key)
        except Exception:
            pass
    if _limiter is not None:
        try:
            _limiter._memory._events.clear()
        except Exception:
            pass
    _limiter = None


def _user_from_bearer(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return None
    try:
        from keprix.auth.session import auth_manager

        user = auth_manager.validate_token(token)
    except Exception:
        return None
    if not user:
        return None
    user_id = user.get("id") or user.get("username")
    return str(user_id) if user_id else None


def _route_rule(path: str, method: str) -> RateLimitRule:
    if path == "/api/audio/transcribe" and method.upper() == "POST":
        return DEFAULT_RULES["audio_transcribe"]
    if path.startswith("/api/v1/auth"):
        return DEFAULT_RULES["auth"]
    if path.startswith("/v1/") or path.startswith("/api/v1/agent/chat") or path.startswith("/api/v1/chat"):
        return DEFAULT_RULES["agent_chat"]
    if path.startswith("/api/v1/keys/activate"):
        return DEFAULT_RULES["key_activation"]
    if path.startswith("/api/v1/tools/risky"):
        return DEFAULT_RULES["risky_tools"]
    return DEFAULT_RULES["general"]


def _client_identifier(request: Request) -> str:
    api_key = getattr(request.state, "api_key", None)
    if api_key is not None:
        key_id = getattr(api_key, "key_id", None)
        if key_id:
            return f"apikey:{key_id}"
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    bearer_user = _user_from_bearer(request)
    if bearer_user:
        return f"user:{bearer_user}"
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return f"ip:{ip}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)
        rule = _route_rule(request.url.path, request.method)
        limiter = get_rate_limiter()
        allowed, remaining, reset_at = limiter.check(_client_identifier(request), rule)
        if not allowed:
            retry_after = max(reset_at - int(time.time()), 1)
            return JSONResponse(
                status_code=429,
                content={
                    "code": "rate_limited",
                    "message": (
                        f"Too many requests. You have {remaining} requests left. "
                        f"Reset at {reset_at}."
                    ),
                    "retry_after": retry_after,
                },
                headers={
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_at),
                    "Retry-After": str(retry_after),
                },
            )
        response = await call_next(request)
        response.headers.setdefault("X-RateLimit-Remaining", str(remaining))
        response.headers.setdefault("X-RateLimit-Reset", str(reset_at))
        return response
