"""Per-key rate limiting for the public API."""

from __future__ import annotations

from fastapi import HTTPException, Request

from keprix.public_api.keys import ApiKeyContext
from keprix.security.rate_limit import DEFAULT_RULES, get_rate_limiter


PUBLIC_API_RULE = DEFAULT_RULES["agent_chat"]


def enforce_rate_limit(request: Request, ctx: ApiKeyContext) -> None:
    limiter = get_rate_limiter()
    identifier = f"apikey:{ctx.key_id}"
    allowed, remaining, reset_at = limiter.check(identifier, PUBLIC_API_RULE)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "code": "rate_limited",
                "retry_after": max(reset_at - __import__("time").time(), 1),
            },
            headers={
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_at),
            },
        )
    request.state.rate_limit_remaining = remaining
