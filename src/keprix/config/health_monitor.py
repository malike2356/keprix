"""Continuous component health monitoring for self-configuration."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Awaitable, Callable

import httpx

from keprix.brain.provider_registry import iter_configured_providers


@dataclass
class ComponentHealth:
    name: str
    status: str  # "healthy" | "degraded" | "down"
    latency_ms: float
    error: str
    checked_at: float


class ConfigHealthMonitor:
    def __init__(self, check_interval_seconds: int = 60):
        self.interval = check_interval_seconds
        self._results: dict[str, ComponentHealth] = {}
        self._callbacks: list[Callable[[ComponentHealth], Awaitable[None]]] = []
        self._task: asyncio.Task | None = None

    def on_status_change(self, cb: Callable[[ComponentHealth], Awaitable[None]]) -> None:
        self._callbacks.append(cb)

    async def run(self) -> None:
        while True:
            await self._run_all_checks()
            await asyncio.sleep(self.interval)

    def start_background(self) -> asyncio.Task:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.run())
        return self._task

    async def _run_all_checks(self) -> None:
        checks = [
            self._check_llm_providers(),
            self._check_redis(),
            self._check_postgres(),
            self._check_egress(),
            self._check_channel_adapters(),
            self._check_credential_proxy(),
        ]
        results = await asyncio.gather(*checks, return_exceptions=True)
        for batch in results:
            if isinstance(batch, list):
                for health in batch:
                    prev = self._results.get(health.name)
                    self._results[health.name] = health
                    if prev and prev.status != health.status:
                        for cb in self._callbacks:
                            asyncio.create_task(cb(health))

    async def _check_llm_providers(self) -> list[ComponentHealth]:
        results: list[ComponentHealth] = []
        async with httpx.AsyncClient(timeout=5.0) as client:
            for provider in iter_configured_providers():
                t0 = time.monotonic()
                try:
                    await provider.health_check(client)
                    latency = (time.monotonic() - t0) * 1000
                    results.append(
                        ComponentHealth(
                            name=f"llm:{provider.name}",
                            status="healthy",
                            latency_ms=latency,
                            error="",
                            checked_at=time.time(),
                        )
                    )
                except Exception as exc:
                    results.append(
                        ComponentHealth(
                            name=f"llm:{provider.name}",
                            status="down",
                            latency_ms=0,
                            error=str(exc)[:200],
                            checked_at=time.time(),
                        )
                    )
        return results

    async def _check_redis(self) -> list[ComponentHealth]:
        from keprix.db.redis_client import get_redis

        t0 = time.monotonic()
        try:
            client = await get_redis()
            await asyncio.to_thread(client.ping)
            return [
                ComponentHealth(
                    name="redis",
                    status="healthy",
                    latency_ms=(time.monotonic() - t0) * 1000,
                    error="",
                    checked_at=time.time(),
                )
            ]
        except Exception as exc:
            return [
                ComponentHealth(
                    name="redis",
                    status="down",
                    latency_ms=0,
                    error=str(exc)[:200],
                    checked_at=time.time(),
                )
            ]

    async def _check_postgres(self) -> list[ComponentHealth]:
        from keprix.db.postgres import ping

        t0 = time.monotonic()
        try:
            await ping()
            return [
                ComponentHealth(
                    name="postgres",
                    status="healthy",
                    latency_ms=(time.monotonic() - t0) * 1000,
                    error="",
                    checked_at=time.time(),
                )
            ]
        except Exception as exc:
            return [
                ComponentHealth(
                    name="postgres",
                    status="down",
                    latency_ms=0,
                    error=str(exc)[:200],
                    checked_at=time.time(),
                )
            ]

    async def _check_egress(self) -> list[ComponentHealth]:
        probes = [
            ("egress:api.openai.com", "https://api.openai.com/"),
            ("egress:api.anthropic.com", "https://api.anthropic.com/"),
            ("egress:api.deepseek.com", "https://api.deepseek.com/"),
        ]
        results: list[ComponentHealth] = []
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, url in probes:
                t0 = time.monotonic()
                try:
                    await client.head(url)
                    results.append(
                        ComponentHealth(
                            name=name,
                            status="healthy",
                            latency_ms=(time.monotonic() - t0) * 1000,
                            error="",
                            checked_at=time.time(),
                        )
                    )
                except Exception as exc:
                    results.append(
                        ComponentHealth(
                            name=name,
                            status="down",
                            latency_ms=0,
                            error=str(exc)[:200],
                            checked_at=time.time(),
                        )
                    )
        return results

    async def _check_channel_adapters(self) -> list[ComponentHealth]:
        from keprix.gateway.adapter_registry import get_active_adapters

        results: list[ComponentHealth] = []
        for adapter in get_active_adapters():
            t0 = time.monotonic()
            try:
                await adapter.health_check()
                results.append(
                    ComponentHealth(
                        name=f"channel:{adapter.name}",
                        status="healthy",
                        latency_ms=(time.monotonic() - t0) * 1000,
                        error="",
                        checked_at=time.time(),
                    )
                )
            except Exception as exc:
                results.append(
                    ComponentHealth(
                        name=f"channel:{adapter.name}",
                        status="down",
                        latency_ms=0,
                        error=str(exc)[:200],
                        checked_at=time.time(),
                    )
                )
        return results

    async def _check_credential_proxy(self) -> list[ComponentHealth]:
        from keprix.proxy.cordon_bridge import CordonHealthCheck

        return [await CordonHealthCheck().check()]

    def get_all(self) -> dict[str, ComponentHealth]:
        return dict(self._results)


_GLOBAL_MONITOR: ConfigHealthMonitor | None = None


def get_health_monitor() -> ConfigHealthMonitor:
    global _GLOBAL_MONITOR
    if _GLOBAL_MONITOR is None:
        _GLOBAL_MONITOR = ConfigHealthMonitor()
    return _GLOBAL_MONITOR
