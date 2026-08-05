"""Data residency: restrict which providers are allowed based on geography."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Region(str, Enum):
    EU   = "eu"
    US   = "us"
    UK   = "uk"
    APAC = "apac"
    ANY  = "any"    # no restriction


# Providers known to host data in specific regions.
# "any" means the provider operates globally with no single-region guarantee.
_PROVIDER_REGIONS: dict[str, list[Region]] = {
    "anthropic":    [Region.US],
    "openai":       [Region.US, Region.EU],
    "mistral":      [Region.EU],
    "groq":         [Region.US],
    "google":       [Region.US, Region.EU, Region.APAC],
    "gemini":       [Region.US, Region.EU, Region.APAC],
    "ollama":       [Region.ANY],       # self-hosted, operator-controlled
    "lm_studio":    [Region.ANY],
    "deepseek":     [Region.APAC],
    "xai":          [Region.US],
    "openrouter":   [Region.ANY],
    "pollinations": [Region.US],
    "together":     [Region.US],
    "fireworks":    [Region.US],
    "cohere":       [Region.US, Region.EU],
}


@dataclass
class ResidencyViolation:
    provider: str
    required: Region
    available: list[Region]


class DataResidencyPolicy:
    """Filter providers by data residency requirement.

    Tenants in regulated environments specify a ``required_region``.
    Any provider not certified for that region is excluded from the
    candidate list before routing.

    Self-hosted providers (ollama, lm_studio) are always allowed because
    the operator controls where the data lives.

    Usage::

        policy = DataResidencyPolicy(required_region=Region.EU)
        allowed = policy.filter_providers(["openai", "mistral", "groq"])
        # -> ["openai", "mistral"]  (groq is US-only)
    """

    def __init__(
        self,
        required_region: Region = Region.ANY,
        custom_map: dict[str, list[Region]] | None = None,
    ) -> None:
        self._required = required_region
        self._map = {**_PROVIDER_REGIONS, **(custom_map or {})}

    @property
    def required_region(self) -> Region:
        return self._required

    def is_allowed(self, provider: str) -> bool:
        """Return True if the provider satisfies the residency requirement."""
        if self._required == Region.ANY:
            return True
        regions = self._map.get(provider, [Region.ANY])
        if Region.ANY in regions:
            return True
        return self._required in regions

    def filter_providers(self, providers: list[str]) -> list[str]:
        """Return only the providers that satisfy the residency requirement."""
        allowed = [p for p in providers if self.is_allowed(p)]
        blocked = [p for p in providers if not self.is_allowed(p)]
        if blocked:
            logger.debug(
                "Data residency (%s): blocked %s", self._required.value, blocked
            )
        return allowed

    def violations(self, providers: list[str]) -> list[ResidencyViolation]:
        """Return a list of violations for diagnostic/audit purposes."""
        result = []
        for p in providers:
            if not self.is_allowed(p):
                result.append(ResidencyViolation(
                    provider=p,
                    required=self._required,
                    available=self._map.get(p, [Region.ANY]),
                ))
        return result

    def compliant_regions(self, provider: str) -> list[Region]:
        """Return the region(s) a provider is certified for."""
        return self._map.get(provider, [Region.ANY])
