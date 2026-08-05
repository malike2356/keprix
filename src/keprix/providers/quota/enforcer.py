"""Quota enforcement helper."""

from __future__ import annotations

from keprix.providers.fallback.error_handler import QuotaExhausted
from keprix.providers.quota.tracker import QuotaTracker


class QuotaEnforcer:
    def __init__(self, quota: QuotaTracker) -> None:
        self.quota = quota

    async def require(self, provider: str, estimated_tokens: int, *, account_id: str = "default") -> None:
        if not await self.quota.check(provider, estimated_tokens, account_id=account_id):
            raise QuotaExhausted(f"Provider {provider} quota exhausted")
