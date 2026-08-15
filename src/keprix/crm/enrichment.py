"""Opt-in, provenance-preserving CRM enrichment helpers."""

from __future__ import annotations

from typing import Any

from keprix.integrations.companies_house.config import public_company_url


def merge_companies_house_profile(lead: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Build an empty-cell-safe patch from a Companies House profile.

    The raw profile is retained under ``custom_fields`` so operators can audit
    where each enrichment came from. Existing user-entered values win.
    """
    custom = dict(lead.get("custom_fields") or {})
    sources = list(custom.get("enrichment_sources") or [])
    number = str(profile.get("company_number") or lead.get("company_number") or "").strip().upper()
    source_url = str(profile.get("public_url") or (public_company_url(number) if number else ""))
    record = {
        "provider": "companies_house",
        "company_number": number,
        "url": source_url,
        "company_status": profile.get("company_status"),
        "sic_codes": list(profile.get("sic_codes") or []),
        "registered_office_address": profile.get("registered_office_address"),
        "officers": list(profile.get("officers") or []),
    }
    if not any(item.get("provider") == "companies_house" and item.get("company_number") == number for item in sources if isinstance(item, dict)):
        sources.append(record)
    custom["companies_house"] = record
    custom["enrichment_sources"] = sources
    patch: dict[str, Any] = {"custom_fields": custom}
    if number and not lead.get("company_number"):
        patch["company_number"] = number
    if profile.get("company_name") and not lead.get("company_name"):
        patch["company_name"] = str(profile["company_name"]).strip()
    if profile.get("registered_office_address") and not lead.get("locality"):
        address = profile["registered_office_address"]
        if isinstance(address, dict) and address.get("locality"):
            patch["locality"] = address["locality"]
    return patch


def apply_companies_house_profile(store: Any, workspace_id: str, lead_id: str, profile: dict[str, Any]) -> dict[str, Any] | None:
    lead = store.get_lead(workspace_id, lead_id)
    if not lead:
        return None
    patch = merge_companies_house_profile(lead, profile)
    return store.update_lead(workspace_id, lead_id, **patch)
