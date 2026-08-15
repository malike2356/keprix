"""Bounded recursive model calls with an injected provider function."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable


@dataclass
class RlmBudget:
    max_depth: int = 3
    max_calls: int = 8
    max_output_tokens: int = 2000
    calls: int = 0
    output_tokens: int = 0

    def allow(self, depth: int) -> bool:
        return depth <= self.max_depth and self.calls < self.max_calls and self.output_tokens < self.max_output_tokens


@dataclass
class RlmResult:
    ok: bool
    value: Any
    depth: int
    model: str
    calls: int
    truncated: bool = False


ProviderCall = Callable[[str, list[dict[str, Any]], str, int], Awaitable[Any]]


class RecursiveModel:
    def __init__(self, provider_call: ProviderCall, *, model: str, leaf_model: str | None = None, budget: RlmBudget | None = None) -> None:
        self.provider_call = provider_call
        self.model = model
        self.leaf_model = leaf_model or model
        self.budget = budget or RlmBudget()

    async def call(self, context_subset: list[dict[str, Any]], instruction: str, *, depth: int = 0, model: str | None = None) -> RlmResult:
        if not self.budget.allow(depth):
            return RlmResult(ok=False, value={"error": "rlm_budget_exhausted"}, depth=depth, model=model or self.model, calls=self.budget.calls, truncated=True)
        selected_model = model or (self.leaf_model if depth >= self.budget.max_depth else self.model)
        self.budget.calls += 1
        value = await self.provider_call(selected_model, list(context_subset), instruction, depth)
        text = str(value)
        remaining = max(0, self.budget.max_output_tokens - self.budget.output_tokens)
        if len(text) > remaining * 4:
            value = text[: remaining * 4]
            truncated = True
        else:
            truncated = False
        self.budget.output_tokens += min(remaining, max(1, len(str(value)) // 4))
        return RlmResult(ok=True, value=value, depth=depth, model=selected_model, calls=self.budget.calls, truncated=truncated)
