"""Fake discovery adapter for tests and local demos."""

from __future__ import annotations

from typing import Any

from keprix.discovery.models import (
    AdapterHealth,
    AdapterHealthStatus,
    AdapterManifest,
    DiscoverLimits,
    DiscoverQuery,
    FieldProvenance,
    LeadCandidate,
)


class FakeDiscoveryAdapter:
    name = "fake"
    domain_packs = ["generic"]

    def __init__(self, candidates: list[LeadCandidate] | None = None) -> None:
        self._candidates = candidates

    @property
    def manifest(self) -> AdapterManifest:
        return AdapterManifest(
            name=self.name,
            title="Fake discovery adapter",
            description="Deterministic adapter for tests. Never used for outreach.",
            licence_ref="internal-test",
            source_licence="test",
            permitted_purpose="testing",
            contact_use_eligible=False,
            outreach_allowed=False,
            rate_limit_per_minute=120,
            domain_packs=list(self.domain_packs),
        )

    def health(self) -> AdapterHealth:
        return AdapterHealth(
            name=self.name,
            status=AdapterHealthStatus.HEALTHY,
            message="Fake adapter always ready",
            configured=True,
            enabled=True,
        )

    def cost_forecast(self, query: DiscoverQuery, limits: DiscoverLimits) -> dict[str, Any]:
        return {"units": float(min(limits.max_results, 10)), "currency": "estimate", "note": "fake"}

    def discover(self, query: DiscoverQuery, limits: DiscoverLimits) -> list[LeadCandidate]:
        if self._candidates is not None:
            return list(self._candidates)[: limits.max_results]
        text = (query.text or "Acme").strip() or "Acme"
        out: list[LeadCandidate] = []
        for i in range(min(limits.max_results, 3)):
            company = f"{text} Co {i + 1}"
            out.append(
                LeadCandidate(
                    company=company,
                    contacts=[{"name": f"Contact {i + 1}", "email": f"c{i + 1}@example.com"}],
                    urls=[f"https://example.com/{i + 1}"],
                    geo={"locality": query.params.get("location") or "London"},
                    source=self.name,
                    external_id=f"fake-{i + 1}",
                    raw={"query": query.to_dict(), "index": i},
                    score_hint=0.9 - (i * 0.1),
                    emails=[f"c{i + 1}@example.com"],
                    domain="example.com",
                    domain_pack=query.domain_pack or "generic",
                    provenance=[
                        FieldProvenance(field="company", source=self.name, external_id=f"fake-{i + 1}")
                    ],
                )
            )
        return out
