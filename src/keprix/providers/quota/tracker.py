"""Per-provider quota tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


@dataclass
class QuotaBucket:
    provider: str
    account_id: str = "default"
    limit: int = 0
    used: int = 0
    reserved: int = 0
    burn_rate: float = 0.0
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def remaining(self) -> int:
        if self.limit <= 0:
            return 10**12
        return max(0, self.limit - self.used - self.reserved)

    @property
    def is_exhausted(self) -> bool:
        return self.limit > 0 and self.remaining <= 0

    @property
    def remaining_pct(self) -> float:
        if self.limit <= 0:
            return 1.0
        return max(0.0, min(1.0, self.remaining / self.limit))


class QuotaTracker:
    def __init__(self) -> None:
        self._buckets: dict[tuple[str, str], QuotaBucket] = {}

    async def set_limit(self, provider: str, limit: int, *, account_id: str = "default") -> QuotaBucket:
        bucket = await self.get_bucket(provider, account_id)
        bucket.limit = limit
        return bucket

    async def set_quota(self, provider: str, *, remaining: int, total: int, account_id: str = "default") -> QuotaBucket:
        bucket = await self.get_bucket(provider, account_id)
        bucket.limit = total
        bucket.used = max(0, total - remaining) if total > 0 else 0
        bucket.reserved = 0
        return bucket

    async def get_bucket(self, provider: str, account_id: str = "default") -> QuotaBucket:
        key = (provider, account_id)
        self._buckets.setdefault(key, QuotaBucket(provider=provider, account_id=account_id))
        return self._buckets[key]

    async def check(self, provider: str, estimated_tokens: int, *, account_id: str = "default") -> bool:
        bucket = await self.get_bucket(provider, account_id)
        return bucket.remaining >= max(0, estimated_tokens)

    async def reserve(self, provider: str, tokens: int, *, account_id: str = "default") -> bool:
        if not await self.check(provider, tokens, account_id=account_id):
            return False
        bucket = await self.get_bucket(provider, account_id)
        bucket.reserved += max(0, tokens)
        return True

    async def record_usage(self, provider: str, tokens: int, *, account_id: str = "default") -> None:
        bucket = await self.get_bucket(provider, account_id)
        now = datetime.now(timezone.utc)
        elapsed = max((now - bucket.updated_at).total_seconds(), 1.0)
        bucket.burn_rate = (bucket.burn_rate * 0.7) + ((max(0, tokens) / elapsed) * 0.3)
        bucket.used += max(0, tokens)
        bucket.reserved = max(0, bucket.reserved - max(0, tokens))
        bucket.updated_at = now

    async def mark_exhausted(self, provider: str, *, account_id: str = "default") -> None:
        bucket = await self.get_bucket(provider, account_id)
        if bucket.limit > 0:
            bucket.used = bucket.limit

    async def get_all(self) -> dict[str, QuotaBucket]:
        return {provider: bucket for (provider, account_id), bucket in self._buckets.items() if account_id == "default"}

    async def predict_exhaustion(self, provider: str, *, account_id: str = "default") -> datetime | None:
        bucket = await self.get_bucket(provider, account_id)
        if bucket.limit <= 0 or bucket.burn_rate <= 0:
            return None
        return datetime.now(timezone.utc) + timedelta(seconds=bucket.remaining / bucket.burn_rate)
