"""Request metrics: counters, latency histograms, per-provider aggregates."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RequestMetric:
    provider: str
    model: str
    combo_id: str
    success: bool
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    pii_masked: bool = False
    injection_detected: bool = False
    compression_savings_pct: float = 0.0
    at: float = field(default_factory=time.time)


@dataclass
class ProviderSummary:
    provider: str
    total_requests: int
    success_count: int
    error_count: int
    avg_latency_ms: float
    p99_latency_ms: float
    total_tokens: int
    success_rate: float


class MetricsCollector:
    """In-memory rolling metrics window.

    Stores the last ``window`` requests per provider for percentile
    calculations. Suitable for dashboards and health endpoints; for
    long-term retention, export to Prometheus / InfluxDB / Clickhouse.

    Usage::

        collector = MetricsCollector(window=1000)
        collector.record(RequestMetric(provider="anthropic", ...))
        summary = collector.summary("anthropic")
        all_summaries = collector.all_summaries()
    """

    def __init__(self, window: int = 500) -> None:
        self._window = window
        self._metrics: dict[str, deque[RequestMetric]] = defaultdict(
            lambda: deque(maxlen=window)
        )
        self._lock = asyncio.Lock()
        self._totals: dict[str, dict[str, int]] = defaultdict(lambda: {
            "requests": 0, "successes": 0, "errors": 0, "tokens": 0
        })

    async def record(self, metric: RequestMetric) -> None:
        async with self._lock:
            self._metrics[metric.provider].append(metric)
            t = self._totals[metric.provider]
            t["requests"] += 1
            t["tokens"] += metric.prompt_tokens + metric.completion_tokens
            if metric.success:
                t["successes"] += 1
            else:
                t["errors"] += 1

    def summary(self, provider: str) -> ProviderSummary | None:
        window = list(self._metrics.get(provider, []))
        if not window:
            return None
        latencies = sorted(m.latency_ms for m in window)
        n = len(latencies)
        avg = sum(latencies) / n
        p99 = latencies[int(n * 0.99)] if n >= 100 else latencies[-1]
        totals = self._totals[provider]
        total = totals["requests"]
        return ProviderSummary(
            provider=provider,
            total_requests=total,
            success_count=totals["successes"],
            error_count=totals["errors"],
            avg_latency_ms=round(avg, 1),
            p99_latency_ms=round(p99, 1),
            total_tokens=totals["tokens"],
            success_rate=round(totals["successes"] / total, 4) if total else 0.0,
        )

    def all_summaries(self) -> list[ProviderSummary]:
        return [s for p in list(self._metrics) if (s := self.summary(p))]

    def global_stats(self) -> dict[str, Any]:
        summaries = self.all_summaries()
        if not summaries:
            return {"providers": 0, "total_requests": 0, "avg_latency_ms": 0}
        total_req = sum(s.total_requests for s in summaries)
        avg_lat = sum(s.avg_latency_ms * s.total_requests for s in summaries) / max(total_req, 1)
        return {
            "providers": len(summaries),
            "total_requests": total_req,
            "avg_latency_ms": round(avg_lat, 1),
            "total_tokens": sum(s.total_tokens for s in summaries),
        }
