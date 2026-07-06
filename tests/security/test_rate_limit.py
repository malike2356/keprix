"""Rate limit tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.security.rate_limit import DEFAULT_RULES, InMemoryRateLimiter


def test_sliding_window_blocks_after_limit():
    limiter = InMemoryRateLimiter()
    rule = DEFAULT_RULES["auth"]
    allowed_count = 0
    for _ in range(rule.limit):
        allowed, _, _ = limiter.hit("ip:test", rule)
        if allowed:
            allowed_count += 1
    blocked, remaining, reset_at = limiter.hit("ip:test", rule)
    assert allowed_count == rule.limit
    assert blocked is False
    assert remaining == 0
    assert reset_at > 0


@pytest.mark.asyncio
async def test_auth_route_returns_429_with_expected_shape():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        last = None
        for _ in range(61):
            last = await client.post(
                "/api/v1/auth/login",
                json={"username": "user", "password": "pass"},
            )
    assert last is not None
    assert last.status_code == 429
    payload = last.json()
    assert payload["code"] == "rate_limited"
    assert "retry_after" in payload
    assert last.headers.get("X-RateLimit-Remaining") is not None
    assert last.headers.get("X-RateLimit-Reset") is not None
