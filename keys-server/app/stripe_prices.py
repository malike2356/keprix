"""Stripe price ID to product tier mapping for keys.petraclus.uk (Petraclus only)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PriceMapping:
    product: str
    tier: str
    interval: str


def _env(key: str) -> str | None:
    value = os.getenv(key, "").strip()
    return value or None


def build_price_map() -> dict[str, PriceMapping]:
    entries: list[tuple[str, PriceMapping]] = []
    pairs = [
        ("STRIPE_PRICE_PETRA_PRO_MONTHLY", "petraclus", "PRO", "month"),
        ("STRIPE_PRICE_PETRA_PRO_ANNUAL", "petraclus", "PRO", "year"),
        ("STRIPE_PRICE_PETRA_TEAM_MONTHLY", "petraclus", "TEAM", "month"),
        ("STRIPE_PRICE_PETRA_TEAM_ANNUAL", "petraclus", "TEAM", "year"),
    ]
    for env_key, product, tier, interval in pairs:
        price_id = _env(env_key)
        if price_id:
            entries.append((price_id, PriceMapping(product=product, tier=tier, interval=interval)))
    return dict(entries)
