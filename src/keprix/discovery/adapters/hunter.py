"""Hunter.io domain email lookup adapter; missing results remain empty."""

from __future__ import annotations

import json
import os
from urllib.parse import urlencode
from urllib.request import urlopen

from keprix.discovery.models import AdapterHealth, AdapterHealthStatus, AdapterManifest, DiscoverLimits, DiscoverQuery, FieldProvenance, LeadCandidate


class HunterAdapter:
    name = "hunter"
    domain_packs = ["generic", "property", "health_social", "plumbing"]

    @property
    def manifest(self) -> AdapterManifest:
        return AdapterManifest(name=self.name, title="Hunter email enrichment", description="Find a probable business email for a known domain using Hunter.io.", licence_ref="https://hunter.io/api-documentation", source_licence="Hunter.io terms", permitted_purpose="contact_enrichment_review", contact_use_eligible=False, outreach_allowed=False, rate_limit_per_minute=20, domain_packs=list(self.domain_packs), requires_env=["HUNTER_API_KEY"], docs_path="docs/features/discovery-hunter.md")

    def health(self) -> AdapterHealth:
        configured = bool(os.environ.get("HUNTER_API_KEY", "").strip())
        return AdapterHealth(name=self.name, status=AdapterHealthStatus.HEALTHY if configured else AdapterHealthStatus.DISABLED, message="Hunter API configured" if configured else "Hunter enrichment is disabled until HUNTER_API_KEY is configured", configured=configured, enabled=configured)

    def cost_forecast(self, query: DiscoverQuery, limits: DiscoverLimits) -> dict:
        return {"units": 1.0, "currency": "hunter_api_requests"}

    def discover(self, query: DiscoverQuery, limits: DiscoverLimits) -> list[LeadCandidate]:
        key = os.environ.get("HUNTER_API_KEY", "").strip()
        domain = str(query.params.get("domain") or query.text or "").strip().lower().removeprefix("https://").removeprefix("http://").split("/", 1)[0]
        if not key or not domain:
            return []
        with urlopen("https://api.hunter.io/v2/domain-search?" + urlencode({"domain": domain, "api_key": key, "limit": 1}), timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        data = payload.get("data") or {}
        emails = [str(item.get("value")) for item in (data.get("emails") or []) if item.get("value")]
        return [LeadCandidate(company=str(data.get("organization") or domain), domain=domain, emails=emails[:1], urls=[f"https://{domain}"], source=self.name, external_id=domain, raw=data, domain_pack=query.domain_pack or "generic", provenance=[FieldProvenance(field="emails", source=self.name, external_id=domain)])]
