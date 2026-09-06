"""Normalized OpenCorporates, GLEIF, and SEC EDGAR lookup client."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RegistryEntity:
    name: str | None = None
    jurisdiction: str | None = None
    registration_id: str | None = None
    lei: str | None = None
    status: str | None = None
    officers: list[dict[str, Any]] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    providers: list[str] = field(default_factory=list)

    def merge(self, other: RegistryEntity) -> None:
        for field_name in ("name", "jurisdiction", "registration_id", "lei", "status"):
            if not getattr(self, field_name) and getattr(other, field_name):
                setattr(self, field_name, getattr(other, field_name))
        if not self.officers and other.officers:
            self.officers = list(other.officers)
        self.sources.extend(source for source in other.sources if source not in self.sources)
        self.providers.extend(
            provider for provider in other.providers if provider not in self.providers
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "jurisdiction": self.jurisdiction,
            "registration_id": self.registration_id,
            "lei": self.lei,
            "status": self.status,
            "officers": self.officers,
            "sources": self.sources,
            "providers": self.providers,
        }


def _enabled_provider(name: str) -> bool:
    return os.environ.get(f"KEPRIX_COMPANY_REGISTRY_{name.upper()}_ENABLED", "1").lower() not in {
        "0",
        "false",
        "no",
    }


class CompanyRegistryClient:
    def __init__(self, *, timeout: float = 20.0) -> None:
        self.timeout = timeout

    async def _get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        from keprix.http_client import get_http_client

        async with get_http_client(product_id="keprix", timeout=self.timeout) as client:
            response = await client.get(url, params=params or {}, headers=headers or {})
            response.raise_for_status()
            return response.json()

    async def opencorporates(self, query: str) -> RegistryEntity | None:
        key = os.environ.get("OPENCORPORATES_API_TOKEN", "").strip()
        if not _enabled_provider("opencorporates") or not key:
            return None
        data = await self._get(
            "https://api.opencorporates.com/v0.4/companies/search",
            params={"q": query, "api_token": key, "per_page": 1},
        )
        rows = (data.get("results") or {}).get("companies") or []
        company = (rows[0] or {}).get("company") if rows else None
        if not company:
            return None
        return RegistryEntity(
            name=company.get("name"),
            jurisdiction=company.get("jurisdiction_code"),
            registration_id=company.get("company_number"),
            status=company.get("company_status"),
            sources=[company.get("opencorporates_url") or "opencorporates"],
            providers=["opencorporates"],
        )

    async def gleif(self, query: str) -> RegistryEntity | None:
        if not _enabled_provider("gleif"):
            return None
        data = await self._get(
            "https://api.gleif.org/api/v1/lei-records",
            params={"filter[entity.legalName]": query, "page[size]": 1},
        )
        row = (data.get("data") or [None])[0]
        attrs = (row or {}).get("attributes") or {}
        entity = attrs.get("entity") or {}
        if not row:
            return None
        return RegistryEntity(
            name=entity.get("legalName"),
            jurisdiction=entity.get("jurisdiction"),
            lei=(row or {}).get("id"),
            status=attrs.get("registration", {}).get("status"),
            sources=["https://api.gleif.org"],
            providers=["gleif"],
        )

    async def edgar(self, query: str) -> RegistryEntity | None:
        if not _enabled_provider("edgar"):
            return None
        data = await self._get(
            "https://www.sec.gov/files/company_tickers.json",
            headers={
                "User-Agent": os.environ.get(
                    "SEC_EDGAR_USER_AGENT", "Keprix company registry contact@verlox.uk"
                )
            },
        )
        match = next(
            (
                row
                for row in (data or {}).values()
                if query.lower() in str(row.get("title") or "").lower()
            ),
            None,
        )
        if not match:
            return None
        cik = str(match.get("cik_str") or "").zfill(10)
        return RegistryEntity(
            name=match.get("title"),
            jurisdiction="US",
            registration_id=str(match.get("cik_str") or "").zfill(10),
            status="public filer",
            sources=[
                f"https://data.sec.gov/submissions/CIK{cik}.json"
            ],
            providers=["sec_edgar"],
        )

    async def lookup(self, query: str, *, jurisdiction: str | None = None) -> dict[str, Any]:
        q = query.strip()
        if not q:
            raise ValueError("Company registry query is required")
        normalized = (jurisdiction or "").strip().lower()
        if normalized in {"gb", "uk", "united kingdom"}:
            return {
                "query": q,
                "jurisdiction": jurisdiction,
                "entity": None,
                "providers": [],
                "disabled": [],
                "native_provider": "companies_house",
            }
        jobs: list[tuple[str, Callable[[str], Awaitable[RegistryEntity | None]]]] = [
            ("opencorporates", self.opencorporates),
            ("gleif", self.gleif),
            ("sec_edgar", self.edgar),
        ]
        entities: list[RegistryEntity] = []
        disabled: list[str] = []
        for name, job in jobs:
            if (
                name == "opencorporates"
                and not os.environ.get("OPENCORPORATES_API_TOKEN", "").strip()
            ):
                disabled.append(name)
                continue
            if not _enabled_provider(name):
                disabled.append(name)
                continue
            try:
                result = await job(q)
            except Exception:
                result = None
            if result:
                entities.append(result)
        merged = RegistryEntity()
        for entity in entities:
            merged.merge(entity)
        return {
            "query": q,
            "jurisdiction": jurisdiction,
            "entity": merged.to_dict() if entities else None,
            "providers": [name for name, _ in jobs if name not in disabled],
            "disabled": disabled,
        }


async def lookup_company(query: str, *, jurisdiction: str | None = None) -> dict[str, Any]:
    return await CompanyRegistryClient().lookup(query, jurisdiction=jurisdiction)
