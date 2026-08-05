"""Composite tier ordering helpers."""

from __future__ import annotations

from keprix.providers.combo.tier import ProviderCombo


class CompositeTierPlanner:
    def order_tiers(self, combo: ProviderCombo, strategy: str | None = None) -> list:
        tiers = list(combo.tiers)
        if strategy in {"fast", "auto/fast"}:
            return tiers
        if strategy in {"local", "fallback"}:
            return sorted(tiers, key=lambda tier: 0 if tier.id == "fallback" else 1)
        if strategy in {"paid", "quality"}:
            return sorted(tiers, key=lambda tier: 0 if tier.id in {"subscription", "api_keys"} else 1)
        return tiers
