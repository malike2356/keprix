"""Provider health scoring for combo routing."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class ProviderHealth:
    successes: int = 0
    failures: int = 0
    latency_ms: float = 0.0
    demoted_until: float = 0.0

    @property
    def success_rate(self) -> float:
        total = self.successes + self.failures
        return 1.0 if total == 0 else self.successes / total

    @property
    def available(self) -> bool:
        return time.monotonic() >= self.demoted_until

    @property
    def score(self) -> float:
        latency_penalty = min(self.latency_ms / 10_000, 0.5) if self.latency_ms else 0.0
        availability = 1.0 if self.available else 0.0
        return max(0.0, (self.success_rate * availability) - latency_penalty)


class HealthMonitor:
    def __init__(self) -> None:
        self._health: dict[str, ProviderHealth] = {}

    def get(self, provider: str) -> ProviderHealth:
        return self._health.setdefault(provider, ProviderHealth())

    def is_available(self, provider: str) -> bool:
        return self.get(provider).available

    def record_success(self, provider: str, latency_ms: int) -> None:
        health = self.get(provider)
        health.successes += 1
        health.latency_ms = latency_ms if health.latency_ms == 0 else (health.latency_ms * 0.8) + (latency_ms * 0.2)

    def record_failure(self, provider: str, cooldown_seconds: int = 30) -> None:
        health = self.get(provider)
        health.failures += 1
        health.demoted_until = max(health.demoted_until, time.monotonic() + cooldown_seconds)

    def score(self, provider: str) -> float:
        return self.get(provider).score
