"""Automatic provider ordering based on health and quota."""

from __future__ import annotations

from keprix.providers.combo.health import HealthMonitor
from keprix.providers.combo.tier import ComboTier, ProviderCandidate
from keprix.providers.quota.tracker import QuotaTracker


class AutoPromoter:
    def __init__(self, health: HealthMonitor, quota: QuotaTracker) -> None:
        self.health = health
        self.quota = quota

    async def order(self, tier: ComboTier, estimated_tokens: int = 0) -> list[ProviderCandidate]:
        scored: list[tuple[float, ProviderCandidate]] = []
        for candidate in tier.providers:
            if not self.health.is_available(candidate.provider_id):
                continue
            bucket = await self.quota.get_bucket(candidate.provider_id, candidate.account_id)
            quota_ratio = 1.0 if bucket.limit <= 0 else max(0.0, bucket.remaining / bucket.limit)
            score = (self.health.score(candidate.provider_id) * 0.7) + (quota_ratio * 0.3) + (candidate.weight * 0.01)
            if await self.quota.check(candidate.provider_id, estimated_tokens, account_id=candidate.account_id):
                scored.append((score, candidate))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [candidate for _, candidate in scored]
