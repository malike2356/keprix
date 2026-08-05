"""Headroom detection: predict how much runway remains before quota or budget exhaustion."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass
class HeadroomResult:
    provider: str
    tokens_remaining: int        # -1 = unknown
    estimated_calls_remaining: int  # based on avg tokens per call
    exhaustion_eta: datetime | None  # None = unknown or not exhausting
    budget_remaining_usd: float  # -1.0 = no budget set
    risk_level: str              # "ok" | "warn" | "critical"
    message: str = ""


class HeadroomDetector:
    """Combine quota and spend data to produce a headroom estimate.

    This class does not track state itself; it computes from snapshots
    passed in by the caller (from QuotaTracker, SpendTracker, etc.).

    Usage::

        detector = HeadroomDetector(avg_tokens_per_call=1500)
        result = detector.compute(
            provider="openai",
            tokens_remaining=50_000,
            burn_rate_tokens_per_sec=10.0,
            spend_usd=42.0,
            budget_usd=50.0,
        )
    """

    def __init__(
        self,
        avg_tokens_per_call: int = 1500,
        warn_calls_threshold: int = 100,
        critical_calls_threshold: int = 10,
    ) -> None:
        self._avg_call = avg_tokens_per_call
        self._warn = warn_calls_threshold
        self._critical = critical_calls_threshold

    def compute(
        self,
        provider: str,
        tokens_remaining: int = -1,
        burn_rate_tokens_per_sec: float = 0.0,
        spend_usd: float = 0.0,
        budget_usd: float = -1.0,
    ) -> HeadroomResult:
        # Calls remaining from token quota
        if tokens_remaining < 0:
            calls_remaining = -1
            exhaustion_eta = None
        elif tokens_remaining == 0:
            calls_remaining = 0
            exhaustion_eta = datetime.now(timezone.utc)
        else:
            calls_remaining = tokens_remaining // max(1, self._avg_call)
            if burn_rate_tokens_per_sec > 0:
                seconds_left = tokens_remaining / burn_rate_tokens_per_sec
                exhaustion_eta = datetime.now(timezone.utc) + timedelta(seconds=seconds_left)
            else:
                exhaustion_eta = None

        # Budget headroom
        budget_remaining = -1.0
        if budget_usd > 0:
            budget_remaining = max(0.0, budget_usd - spend_usd)

        # Risk level
        if calls_remaining == 0 or budget_remaining == 0.0:
            risk = "critical"
            msg = "Quota or budget exhausted."
        elif calls_remaining != -1 and calls_remaining < self._critical:
            risk = "critical"
            msg = f"Only {calls_remaining} calls remaining."
        elif calls_remaining != -1 and calls_remaining < self._warn:
            risk = "warn"
            msg = f"{calls_remaining} calls remaining; approaching limit."
        elif budget_remaining != -1.0 and budget_remaining < (budget_usd * 0.10):
            risk = "warn"
            msg = f"Budget at {budget_remaining:.2f} USD remaining."
        else:
            risk = "ok"
            msg = "Sufficient headroom."

        return HeadroomResult(
            provider=provider,
            tokens_remaining=tokens_remaining,
            estimated_calls_remaining=calls_remaining,
            exhaustion_eta=exhaustion_eta,
            budget_remaining_usd=budget_remaining,
            risk_level=risk,
            message=msg,
        )
