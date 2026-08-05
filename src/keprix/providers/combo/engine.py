"""Combo routing engine with quota-aware fallback."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from keprix.providers.combo.auto_promote import AutoPromoter
from keprix.providers.combo.composite import CompositeTierPlanner
from keprix.providers.combo.explain import RouteExplanation
from keprix.providers.combo.health import HealthMonitor
from keprix.providers.combo.tier import ProviderCombo
from keprix.providers.fallback.circuit_breaker import CircuitBreaker
from keprix.providers.fallback.error_handler import AllProvidersExhausted, classify_error
from keprix.providers.quota.tracker import QuotaTracker

ProviderCallable = Callable[..., Awaitable[Any]]


@dataclass
class ComboRouteResult:
    response: Any
    provider: str
    model: str | None
    explanation: RouteExplanation


class ComboEngine:
    """Routes requests through tiered provider combos with automatic fallback."""

    def __init__(
        self,
        combos: dict[str, ProviderCombo],
        providers: dict[str, ProviderCallable],
        *,
        quota: QuotaTracker | None = None,
        health: HealthMonitor | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        default_combo: str = "default",
    ) -> None:
        self.combos = combos
        self.providers = providers
        self.quota = quota or QuotaTracker()
        self.health = health or HealthMonitor()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.default_combo = default_combo
        self.promoter = AutoPromoter(self.health, self.quota)
        self.planner = CompositeTierPlanner()

    def get(self, combo_id: str | None = None) -> ProviderCombo:
        resolved = combo_id or self.default_combo
        if resolved not in self.combos:
            raise KeyError(f"Unknown provider combo: {resolved}")
        return self.combos[resolved]

    async def route(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str = "auto",
        strategy: str | None = None,
        combo_id: str | None = None,
        estimated_tokens: int = 0,
        **kwargs: Any,
    ) -> ComboRouteResult:
        combo = self.get(combo_id)
        explanation = RouteExplanation(combo_id=combo.id, strategy=strategy, metadata={"model": model})
        last_error: Exception | None = None
        tried = 0

        for tier in self.planner.order_tiers(combo, strategy):
            ordered = await self.promoter.order(tier, estimated_tokens=estimated_tokens)
            if not ordered:
                explanation.add("*", tier.id, "skipped", "no healthy provider with quota")
                continue
            for candidate in ordered:
                provider_id = candidate.provider_id
                handler = self.providers.get(provider_id)
                if handler is None:
                    explanation.add(provider_id, tier.id, "skipped", "provider handler missing")
                    continue
                if not self.circuit_breaker.allow(provider_id):
                    explanation.add(provider_id, tier.id, "skipped", "circuit open")
                    continue
                tried += 1
                started = time.perf_counter()
                try:
                    response = await handler(
                        messages=messages,
                        model=candidate.model or (None if model == "auto" else model),
                        provider=provider_id,
                        **kwargs,
                    )
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    self.health.record_success(provider_id, latency_ms)
                    self.circuit_breaker.record_success(provider_id)
                    usage_tokens = self._extract_usage_tokens(response) or estimated_tokens
                    await self.quota.record_usage(provider_id, usage_tokens, account_id=candidate.account_id)
                    explanation.selected_provider = provider_id
                    explanation.selected_tier = tier.id
                    explanation.add(provider_id, tier.id, "success", latency_ms=latency_ms)
                    return ComboRouteResult(response=response, provider=provider_id, model=candidate.model, explanation=explanation)
                except Exception as exc:
                    last_error = exc
                    reason = classify_error(exc)
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    if reason == "quota":
                        await self.quota.mark_exhausted(provider_id, account_id=candidate.account_id)
                    opened = self.circuit_breaker.record_failure(provider_id)
                    self.health.record_failure(provider_id, cooldown_seconds=tier.cooldown_seconds)
                    explanation.add(provider_id, tier.id, "failed", f"{reason}{' circuit_open' if opened else ''}", latency_ms)
                    continue

        raise AllProvidersExhausted(
            "All providers in combo were exhausted",
            tried=tried,
            last_error=last_error,
            explanation=explanation.as_dict(),
        )

    def explain_combo(self, combo_id: str | None = None) -> dict[str, Any]:
        combo = self.get(combo_id)
        return {
            "id": combo.id,
            "name": combo.name,
            "description": combo.description,
            "tiers": [
                {
                    "id": tier.id,
                    "name": tier.name,
                    "providers": [
                        {
                            "id": candidate.provider_id,
                            "model": candidate.model,
                            "health_score": self.health.score(candidate.provider_id),
                        }
                        for candidate in tier.providers
                    ],
                }
                for tier in combo.tiers
            ],
        }

    @staticmethod
    def _extract_usage_tokens(response: Any) -> int | None:
        usage = getattr(response, "usage", None)
        if isinstance(response, dict):
            usage = response.get("usage")
        if usage is None:
            return None
        if isinstance(usage, dict):
            return int(usage.get("total_tokens") or usage.get("tokens") or 0)
        return int(getattr(usage, "total_tokens", 0) or 0)
