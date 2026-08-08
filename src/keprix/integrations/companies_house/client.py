"""HTTP client for the Companies House Public Data API.

Auth: HTTP Basic with API key as username and empty password.
Docs: https://developer.company-information.service.gov.uk/
"""

from __future__ import annotations

from typing import Any

import httpx

from keprix.integrations.companies_house.config import (
    API_BASE,
    ensure_egress_allowlist,
    get_api_key,
    is_enabled,
    public_company_url,
)
from keprix.integrations.companies_house.errors import (
    CompaniesHouseApiError,
    CompaniesHouseConfigError,
)


def _require_ready() -> str:
    if not is_enabled():
        raise CompaniesHouseConfigError(
            "Companies House integration is disabled. Set KEPRIX_COMPANIES_HOUSE_ENABLED=1."
        )
    key = get_api_key()
    if not key:
        raise CompaniesHouseConfigError(
            "Companies House API key not configured. Set COMPANIES_HOUSE_API_KEY "
            "or save it under Settings > Companies House."
        )
    return key


def _normalize_address(addr: Any) -> dict[str, Any] | None:
    if not isinstance(addr, dict):
        return None
    lines = [str(addr.get(k) or "").strip() for k in ("address_line_1", "address_line_2", "locality", "region", "postal_code", "country")]
    joined = ", ".join(part for part in lines if part)
    return {
        "address_line_1": addr.get("address_line_1"),
        "address_line_2": addr.get("address_line_2"),
        "locality": addr.get("locality"),
        "region": addr.get("region"),
        "postal_code": addr.get("postal_code"),
        "country": addr.get("country"),
        "formatted": joined or None,
    }


def _search_item(raw: dict[str, Any]) -> dict[str, Any]:
    number = str(raw.get("company_number") or "").strip().upper()
    return {
        "company_number": number,
        "title": raw.get("title") or raw.get("company_name"),
        "company_status": raw.get("company_status"),
        "company_type": raw.get("company_type"),
        "date_of_creation": raw.get("date_of_creation"),
        "address_snippet": raw.get("address_snippet"),
        "description": raw.get("description"),
        "kind": raw.get("kind"),
        "public_url": public_company_url(number) if number else None,
    }


def extract_officer_id(input_value: str) -> str:
    """Accept raw officer id or a /officers/{id}(/appointments) path/URL."""
    import re
    from urllib.parse import unquote, urlparse

    raw = (input_value or "").strip()
    if not raw:
        raise CompaniesHouseConfigError("officer_id is required.")
    if raw.lower().startswith("http://") or raw.lower().startswith("https://"):
        try:
            path = urlparse(raw).path or ""
            match = re.search(r"/officers/([^/]+)", path, re.I)
            if match:
                return unquote(match.group(1))
        except Exception:
            pass
    match = re.search(r"/officers/([^/]+)", raw, re.I)
    if match:
        return unquote(match.group(1))
    if "/" in raw:
        raise CompaniesHouseConfigError(
            "Could not parse officer id. Pass the officer id or a Companies House /officers/{id} path."
        )
    return raw


def _officer_search_item(raw: dict[str, Any]) -> dict[str, Any]:
    links = raw.get("links") if isinstance(raw.get("links"), dict) else {}
    self_path = links.get("self") if isinstance(links, dict) else None
    officer_id = None
    if self_path:
        try:
            officer_id = extract_officer_id(str(self_path))
        except CompaniesHouseConfigError:
            officer_id = None
    return {
        "officer_id": officer_id,
        "name": raw.get("title") or raw.get("name"),
        "description": raw.get("description"),
        "appointment_count": raw.get("appointment_count"),
        "address_snippet": raw.get("address_snippet"),
        "date_of_birth": raw.get("date_of_birth"),
        "self": self_path,
    }


def _compact_appointment(item: dict[str, Any]) -> dict[str, Any]:
    appointed_to = item.get("appointed_to") if isinstance(item.get("appointed_to"), dict) else {}
    number = str(appointed_to.get("company_number") or "").strip().upper() or None
    return {
        "company_number": number,
        "company_name": appointed_to.get("company_name"),
        "company_status": appointed_to.get("company_status"),
        "officer_role": item.get("officer_role"),
        "appointed_on": item.get("appointed_on"),
        "resigned_on": item.get("resigned_on"),
        "nationality": item.get("nationality"),
        "country_of_residence": item.get("country_of_residence"),
        "occupation": item.get("occupation"),
        "uri": public_company_url(number) if number else None,
    }


class CompaniesHouseClient:
    """Async Companies House client with egress-gated HTTP."""

    def __init__(self, api_key: str | None = None, *, product_id: str = "keprix") -> None:
        self._api_key = (api_key or "").strip() or None
        self._product_id = product_id

    def _key(self) -> str:
        return self._api_key or _require_ready()

    async def _request(self, method: str, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        key = self._key()
        ensure_egress_allowlist(self._product_id)
        from keprix.http_client import get_http_client

        url = f"{API_BASE}{path}"
        async with get_http_client(product_id=self._product_id, timeout=30.0) as client:
            response = await client.request(
                method,
                url,
                params=params or {},
                auth=httpx.BasicAuth(key, ""),
                headers={"Accept": "application/json"},
            )
        if response.status_code == 401:
            raise CompaniesHouseApiError("Companies House rejected the API key (401).", status_code=401)
        if response.status_code == 404:
            raise CompaniesHouseApiError("Company not found.", status_code=404)
        if response.status_code == 429:
            raise CompaniesHouseApiError(
                "Companies House rate limit exceeded. Try again shortly.",
                status_code=429,
            )
        if response.status_code >= 400:
            detail = response.text[:300]
            raise CompaniesHouseApiError(
                f"Companies House API error {response.status_code}: {detail}",
                status_code=response.status_code,
            )
        data = response.json()
        if not isinstance(data, dict):
            raise CompaniesHouseApiError("Unexpected Companies House response shape.")
        return data

    async def search_companies(
        self,
        query: str,
        *,
        items_per_page: int = 20,
        start_index: int = 0,
    ) -> dict[str, Any]:
        q = (query or "").strip()
        if not q:
            raise CompaniesHouseConfigError("Search query is required.")
        page_size = max(1, min(int(items_per_page or 20), 100))
        start = max(0, int(start_index or 0))
        raw = await self._request(
            "GET",
            "/search/companies",
            params={"q": q, "items_per_page": page_size, "start_index": start},
        )
        items = [_search_item(item) for item in (raw.get("items") or []) if isinstance(item, dict)]
        return {
            "query": q,
            "mode": "companies",
            "total_results": raw.get("total_results"),
            "items_per_page": raw.get("items_per_page") or page_size,
            "start_index": raw.get("start_index") or start,
            "items": items,
        }

    async def search_officers(
        self,
        query: str,
        *,
        items_per_page: int = 20,
        start_index: int = 0,
    ) -> dict[str, Any]:
        q = (query or "").strip()
        if not q:
            raise CompaniesHouseConfigError("Search query is required.")
        page_size = max(1, min(int(items_per_page or 20), 100))
        start = max(0, int(start_index or 0))
        raw = await self._request(
            "GET",
            "/search/officers",
            params={"q": q, "items_per_page": page_size, "start_index": start},
        )
        items = [
            item
            for item in (_officer_search_item(row) for row in (raw.get("items") or []) if isinstance(row, dict))
            if item.get("officer_id") or item.get("name")
        ]
        return {
            "query": q,
            "mode": "officers",
            "total_results": raw.get("total_results"),
            "items_per_page": raw.get("items_per_page") or page_size,
            "start_index": raw.get("start_index") or start,
            "items": items,
        }

    async def list_officer_appointments(
        self,
        officer_id_or_path: str,
        *,
        max_items: int = 50,
        page_size: int = 35,
    ) -> dict[str, Any]:
        officer_id = extract_officer_id(officer_id_or_path)
        cap = max(1, min(200, int(max_items or 50)))
        size = max(1, min(100, int(page_size or 35)))
        items: list[dict[str, Any]] = []
        start_index = 0
        total: int | None = None
        name: str | None = None
        while len(items) < cap:
            page = await self._request(
                "GET",
                f"/officers/{officer_id}/appointments",
                params={"items_per_page": size, "start_index": start_index},
            )
            if not name and page.get("name"):
                name = str(page.get("name"))
            if page.get("total_results") is not None:
                try:
                    total = int(page.get("total_results"))
                except (TypeError, ValueError):
                    total = None
            batch = [row for row in (page.get("items") or []) if isinstance(row, dict)]
            if not batch:
                break
            items.extend(batch)
            start_index += len(batch)
            if total is not None and start_index >= total:
                break
            if len(batch) < size and total is None:
                break
        companies = [_compact_appointment(row) for row in items[:cap]]
        return {
            "officer_id": officer_id,
            "name": name,
            "total_results": total if total is not None else len(companies),
            "returned": len(companies),
            "companies": companies,
        }

    async def get_company_profile(self, company_number: str, *, include_officers: bool = True) -> dict[str, Any]:
        number = (company_number or "").strip().upper()
        if not number:
            raise CompaniesHouseConfigError("company_number is required.")
        profile = await self._request("GET", f"/company/{number}")
        officers: list[dict[str, Any]] = []
        if include_officers:
            try:
                officers_raw = await self._request(
                    "GET",
                    f"/company/{number}/officers",
                    params={"items_per_page": 20},
                )
                for item in officers_raw.get("items") or []:
                    if not isinstance(item, dict):
                        continue
                    officers.append(
                        {
                            "name": item.get("name"),
                            "officer_role": item.get("officer_role"),
                            "appointed_on": item.get("appointed_on"),
                            "resigned_on": item.get("resigned_on"),
                            "nationality": item.get("nationality"),
                            "occupation": item.get("occupation"),
                            "country_of_residence": item.get("country_of_residence"),
                        }
                    )
            except CompaniesHouseApiError:
                officers = []

        return {
            "company_number": profile.get("company_number") or number,
            "company_name": profile.get("company_name"),
            "company_status": profile.get("company_status"),
            "company_status_detail": profile.get("company_status_detail"),
            "type": profile.get("type"),
            "date_of_creation": profile.get("date_of_creation"),
            "date_of_cessation": profile.get("date_of_cessation"),
            "jurisdiction": profile.get("jurisdiction"),
            "sic_codes": profile.get("sic_codes") or [],
            "has_been_liquidated": profile.get("has_been_liquidated"),
            "has_insolvency_history": profile.get("has_insolvency_history"),
            "has_charges": profile.get("has_charges"),
            "registered_office_address": _normalize_address(profile.get("registered_office_address")),
            "accounts": profile.get("accounts"),
            "confirmation_statement": profile.get("confirmation_statement"),
            "officers": officers,
            "public_url": public_company_url(number),
        }
