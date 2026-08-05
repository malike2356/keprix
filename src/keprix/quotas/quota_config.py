"""QuotaConfig: per-product resource quota definitions.

Quotas are loaded from each product's keprix.yaml and stored here at startup.
The enforcer reads these limits before every LLM call and tool invocation.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ResourceType(str, Enum):
    LLM_TOKENS_IN = "llm_tokens_in"
    LLM_TOKENS_OUT = "llm_tokens_out"
    TOOL_CALLS = "tool_calls"
    CONCURRENT_SESSIONS = "concurrent_sessions"
    STORAGE_BYTES = "storage_bytes"
    VOICE_MINUTES = "voice_minutes"
    API_CALLS = "api_calls"
    MUTATION_RUNS = "mutation_runs"
    ESTIMATED_TOKENS = "estimated_tokens"


# Default limits used when a product registers no explicit quota.
_UNLIMITED = 10_000_000_000   # effectively unlimited


@dataclass
class ProductQuota:
    """Quota limits and enforcement policy for one product."""
    product_id: str
    period: str = "monthly"      # "hourly" | "daily" | "weekly" | "monthly"
    limits: dict[ResourceType, int] = field(default_factory=dict)
    on_exhaustion: dict[ResourceType, str] = field(default_factory=dict)
    burst_allowance: float = 0.0    # fraction of limit that can be exceeded before hard block

    def get_limit(self, resource: ResourceType) -> int:
        return self.limits.get(resource, _UNLIMITED)

    def get_action(self, resource: ResourceType) -> str:
        return self.on_exhaustion.get(resource, "block")

    def hard_limit(self, resource: ResourceType) -> int:
        """Limit including burst allowance."""
        base = self.get_limit(resource)
        return int(base * (1.0 + self.burst_allowance))


@dataclass
class QuotaUsage:
    """Current period usage for one product."""
    product_id: str
    period_start: datetime
    period_end: datetime
    usage: dict[ResourceType, int] = field(default_factory=dict)
    limits: dict[ResourceType, int] = field(default_factory=dict)
    burst_allowance: float = 0.0

    def used(self, resource: ResourceType) -> int:
        return self.usage.get(resource, 0)

    def limit(self, resource: ResourceType) -> int:
        return self.limits.get(resource, _UNLIMITED)

    def hard_limit(self, resource: ResourceType) -> int:
        base = self.limit(resource)
        return int(base * (1.0 + self.burst_allowance))

    def remaining(self, resource: ResourceType) -> int:
        return max(0, self.hard_limit(resource) - self.used(resource))

    def pct_used(self, resource: ResourceType) -> float:
        lim = self.limit(resource)
        if lim == 0 or lim >= _UNLIMITED:
            return 0.0
        return min(1.0, self.used(resource) / lim)

    def is_exhausted(self, resource: ResourceType) -> bool:
        return self.remaining(resource) <= 0

    def is_near_limit(self, resource: ResourceType, threshold: float = 0.90) -> bool:
        return self.pct_used(resource) >= threshold

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "usage": {r.value: v for r, v in self.usage.items()},
            "limits": {r.value: v for r, v in self.limits.items()},
        }


class QuotaConfig:
    """Registry of per-product quota definitions.

    Usage::

        config = QuotaConfig()
        config.register(ProductQuota(
            product_id="aiva",
            period="monthly",
            limits={ResourceType.LLM_TOKENS_IN: 5_000_000},
            on_exhaustion={ResourceType.LLM_TOKENS_IN: "graceful"},
            burst_allowance=0.10,
        ))
        quota = await config.get_quota("aiva")
    """

    def __init__(self) -> None:
        self._quotas: dict[str, ProductQuota] = {}
        self._lock = asyncio.Lock()

    def register(self, quota: ProductQuota) -> None:
        """Register or replace quota definition for a product (call at startup)."""
        self._quotas[quota.product_id] = quota

    async def get_quota(self, product_id: str) -> ProductQuota:
        """Return the quota for a product. Returns an unlimited quota if unregistered."""
        async with self._lock:
            if product_id in self._quotas:
                return self._quotas[product_id]
            return ProductQuota(product_id=product_id)   # default: unlimited

    def list_products(self) -> list[str]:
        return list(self._quotas.keys())


_default_config: QuotaConfig | None = None


def get_quota_config() -> QuotaConfig:
    global _default_config
    if _default_config is None:
        _default_config = QuotaConfig()
    return _default_config


def reset_quota_config() -> None:
    global _default_config
    _default_config = None
