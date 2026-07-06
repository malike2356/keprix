"""Bridge to agent usage pricing (no duplicated rate tables)."""

from __future__ import annotations

from typing import Any

from agent.usage_pricing import CanonicalUsage, CostResult, estimate_usage_cost


def estimate_llm_cost(
    *,
    usage: CanonicalUsage,
    model: str,
    provider: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> CostResult:
    return estimate_usage_cost(
        model,
        usage,
        provider=provider,
        base_url=base_url,
        api_key=api_key or "",
    )


def usage_from_response(response: Any) -> CanonicalUsage:
    from agent.usage_pricing import normalize_usage

    raw = getattr(response, "usage", None)
    if raw is None:
        return CanonicalUsage()
    if isinstance(raw, dict):
        return normalize_usage(raw)
    payload = {
        "input_tokens": getattr(raw, "input_tokens", None) or getattr(raw, "prompt_tokens", 0),
        "output_tokens": getattr(raw, "output_tokens", None) or getattr(raw, "completion_tokens", 0),
        "cache_read_tokens": getattr(raw, "cache_read_input_tokens", None)
        or getattr(raw, "cache_read_tokens", 0),
        "cache_write_tokens": getattr(raw, "cache_creation_input_tokens", None)
        or getattr(raw, "cache_write_tokens", 0),
        "reasoning_tokens": getattr(raw, "reasoning_tokens", 0),
        "total_tokens": getattr(raw, "total_tokens", 0),
    }
    return normalize_usage(payload)


def list_pricing_catalog() -> list[dict[str, Any]]:
    from agent.usage_pricing import _OFFICIAL_DOCS_PRICING

    items: list[dict[str, Any]] = []
    for (provider, model), entry in _OFFICIAL_DOCS_PRICING.items():
        items.append(
            {
                "provider": provider,
                "model": model,
                "input_cost_per_million": float(entry.input_cost_per_million)
                if entry.input_cost_per_million is not None
                else None,
                "output_cost_per_million": float(entry.output_cost_per_million)
                if entry.output_cost_per_million is not None
                else None,
                "source": entry.source,
            }
        )
    return sorted(items, key=lambda row: (row["provider"], row["model"]))


def usage_from_counts(
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
    reasoning_tokens: int = 0,
) -> CanonicalUsage:
    return CanonicalUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read_tokens,
        cache_write_tokens=cache_write_tokens,
        reasoning_tokens=reasoning_tokens,
    )
