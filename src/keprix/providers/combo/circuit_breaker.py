"""Circuit breaker: prevents hammering a failing provider.

Opens after N failures in a sliding window; auto-closes after cooldown.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FailureEvent:
    provider: str
    at: float = field(default_factory=time.monotonic)
    error: str = ""


class CircuitBreaker:
    """Per-provider circuit breaker with sliding failure window."""

    def __init__(
        self,
        failure_threshold: int = 5,
        window_seconds: float = 60.0,
        cooldown_seconds: float = 30.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds

        self._failures: dict[str, list[FailureEvent]] = {}
        self._broken_until: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def record_failure(self, provider: str, error: str = "") -> bool:
        """Record a failure. Returns True if circuit just opened."""
        async with self._lock:
            now = time.monotonic()
            events = self._failures.setdefault(provider, [])
            events.append(FailureEvent(provider=provider, at=now, error=error))
            # Trim outside window
            cutoff = now - self.window_seconds
            self._failures[provider] = [e for e in events if e.at >= cutoff]

            if len(self._failures[provider]) >= self.failure_threshold:
                if provider not in self._broken_until or self._broken_until[provider] <= now:
                    self._broken_until[provider] = now + self.cooldown_seconds
                    return True
        return False

    async def record_success(self, provider: str) -> None:
        """A success clears the failure window."""
        async with self._lock:
            self._failures.pop(provider, None)

    async def is_open(self, provider: str) -> bool:
        """Returns True if the circuit is currently open (provider should be skipped)."""
        async with self._lock:
            until = self._broken_until.get(provider, 0.0)
            return time.monotonic() < until

    async def close(self, provider: str) -> None:
        """Manually close the circuit (e.g. after health probe succeeds)."""
        async with self._lock:
            self._broken_until.pop(provider, None)
            self._failures.pop(provider, None)

    async def status(self) -> dict[str, Any]:
        async with self._lock:
            now = time.monotonic()
            return {
                p: {
                    "open": now < until,
                    "opens_until": until,
                    "failures_in_window": len(
                        [e for e in self._failures.get(p, []) if e.at >= now - self.window_seconds]
                    ),
                }
                for p, until in self._broken_until.items()
            }
