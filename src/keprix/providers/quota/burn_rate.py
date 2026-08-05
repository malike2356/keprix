"""Burn-rate helpers for quota prediction."""

from __future__ import annotations

from datetime import datetime

from keprix.providers.quota.tracker import QuotaTracker


class BurnRateMonitor:
    def __init__(self, quota: QuotaTracker) -> None:
        self.quota = quota

    async def seconds_until_empty(self, provider: str, *, account_id: str = "default") -> float | None:
        bucket = await self.quota.get_bucket(provider, account_id)
        if bucket.limit <= 0 or bucket.burn_rate <= 0:
            return None
        return bucket.remaining / bucket.burn_rate

    async def predict_exhaustion(self, provider: str, *, account_id: str = "default") -> datetime | None:
        return await self.quota.predict_exhaustion(provider, account_id=account_id)
