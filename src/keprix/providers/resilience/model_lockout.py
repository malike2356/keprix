"""Model lockout with exponential backoff per provider."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_BASE_DELAY = 5.0        # seconds
_MAX_DELAY  = 300.0      # 5 minutes ceiling
_BACKOFF    = 2.0        # multiplier per failure


@dataclass
class LockoutState:
    provider: str
    failures: int = 0
    locked_until: float = 0.0   # monotonic time
    last_error: str = ""

    @property
    def is_locked(self) -> bool:
        return time.monotonic() < self.locked_until

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, self.locked_until - time.monotonic())

    def next_delay(self) -> float:
        delay = _BASE_DELAY * (_BACKOFF ** max(0, self.failures - 1))
        return min(delay, _MAX_DELAY)


class ModelLockout:
    """Per-provider lockout with exponential backoff.

    5s -> 10s -> 20s -> 40s -> 80s -> ... -> 300s (ceiling).
    A provider is locked on each consecutive failure and unlocked
    either by calling ``release()`` explicitly or by waiting out the
    backoff window.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._states: dict[str, LockoutState] = {}

    def _get(self, provider: str) -> LockoutState:
        if provider not in self._states:
            self._states[provider] = LockoutState(provider=provider)
        return self._states[provider]

    async def is_locked(self, provider: str) -> bool:
        async with self._lock:
            return self._get(provider).is_locked

    async def record_failure(self, provider: str, error: str = "") -> float:
        """Record a failure. Returns the lockout duration in seconds."""
        async with self._lock:
            state = self._get(provider)
            state.failures += 1
            state.last_error = error
            delay = state.next_delay()
            state.locked_until = time.monotonic() + delay
            logger.warning(
                "Provider %r locked for %.0fs (failure #%d): %s",
                provider, delay, state.failures, error or "no detail",
            )
            return delay

    async def record_success(self, provider: str) -> None:
        """Reset the failure counter after a successful call."""
        async with self._lock:
            state = self._get(provider)
            if state.failures:
                logger.debug("Provider %r lockout cleared after success", provider)
            state.failures = 0
            state.locked_until = 0.0
            state.last_error = ""

    async def release(self, provider: str) -> None:
        """Manually lift a lockout (e.g., after a health probe passes)."""
        async with self._lock:
            state = self._get(provider)
            state.locked_until = 0.0
            logger.info("Provider %r lockout released manually", provider)

    async def snapshot(self) -> dict[str, dict]:
        """Return a read-only summary of all lockout states."""
        async with self._lock:
            return {
                p: {
                    "failures": s.failures,
                    "is_locked": s.is_locked,
                    "remaining_seconds": round(s.remaining_seconds, 1),
                    "last_error": s.last_error,
                }
                for p, s in self._states.items()
            }
