"""Structured, best-effort property due diligence."""

from __future__ import annotations

import statistics
from datetime import date, timedelta
from typing import Any

from .refresh import _connection
from .schema import ensure_schema

_last_run: dict[str, Any] | None = None


async def run_due_diligence(uprn: str = "", *, address: str = "", connection=None) -> dict[str, Any]:
    global _last_run
    connection = _connection(connection)
    ensure_schema(connection)
    requested_uprn = (uprn or "").strip()
    if requested_uprn:
        base = connection.execute("SELECT address_full,postcode FROM property_base WHERE uprn=?", (requested_uprn,)).fetchone()
    else:
        base = connection.execute("SELECT uprn,address_full,postcode FROM property_base WHERE lower(address_full)=lower(?) LIMIT 1", ((address or "").strip(),)).fetchone()
        if base:
            requested_uprn = str(base[0])
            base = (base[1], base[2])
    uprn = requested_uprn
    result: dict[str, Any] = {"uprn": uprn, "status": "ok", "sections": {}}
    if not base:
        result["status"] = "unavailable"
        result["sections"]["property"] = {"status": "unavailable", "reason": "UPRN not found"}
        return result
    postcode = base[1]
    cutoff = (date.today() - timedelta(days=730)).isoformat()
    sales = [row[0] for row in connection.execute("SELECT price_gbp FROM property_sold_prices WHERE uprn IN (SELECT uprn FROM property_base WHERE postcode=?) AND sale_date >= ? ORDER BY price_gbp", (postcode, cutoff)).fetchall()]
    if sales:
        result["sections"]["comparables"] = {"status": "available", "count": len(sales), "median_price_gbp": statistics.median(sales), "spread_gbp": max(sales) - min(sales), "window_days": 730, "postcode": postcode, "source": "HM Land Registry Price Paid Data"}
    else:
        result["sections"]["comparables"] = {"status": "unavailable", "reason": "No comparable sales in the last 24 months"}
    epc = connection.execute("SELECT current_energy_rating,potential_energy_rating,current_energy_efficiency,floor_area_m2 FROM property_epc WHERE uprn=? ORDER BY inspection_date DESC LIMIT 1", (uprn,)).fetchone()
    result["sections"]["epc"] = {"status": "available", "current_rating": epc[0], "potential_rating": epc[1], "efficiency": epc[2], "floor_area_m2": epc[3], "source": "EPC open data"} if epc else {"status": "unavailable", "reason": "No EPC record for UPRN"}
    owner = connection.execute("SELECT company_number,country_of_incorporation FROM property_company_ownership WHERE uprn=? LIMIT 1", (uprn,)).fetchone()
    result["sections"]["ownership"] = {"status": "available", "overseas_owner": True, "company_number": owner[0], "country": owner[1], "source": "CCOD/OCOD derived ownership signal"} if owner else {"status": "available", "overseas_owner": False, "source": "CCOD/OCOD derived ownership signal"}
    if owner:
        try:
            from keprix.integrations.companies_house.client import CompaniesHouseClient
            result["sections"]["companies_house"] = {"status": "available", "company": await CompaniesHouseClient().get_company_profile(owner[0], include_officers=True)}
        except Exception as exc:
            result["sections"]["companies_house"] = {"status": "unavailable", "reason": str(exc)}
    else:
        result["sections"]["companies_house"] = {"status": "unavailable", "reason": "No linked company number"}
    _last_run = result
    return result


def diligence_status() -> dict[str, Any]:
    if not _last_run:
        return {"last_run": None, "coverage": {"comparables": 0, "epc": 0, "ownership": 0, "companies_house": 0}}
    sections = _last_run.get("sections", {})
    return {"last_run": _last_run, "coverage": {key: int(value.get("status") == "available") for key, value in sections.items()}}
