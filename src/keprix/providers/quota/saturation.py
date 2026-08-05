"""Quota saturation signal generation."""

from __future__ import annotations

from dataclasses import dataclass

from keprix.providers.quota.burn_rate import BurnRateMonitor
from keprix.providers.quota.tracker import QuotaTracker


@dataclass
class SaturationSignal:
    provider: str
    level: str
    remaining: int
    seconds_until_empty: float | None


class SaturationMonitor:
    def __init__(self, quota: QuotaTracker) -> None:
        self.quota = quota
        self.burn = BurnRateMonitor(quota)

    async def check(self, provider: str, *, account_id: str = "default") -> SaturationSignal:
        bucket = await self.quota.get_bucket(provider, account_id)
        seconds = await self.burn.seconds_until_empty(provider, account_id=account_id)
        ratio = 1.0 if bucket.limit <= 0 else bucket.remaining / bucket.limit
        level = "healthy"
        if ratio <= 0.05 or (seconds is not None and seconds < 60):
            level = "critical"
        elif ratio <= 0.2 or (seconds is not None and seconds < 300):
            level = "warning"
        return SaturationSignal(provider=provider, level=level, remaining=bucket.remaining, seconds_until_empty=seconds)
