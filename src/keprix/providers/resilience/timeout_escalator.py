"""Timeout escalation per tier: short timeouts on premium tiers, longer on fallbacks."""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Default tier timeout ladder (seconds).
# Earlier tiers (premium/fast) get tighter timeouts.
_DEFAULT_LADDER: list[float] = [30.0, 60.0, 120.0, 240.0]


@dataclass
class TierTimeout:
    tier_id: str
    timeout_seconds: float


class TimeoutEscalator:
    """Return an escalating timeout per tier index.

    The first tier gets the tightest timeout; each subsequent tier gets
    a longer one to accommodate slower/less reliable fallback providers.

    Usage::

        esc = TimeoutEscalator(ladder=[30, 60, 120])
        timeout = esc.for_tier(tier_index=0)  # -> 30s
        timeout = esc.for_tier(tier_index=2)  # -> 120s
        timeout = esc.for_tier(tier_index=5)  # -> 120s (clamps to last)
    """

    def __init__(
        self,
        ladder: list[float] | None = None,
        tier_ids: list[str] | None = None,
    ) -> None:
        self._ladder   = ladder or _DEFAULT_LADDER
        self._tier_ids = tier_ids or []

    def for_tier(self, tier_index: int) -> float:
        """Return the timeout for the given tier index."""
        idx     = max(0, min(tier_index, len(self._ladder) - 1))
        timeout = self._ladder[idx]
        logger.debug("Tier[%d] timeout -> %.0fs", tier_index, timeout)
        return timeout

    def for_tier_id(self, tier_id: str) -> float:
        """Return the timeout for a tier identified by string ID."""
        try:
            idx = self._tier_ids.index(tier_id)
        except ValueError:
            idx = len(self._tier_ids)  # treat unknown as last/longest
        return self.for_tier(idx)

    def all_timeouts(self) -> list[TierTimeout]:
        """Return timeout assignments for all known tier IDs."""
        result = []
        for i, tid in enumerate(self._tier_ids):
            result.append(TierTimeout(tier_id=tid, timeout_seconds=self.for_tier(i)))
        return result

    def summary(self) -> dict[str, float]:
        """Return {tier_id: timeout_seconds} for all known tiers."""
        return {tid: self.for_tier(i) for i, tid in enumerate(self._tier_ids)}
