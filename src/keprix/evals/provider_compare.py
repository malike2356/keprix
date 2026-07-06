"""Provider comparison from eval results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ProviderScore:
    provider: str
    pass_rate: float
    avg_cost_usd: float
    avg_latency_ms: float
    rank: int = 0


def compare_providers(results_by_provider: dict[str, dict[str, Any]]) -> list[ProviderScore]:
    scores: list[ProviderScore] = []
    for provider, payload in results_by_provider.items():
        scores.append(
            ProviderScore(
                provider=provider,
                pass_rate=float(payload.get("pass_rate", 0.0)),
                avg_cost_usd=float(payload.get("avg_cost_usd", 0.0)),
                avg_latency_ms=float(payload.get("avg_latency_ms", 0.0)),
            )
        )
    scores.sort(key=lambda item: (-item.pass_rate, item.avg_cost_usd, item.avg_latency_ms))
    for index, score in enumerate(scores, start=1):
        score.rank = index
    return scores
