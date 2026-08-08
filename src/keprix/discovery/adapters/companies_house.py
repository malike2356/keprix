"""Companies House discovery adapter (wraps integrations/companies_house)."""

from __future__ import annotations

import asyncio
import concurrent.futures
from datetime import datetime
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
from keprix.integrations.companies_house.config import is_configured, is_enabled, status_payload
from keprix.integrations.companies_house.errors import CompaniesHouseConfigError, CompaniesHouseError


def _run_async(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def _score_hint(item: dict[str, Any]) -> float:
    score = 0.4
    status = str(item.get("company_status") or "").lower()
    if status == "active":
        score += 0.35
    elif status:
        score += 0.05
    if item.get("address_snippet"):
        score += 0.15
    created = item.get("date_of_creation")
    if created:
        try:
            year = int(str(created)[:4])
            age = max(0, datetime.utcnow().year - year)
            if age >= 2:
                score += 0.1
            elif age >= 1:
                score += 0.05
        except ValueError:
            pass
    return round(min(score, 1.0), 3)


class CompaniesHouseAdapter:
    name = "companies_house"
    domain_packs = ["generic", "property", "health_social", "plumbing"]

    @property
    def manifest(self) -> AdapterManifest:
        return AdapterManifest(
            name=self.name,
            title="UK Companies House",
            description="Search UK companies via the Companies House Public Data API.",
            licence_ref="https://www.gov.uk/government/publications/companies-house-data-products/companies-house-data-products",
            source_licence="Companies House Open Government Licence / API terms",
            permitted_purpose="company_discovery_review",
            allowed_fields=["company", "company_number", "geo", "urls", "raw"],
            retention="workspace_policy",
            jurisdiction="UK",
            contact_use_eligible=False,
            outreach_allowed=False,
            rate_limit_per_minute=20,
            domain_packs=list(self.domain_packs),
            requires_env=["COMPANIES_HOUSE_API_KEY"],
            docs_path="docs/features/companies-house.md",
        )

    def health(self) -> AdapterHealth:
        snap = status_payload()
        if not is_enabled():
            return AdapterHealth(
                name=self.name,
                status=AdapterHealthStatus.DISABLED,
                message="Companies House disabled (KEPRIX_COMPANIES_HOUSE_ENABLED)",
                configured=is_configured(),
                enabled=False,
                details=snap,
            )
        if not is_configured():
            return AdapterHealth(
                name=self.name,
                status=AdapterHealthStatus.NOT_CONFIGURED,
                message="Set COMPANIES_HOUSE_API_KEY to enable Companies House discovery",
                configured=False,
                enabled=True,
                details=snap,
            )
        return AdapterHealth(
            name=self.name,
            status=AdapterHealthStatus.HEALTHY,
            message="Companies House API key configured",
            configured=True,
            enabled=True,
            details=snap,
        )

    def cost_forecast(self, query: DiscoverQuery, limits: DiscoverLimits) -> dict[str, Any]:
        return {
            "units": float(min(limits.max_results, 50)),
            "currency": "ch_api_calls",
            "note": "One search page call; profile fetches not included by default",
        }

    def discover(self, query: DiscoverQuery, limits: DiscoverLimits) -> list[LeadCandidate]:
        from keprix.integrations.companies_house.client import CompaniesHouseClient

        q = (query.text or query.params.get("q") or "").strip()
        keywords = query.params.get("keywords")
        if keywords and not q:
            q = str(keywords)
        sic = query.params.get("sic") or query.params.get("sic_codes")
        location = query.params.get("location")
        status_filter = str(query.params.get("status") or "active").lower()
        if location and location.lower() not in q.lower():
            q = f"{q} {location}".strip()
        if sic and str(sic) not in q:
            q = f"{q} {sic}".strip()
        if not q:
            raise CompaniesHouseConfigError("Companies House query (keywords/SIC/location) is required")

        page_size = max(1, min(int(limits.max_results or 20), 100))
        try:
            result = _run_async(
                CompaniesHouseClient().search_companies(q, items_per_page=page_size)
            )
        except CompaniesHouseError:
            raise

        out: list[LeadCandidate] = []
        for item in result.get("items") or []:
            if not isinstance(item, dict):
                continue
            status = str(item.get("company_status") or "").lower()
            if status_filter and status_filter not in {"any", "*", "all"}:
                if status != status_filter:
                    continue
            number = str(item.get("company_number") or "").strip().upper() or None
            title = item.get("title") or item.get("company_name")
            addr = item.get("address_snippet")
            geo: dict[str, Any] = {}
            if addr:
                geo["address_snippet"] = addr
            if location:
                geo["query_location"] = location
            urls = []
            if item.get("public_url"):
                urls.append(str(item["public_url"]))
            out.append(
                LeadCandidate(
                    company=str(title) if title else None,
                    company_number=number,
                    contacts=[],
                    urls=urls,
                    geo=geo,
                    source=self.name,
                    external_id=number,
                    raw=dict(item),
                    score_hint=_score_hint(item),
                    domain_pack=query.domain_pack or "generic",
                    provenance=[
                        FieldProvenance(
                            field="company",
                            source=self.name,
                            external_id=number,
                        ),
                        FieldProvenance(
                            field="company_number",
                            source=self.name,
                            external_id=number,
                        ),
                    ],
                )
            )
            if len(out) >= limits.max_results:
                break
        return out
