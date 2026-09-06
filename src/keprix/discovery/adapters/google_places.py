"""Official Google Places Text Search adapter; never scrapes Maps."""

from __future__ import annotations

import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from keprix.discovery.models import AdapterHealth, AdapterHealthStatus, AdapterManifest, DiscoverLimits, DiscoverQuery, FieldProvenance, LeadCandidate


class GooglePlacesAdapter:
    name = "google_places"
    domain_packs = ["generic", "property", "health_social", "plumbing"]

    @property
    def manifest(self) -> AdapterManifest:
        return AdapterManifest(name=self.name, title="Google Places Text Search", description="Discover businesses using the official Google Places API.", licence_ref="https://developers.google.com/maps/terms", source_licence="Google Maps Platform terms", permitted_purpose="local_business_discovery_review", contact_use_eligible=False, outreach_allowed=False, rate_limit_per_minute=10, domain_packs=list(self.domain_packs), requires_env=["GOOGLE_PLACES_API_KEY"], docs_path="docs/features/discovery-google-places.md")

    def health(self) -> AdapterHealth:
        configured = bool(os.environ.get("GOOGLE_PLACES_API_KEY", "").strip())
        return AdapterHealth(name=self.name, status=AdapterHealthStatus.HEALTHY if configured else AdapterHealthStatus.DISABLED, message="Google Places API configured" if configured else "Google Places discovery is disabled until GOOGLE_PLACES_API_KEY is configured", configured=configured, enabled=configured)

    def cost_forecast(self, query: DiscoverQuery, limits: DiscoverLimits) -> dict:
        return {"units": 1.0, "currency": "google_places_requests"}

    def discover(self, query: DiscoverQuery, limits: DiscoverLimits) -> list[LeadCandidate]:
        key = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
        if not key:
            return []
        text = (query.text or query.params.get("query") or "").strip()
        if not text:
            raise ValueError("Google Places query is required")
        url = "https://places.googleapis.com/v1/places:searchText"
        body = json.dumps({"textQuery": text, "pageSize": max(1, min(int(limits.max_results or 20), 20))}).encode()
        request = Request(url, data=body, headers={"Content-Type": "application/json", "X-Goog-Api-Key": key, "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri,places.primaryType"}, method="POST")
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        out = []
        for item in payload.get("places") or []:
            name = ((item.get("displayName") or {}).get("text") or "").strip()
            place_id = str(item.get("id") or "").strip()
            if not name:
                continue
            website = str(item.get("websiteUri") or "").strip()
            out.append(LeadCandidate(company=name, urls=[website] if website else [], phones=[str(item["nationalPhoneNumber"]) ] if item.get("nationalPhoneNumber") else [], geo={"address": item.get("formattedAddress", ""), "category": item.get("primaryType", "")}, source=self.name, external_id=place_id or None, raw=item, domain_pack=query.domain_pack or "generic", provenance=[FieldProvenance(field="company", source=self.name, external_id=place_id or None)]))
        return out
