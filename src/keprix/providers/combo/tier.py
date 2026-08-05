"""Tier and combo definitions for smart provider routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProviderCandidate:
    provider_id: str
    model: str | None = None
    account_id: str = "default"
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ComboTier:
    id: str
    name: str
    providers: list[ProviderCandidate]
    max_concurrent: int = 1
    cooldown_seconds: int = 30

    @classmethod
    def from_config(cls, data: dict[str, Any]) -> "ComboTier":
        providers: list[ProviderCandidate] = []
        for raw in data.get("providers", []):
            if isinstance(raw, str):
                providers.append(ProviderCandidate(provider_id=raw))
            elif isinstance(raw, dict):
                providers.append(
                    ProviderCandidate(
                        provider_id=str(raw["id"] if "id" in raw else raw.get("provider")),
                        model=raw.get("model"),
                        account_id=str(raw.get("account_id") or "default"),
                        weight=float(raw.get("weight", 1.0)),
                        metadata={k: v for k, v in raw.items() if k not in {"id", "provider", "model", "account_id", "weight"}},
                    )
                )
        return cls(
            id=str(data["id"]),
            name=str(data.get("name") or data["id"]),
            providers=providers,
            max_concurrent=int(data.get("max_concurrent") or 1),
            cooldown_seconds=int(data.get("cooldown_seconds") or 30),
        )


@dataclass
class ProviderCombo:
    id: str
    name: str
    tiers: list[ComboTier]
    description: str = ""
    extends: str | None = None

    @classmethod
    def from_config(cls, data: dict[str, Any]) -> "ProviderCombo":
        return cls(
            id=str(data["id"]),
            name=str(data.get("name") or data["id"]),
            description=str(data.get("description") or ""),
            extends=data.get("extends"),
            tiers=[ComboTier.from_config(tier) for tier in data.get("tiers", [])],
        )
