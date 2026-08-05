"""Managed AI credit pricing.

1 credit = 1 US cent of charged value.
Charged value = provider cost USD x markup, rounded up to whole credits.
Unknown models use a conservative high fallback so Keprix never undercharges.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

# Charged = provider cost x this factor.
AI_MARKUP = Decimal("2")

# USD per 1,000,000 tokens {input, output}. Keep conservative.
_MODEL_PRICING: dict[str, tuple[Decimal, Decimal]] = {
    "claude-haiku": (Decimal("1.0"), Decimal("5.0")),
    "claude-sonnet": (Decimal("3.0"), Decimal("15.0")),
    "claude-opus": (Decimal("5.0"), Decimal("25.0")),
    "gpt-4o-mini": (Decimal("0.15"), Decimal("0.6")),
    "gpt-4o": (Decimal("2.5"), Decimal("10.0")),
    "gpt-4.1-mini": (Decimal("0.4"), Decimal("1.6")),
    "gpt-4.1": (Decimal("2.0"), Decimal("8.0")),
    "o4-mini": (Decimal("1.1"), Decimal("4.4")),
    "o3": (Decimal("10.0"), Decimal("40.0")),
}

# Most expensive known tier; used when the model is unknown.
FALLBACK_PRICING: tuple[Decimal, Decimal] = (Decimal("10.0"), Decimal("50.0"))

_ONE_MILLION = Decimal("1000000")


@dataclass(frozen=True)
class CreditQuote:
    credits: int
    provider_cost_usd: Decimal
    charged_usd: Decimal
    pricing_source: str  # "catalog" | "fallback"
    input_rate: Decimal
    output_rate: Decimal


def pricing_for(model: str | None) -> tuple[Decimal, Decimal, str]:
    """Return (input_per_m, output_per_m, source) for a model id."""
    m = str(model or "").lower().strip()
    if not m:
        return (*FALLBACK_PRICING, "fallback")

    for key, rates in _MODEL_PRICING.items():
        if key in m:
            return (*rates, "catalog")

    if "haiku" in m:
        return (*_MODEL_PRICING["claude-haiku"], "catalog")
    if "sonnet" in m:
        return (*_MODEL_PRICING["claude-sonnet"], "catalog")
    if "opus" in m:
        return (*_MODEL_PRICING["claude-opus"], "catalog")
    if "mini" in m:
        return (*_MODEL_PRICING["gpt-4o-mini"], "catalog")

    return (*FALLBACK_PRICING, "fallback")


def raw_cost_usd(
    model: str | None,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> tuple[Decimal, str, Decimal, Decimal]:
    in_rate, out_rate, source = pricing_for(model)
    cost = (Decimal(max(0, int(input_tokens))) / _ONE_MILLION) * in_rate + (
        Decimal(max(0, int(output_tokens))) / _ONE_MILLION
    ) * out_rate
    return cost, source, in_rate, out_rate


def credits_for_usage(
    model: str | None,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    markup: Decimal | None = None,
) -> CreditQuote:
    """Whole credits charged for a managed run (minimum 1 when any tokens used)."""
    factor = markup if markup is not None else AI_MARKUP
    provider_cost, source, in_rate, out_rate = raw_cost_usd(
        model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    charged = provider_cost * factor
    tokens = max(0, int(input_tokens)) + max(0, int(output_tokens))
    if tokens <= 0 and charged <= 0:
        credits = 0
    else:
        credits = max(1, int(math.ceil(float(charged * 100))))
    return CreditQuote(
        credits=credits,
        provider_cost_usd=provider_cost,
        charged_usd=charged,
        pricing_source=source,
        input_rate=in_rate,
        output_rate=out_rate,
    )


def estimate_credits_for_tokens(model: str | None, estimated_tokens: int) -> int:
    """Pre-flight estimate treating all tokens as input (conservative for gating)."""
    est = max(0, int(estimated_tokens))
    if est <= 0:
        return 1
    # Assume a small output so we do not under-reserve.
    quote = credits_for_usage(model, input_tokens=est, output_tokens=max(64, est // 8))
    return max(1, quote.credits)


def quote_to_dict(quote: CreditQuote) -> dict[str, Any]:
    return {
        "credits": quote.credits,
        "provider_cost_usd": float(quote.provider_cost_usd),
        "charged_usd": float(quote.charged_usd),
        "pricing_source": quote.pricing_source,
        "input_rate_per_million": float(quote.input_rate),
        "output_rate_per_million": float(quote.output_rate),
        "markup": float(AI_MARKUP),
    }
