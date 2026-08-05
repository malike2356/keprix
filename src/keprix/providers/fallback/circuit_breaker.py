"""Small circuit breaker for provider failures."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class CircuitState:
    failures: int = 0
    opened_until: float = 0.0


class CircuitBreaker:
    def __init__(self, threshold: int = 3, cooldown_seconds: int = 30) -> None:
        self.threshold = threshold
        self.cooldown_seconds = cooldown_seconds
        self._states: dict[str, CircuitState] = {}

    def allow(self, provider: str) -> bool:
        state = self._states.setdefault(provider, CircuitState())
        return time.monotonic() >= state.opened_until

    def record_success(self, provider: str) -> None:
        self._states[provider] = CircuitState()

    def record_failure(self, provider: str) -> bool:
        state = self._states.setdefault(provider, CircuitState())
        state.failures += 1
        if state.failures >= self.threshold:
            state.opened_until = time.monotonic() + self.cooldown_seconds
            return True
        return False
