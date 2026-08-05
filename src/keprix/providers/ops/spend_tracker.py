"""Spend tracker: per-tenant, per-provider token spend with budget enforcement."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SpendRecord:
    tenant_id: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float
    at: float = field(default_factory=time.time)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


# Approximate per-1k-token prices (input/output) in USD, July 2026 estimates.
_PRICE_PER_1K: dict[str, tuple[float, float]] = {
    "anthropic":   (0.003,  0.015),   # claude-sonnet-4
    "openai":      (0.0025, 0.010),   # gpt-4o
    "gemini":      (0.00035, 0.00105),
    "groq":        (0.0001, 0.0001),
    "mistral":     (0.001,  0.003),
    "deepseek":    (0.00014, 0.00028),
    "pollinations":(0.0,    0.0),
    "ollama":      (0.0,    0.0),
    "lm_studio":   (0.0,    0.0),
}


def estimate_cost(provider: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Return an estimated USD cost for a call."""
    in_price, out_price = _PRICE_PER_1K.get(provider, (0.001, 0.003))
    return (prompt_tokens / 1000 * in_price) + (completion_tokens / 1000 * out_price)


class SpendTracker:
    """Track token spend per tenant and optionally enforce a monthly budget cap.

    Usage::

        tracker = SpendTracker()
        await tracker.record(SpendRecord(
            tenant_id="acme",
            provider="openai",
            prompt_tokens=500,
            completion_tokens=200,
            estimated_cost_usd=0.002,
        ))
        total = await tracker.total_spend("acme")
        within = await tracker.within_budget("acme", budget_usd=50.0)
    """

    def __init__(self) -> None:
        self._records: dict[str, list[SpendRecord]] = {}
        self._lock = asyncio.Lock()

    async def record(self, rec: SpendRecord) -> None:
        async with self._lock:
            self._records.setdefault(rec.tenant_id, []).append(rec)

    async def record_call(
        self,
        tenant_id: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> SpendRecord:
        """Build a SpendRecord with auto-estimated cost and record it."""
        cost = estimate_cost(provider, prompt_tokens, completion_tokens)
        rec = SpendRecord(
            tenant_id=tenant_id,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost_usd=cost,
        )
        await self.record(rec)
        return rec

    async def total_spend(self, tenant_id: str) -> float:
        async with self._lock:
            return sum(r.estimated_cost_usd for r in self._records.get(tenant_id, []))

    async def within_budget(self, tenant_id: str, budget_usd: float) -> bool:
        return await self.total_spend(tenant_id) < budget_usd

    async def summary(self, tenant_id: str) -> dict[str, Any]:
        async with self._lock:
            records = self._records.get(tenant_id, [])
        if not records:
            return {"tenant_id": tenant_id, "total_cost_usd": 0.0, "total_tokens": 0, "calls": 0}
        by_provider: dict[str, float] = {}
        for r in records:
            by_provider[r.provider] = by_provider.get(r.provider, 0.0) + r.estimated_cost_usd
        return {
            "tenant_id": tenant_id,
            "total_cost_usd": round(sum(r.estimated_cost_usd for r in records), 6),
            "total_tokens": sum(r.total_tokens for r in records),
            "calls": len(records),
            "by_provider": {p: round(c, 6) for p, c in by_provider.items()},
        }

    async def all_tenants(self) -> list[str]:
        async with self._lock:
            return list(self._records)
