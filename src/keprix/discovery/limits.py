"""Per-adapter rate limiter and circuit breaker helpers."""

from __future__ import annotations

import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class RateLimiter:
    """Simple sliding-window rate limiter (calls per minute)."""

    per_minute: int = 30
    _events: deque[float] = field(default_factory=deque)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def allow(self) -> bool:
        now = time.monotonic()
        with self._lock:
            while self._events and now - self._events[0] > 60.0:
                self._events.popleft()
            if len(self._events) >= max(1, self.per_minute):
                return False
            self._events.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


@dataclass
class CircuitBreaker:
    """Open after consecutive failures; half-open after cooldown."""

    failure_threshold: int = 5
    cooldown_seconds: float = 60.0
    failures: int = 0
    opened_at: float | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def allow(self) -> bool:
        with self._lock:
            if self.opened_at is None:
                return True
            if time.monotonic() - self.opened_at >= self.cooldown_seconds:
                # Half-open: allow one probe.
                return True
            return False

    def record_success(self) -> None:
        with self._lock:
            self.failures = 0
            self.opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self.failures += 1
            if self.failures >= self.failure_threshold:
                self.opened_at = time.monotonic()

    @property
    def is_open(self) -> bool:
        return not self.allow()


def retry_delay(attempt: int, *, base: float = 0.25, cap: float = 8.0) -> float:
    """Exponential backoff with full jitter."""
    exp = min(cap, base * (2 ** max(0, attempt)))
    return random.uniform(0, exp)
