"""Fair-share account selection."""

from __future__ import annotations

from keprix.providers.quota.tracker import QuotaTracker


class FairShareAllocator:
    def __init__(self, quota: QuotaTracker) -> None:
        self.quota = quota

    async def choose_account(self, provider: str, account_ids: list[str], estimated_tokens: int = 0) -> str | None:
        candidates = []
        for account_id in account_ids:
            bucket = await self.quota.get_bucket(provider, account_id)
            if await self.quota.check(provider, estimated_tokens, account_id=account_id):
                ratio = 1.0 if bucket.limit <= 0 else bucket.remaining / bucket.limit
                candidates.append((ratio, account_id))
        if not candidates:
            return None
        candidates.sort(reverse=True)
        return candidates[0][1]
