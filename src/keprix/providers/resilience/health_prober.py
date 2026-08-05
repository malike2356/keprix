"""Active health prober: periodic lightweight pings to provider endpoints."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

# Type alias for a probe callable: (provider_id) -> bool (True = healthy)
ProbeCallable = Callable[[str], Awaitable[bool]]


@dataclass
class ProbeResult:
    provider: str
    healthy: bool
    latency_ms: float
    checked_at: float = field(default_factory=time.monotonic)
    error: str = ""


class HealthProber:
    """Run periodic active health probes against each registered provider.

    Usage::

        async def my_probe(provider_id: str) -> bool:
            # ping the provider, return True if it responds OK
            ...

        prober = HealthProber(probe_fn=my_probe, interval=60)
        prober.register("openai")
        prober.register("anthropic")
        await prober.start()          # runs in background until stop()
        result = prober.last_result("openai")
    """

    def __init__(
        self,
        probe_fn: ProbeCallable,
        interval: float = 60.0,    # seconds between full probe sweeps
        timeout: float = 10.0,     # per-provider probe timeout
    ) -> None:
        self._probe_fn = probe_fn
        self._interval = interval
        self._timeout  = timeout
        self._providers: list[str] = []
        self._results: dict[str, ProbeResult] = {}
        self._task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, provider: str) -> None:
        if provider not in self._providers:
            self._providers.append(provider)

    def unregister(self, provider: str) -> None:
        self._providers = [p for p in self._providers if p != provider]
        self._results.pop(provider, None)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop(), name="health-prober")
        logger.info("HealthProber started (interval=%.0fs)", self._interval)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("HealthProber stopped")

    # ------------------------------------------------------------------
    # Probe loop
    # ------------------------------------------------------------------

    async def _loop(self) -> None:
        while True:
            await self._probe_all()
            await asyncio.sleep(self._interval)

    async def _probe_all(self) -> None:
        tasks = [self._probe_one(p) for p in self._providers]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _probe_one(self, provider: str) -> None:
        t0 = time.monotonic()
        try:
            healthy = await asyncio.wait_for(self._probe_fn(provider), timeout=self._timeout)
            latency = (time.monotonic() - t0) * 1000
            result  = ProbeResult(provider=provider, healthy=healthy, latency_ms=latency)
            if not healthy:
                logger.warning("Health probe FAIL: %r (%.0fms)", provider, latency)
            else:
                logger.debug("Health probe OK: %r (%.0fms)", provider, latency)
        except asyncio.TimeoutError:
            latency = self._timeout * 1000
            result  = ProbeResult(
                provider=provider, healthy=False, latency_ms=latency, error="timeout"
            )
            logger.warning("Health probe TIMEOUT: %r", provider)
        except Exception as exc:
            latency = (time.monotonic() - t0) * 1000
            result  = ProbeResult(
                provider=provider, healthy=False, latency_ms=latency, error=str(exc)
            )
            logger.warning("Health probe ERROR: %r: %s", provider, exc)
        self._results[provider] = result

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def last_result(self, provider: str) -> ProbeResult | None:
        return self._results.get(provider)

    def is_healthy(self, provider: str) -> bool | None:
        """Return True/False based on latest probe, or None if never probed."""
        result = self._results.get(provider)
        return result.healthy if result else None

    def all_results(self) -> dict[str, ProbeResult]:
        return dict(self._results)

    async def probe_now(self, provider: str) -> ProbeResult:
        """Force an immediate probe and return the result."""
        await self._probe_one(provider)
        return self._results[provider]
