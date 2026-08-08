"""Web / directory discovery via configured search backends (SearxNG etc.)."""

from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib.parse import urlparse

from keprix.discovery.models import (
    AdapterHealth,
    AdapterHealthStatus,
    AdapterManifest,
    DiscoverLimits,
    DiscoverQuery,
    FieldProvenance,
    LeadCandidate,
)

# Query templates per domain pack. Operators can still pass free-text query.
QUERY_TEMPLATES: dict[str, str] = {
    "generic": "{query}",
    "plumbing": "plumbers in {location}",
    "property": "estate agents in {location}",
    "health_social": "care homes in {location}",
    "healthcare": "clinics in {location}",
    "care": "care providers in {location}",
}


_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?44|0)\s*\d[\d\s\-()]{8,}")


class WebDirectoryAdapter:
    name = "web_directory"
    domain_packs = ["generic", "plumbing", "property", "health_social", "care"]

    @property
    def manifest(self) -> AdapterManifest:
        return AdapterManifest(
            name=self.name,
            title="Web / directory search",
            description=(
                "Discover businesses via configured search (SearxNG / web_search). "
                "Homepage fetch is off by default and Soft Wall gated."
            ),
            licence_ref="search-backend-terms",
            source_licence="Depends on configured search backend; respect robots.txt on fetch",
            permitted_purpose="directory_discovery_review",
            contact_use_eligible=False,
            outreach_allowed=False,
            rate_limit_per_minute=20,
            domain_packs=list(self.domain_packs),
            docs_path="docs/features/discovery-web-directory.md",
        )

    def health(self) -> AdapterHealth:
        backend = os.environ.get("WEB_SEARCH_BACKEND") or os.environ.get("KEPRIX_WEB_SEARCH_BACKEND") or ""
        searx = os.environ.get("SEARXNG_URL", "").strip()
        # Honest degrade: adapter works with injected results; live search needs backend.
        configured = bool(backend or searx)
        if configured:
            return AdapterHealth(
                name=self.name,
                status=AdapterHealthStatus.HEALTHY,
                message=f"Search backend hint present ({backend or 'searxng'})",
                configured=True,
                enabled=True,
                details={"backend": backend or "searxng", "searxng_url_set": bool(searx)},
            )
        return AdapterHealth(
            name=self.name,
            status=AdapterHealthStatus.DEGRADED,
            message=(
                "No search backend configured. Adapter accepts injected search_results "
                "or will attempt web_search and degrade honestly if unavailable."
            ),
            configured=False,
            enabled=True,
            details={"backend": None},
        )

    def cost_forecast(self, query: DiscoverQuery, limits: DiscoverLimits) -> dict[str, Any]:
        fetches = limits.max_fetches if limits.allow_homepage_fetch else 0
        return {
            "units": float(limits.max_pages + fetches),
            "currency": "search_pages_plus_fetches",
            "homepage_fetch_enabled": limits.allow_homepage_fetch,
            "note": "Homepage fetch disabled by default until Soft Wall approve",
        }

    def discover(self, query: DiscoverQuery, limits: DiscoverLimits) -> list[LeadCandidate]:
        search_query = self._build_query(query)
        results = query.params.get("search_results")
        if results is None:
            results = self._live_search(search_query, limit=min(limits.max_results, limits.max_pages * 10))
        if isinstance(results, str):
            try:
                results = json.loads(results)
            except json.JSONDecodeError:
                results = []
        if not isinstance(results, list):
            results = []

        allow_fetch = bool(limits.allow_homepage_fetch and query.params.get("approve_homepage_fetch"))
        max_fetches = int(limits.max_fetches or 0) if allow_fetch else 0
        fetches_done = 0
        out: list[LeadCandidate] = []

        for idx, item in enumerate(results):
            if len(out) >= limits.max_results:
                break
            if not isinstance(item, dict):
                continue
            title = item.get("title") or item.get("name")
            url = item.get("url") or item.get("link") or item.get("href")
            snippet = item.get("snippet") or item.get("content") or item.get("description") or ""
            if not title and not url:
                continue
            emails: list[str] = []
            phones: list[str] = []
            raw: dict[str, Any] = {"search": item, "query": search_query}
            if url and fetches_done < max_fetches:
                fetched = self._fetch_homepage(str(url))
                fetches_done += 1
                raw["homepage_fetch"] = fetched
                if fetched.get("allowed"):
                    body = str(fetched.get("text") or "")
                    emails = list(dict.fromkeys(_EMAIL_RE.findall(body)))[:5]
                    phones = list(dict.fromkeys(p.strip() for p in _PHONE_RE.findall(body)))[:5]
                elif fetched.get("error"):
                    raw["fetch_error"] = fetched.get("error")

            domain = None
            if url:
                try:
                    domain = urlparse(str(url)).netloc or None
                except Exception:  # noqa: BLE001
                    domain = None
            external_id = str(url or f"web-{idx}")
            out.append(
                LeadCandidate(
                    company=str(title) if title else domain,
                    contacts=[{"email": e} for e in emails],
                    urls=[str(url)] if url else [],
                    geo={"location": query.params.get("location")} if query.params.get("location") else {},
                    source=self.name,
                    external_id=external_id,
                    raw=raw,
                    score_hint=0.5,
                    emails=emails,
                    phones=phones,
                    domain=domain,
                    notes=str(snippet)[:500] if snippet else None,
                    domain_pack=query.domain_pack or "generic",
                    provenance=[
                        FieldProvenance(field="company", source=self.name, external_id=external_id),
                        FieldProvenance(field="urls", source=self.name, external_id=external_id),
                    ],
                )
            )
        return out

    def _build_query(self, query: DiscoverQuery) -> str:
        pack = query.domain_pack or "generic"
        location = str(query.params.get("location") or "").strip()
        text = (query.text or query.params.get("q") or "").strip()
        template = QUERY_TEMPLATES.get(pack) or QUERY_TEMPLATES["generic"]
        if text and "{query}" in template:
            return template.format(query=text, location=location or "UK")
        if location and "{location}" in template and not text:
            return template.format(location=location, query=location)
        if text:
            return text
        if location:
            return template.format(location=location, query=location)
        return "businesses UK"

    def _live_search(self, query: str, *, limit: int) -> list[dict[str, Any]]:
        try:
            from keprix.tools.web_tools import web_search_tool

            raw = web_search_tool(query, limit=limit)
            data = json.loads(raw) if isinstance(raw, str) else raw
        except Exception as exc:  # noqa: BLE001 - honest degrade
            return [
                {
                    "title": None,
                    "url": None,
                    "snippet": f"web_search unavailable: {exc}",
                    "error": "search_unavailable",
                }
            ]
        if isinstance(data, dict):
            if data.get("error"):
                return [{"title": None, "url": None, "snippet": str(data.get("error")), "error": "search_error"}]
            items = data.get("results") or data.get("items") or data.get("organic") or []
            if isinstance(items, list):
                return [i for i in items if isinstance(i, dict)]
        if isinstance(data, list):
            return [i for i in data if isinstance(i, dict)]
        return []

    def _fetch_homepage(self, url: str) -> dict[str, Any]:
        """Egress-aware homepage fetch. Never silently bypasses allowlist."""
        try:
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower()
            if not host:
                return {"allowed": False, "error": "invalid_url"}
            from keprix.security.egress_policy import get_egress_policy

            policy = get_egress_policy()
            # Host allowlist check (IP unknown pre-DNS); use public placeholder IP.
            decision = policy.is_allowed("keprix", host, "1.1.1.1")
            if not getattr(decision, "allowed", False):
                return {
                    "allowed": False,
                    "error": "egress_denied",
                    "reason": getattr(decision, "reason", "host_not_in_allowlist"),
                    "host": host,
                }
            # Soft robots respect: skip obvious disallow patterns; full robots parser Nice.
            if any(part in parsed.path.lower() for part in ("/admin", "/login", "/wp-admin")):
                return {"allowed": False, "error": "robots_heuristic_block", "host": host}

            from keprix.http_client import get_http_client

            # Sync-friendly: use httpx via client helper when available.
            import asyncio
            import concurrent.futures

            async def _get() -> str:
                async with get_http_client(product_id="keprix", timeout=15.0) as client:
                    resp = await client.get(url)
                    if resp.status_code >= 400:
                        return ""
                    return resp.text[:50_000]

            try:
                asyncio.get_running_loop()
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    text = pool.submit(asyncio.run, _get()).result()
            except RuntimeError:
                text = asyncio.run(_get())
            return {"allowed": True, "text": text, "host": host}
        except Exception as exc:  # noqa: BLE001
            return {"allowed": False, "error": str(exc)}
