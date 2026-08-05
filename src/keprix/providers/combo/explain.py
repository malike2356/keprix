"""Route explanation objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class RouteAttempt:
    provider: str
    tier: str
    status: str
    reason: str = ""
    latency_ms: int | None = None


@dataclass
class RouteExplanation:
    combo_id: str
    strategy: str | None = None
    selected_provider: str | None = None
    selected_tier: str | None = None
    attempts: list[RouteAttempt] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def add(self, provider: str, tier: str, status: str, reason: str = "", latency_ms: int | None = None) -> None:
        self.attempts.append(RouteAttempt(provider=provider, tier=tier, status=status, reason=reason, latency_ms=latency_ms))

    def as_dict(self) -> dict[str, Any]:
        return {
            "combo_id": self.combo_id,
            "strategy": self.strategy,
            "selected_provider": self.selected_provider,
            "selected_tier": self.selected_tier,
            "started_at": self.started_at,
            "attempts": [attempt.__dict__ for attempt in self.attempts],
            "metadata": self.metadata,
        }
