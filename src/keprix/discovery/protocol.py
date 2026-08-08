"""Discovery adapter protocol."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from keprix.discovery.models import (
    AdapterHealth,
    AdapterManifest,
    DiscoverLimits,
    DiscoverQuery,
    LeadCandidate,
)


@runtime_checkable
class DiscoveryAdapter(Protocol):
    """Pluggable discovery adapter.

    Discovery produces candidates only. Contactability is a separate policy.
    """

    @property
    def name(self) -> str: ...

    @property
    def domain_packs(self) -> list[str]: ...

    @property
    def manifest(self) -> AdapterManifest: ...

    def discover(self, query: DiscoverQuery, limits: DiscoverLimits) -> list[LeadCandidate]: ...

    def health(self) -> AdapterHealth: ...

    def cost_forecast(self, query: DiscoverQuery, limits: DiscoverLimits) -> dict[str, Any]:
        """Optional cost estimate. Default adapters may return a simple forecast."""
        ...
