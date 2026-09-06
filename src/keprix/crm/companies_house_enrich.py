"""Companies House auto match -> enrich -> persist (prompt 03).

The missing glue between the existing Companies House client and the CRM: a lead
with a company name (and ideally a town) resolves to its company number, SIC
codes, officers and public URL, persisted with a confidence tag. Reuses the
single CompaniesHouseClient (429 handling lives there); no second HTTP client.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from keprix.crm.models import ProvenanceKind
from keprix.crm.store import CrmStore


def _norm(s: Any) -> str:
    return " ".join((str(s or "")).split()).strip().lower()


def _contains_town(address_snippet: Any, town: str) -> bool:
    if not town:
        return True
    return _norm(town) in _norm(address_snippet)


def _match_from_items(
    items: list[dict[str, Any]], company_name: str, town_city: str
) -> dict[str, Any] | None:
    """Exact-title match first, then town-filtered fallback. Ambiguous -> None."""
    target = _norm(company_name)
    if not target:
        return None
    exact = [i for i in items if _norm(i.get("title")) == target]
    if len(exact) == 1:
        return _to_match(exact[0], "high")
    if len(exact) > 1:
        # disambiguate by town when possible
        town_matches = [i for i in exact if _contains_town(i.get("address_snippet"), town_city)]
        if len(town_matches) == 1:
            return _to_match(town_matches[0], "high")
        return None  # ambiguous: two equal-title candidates, not town-resolvable

    # fallback: contains match, prefer town
    contains = [
        i for i in items if target in _norm(i.get("title")) and _norm(i.get("title")) != target
    ]
    if not contains:
        return None
    town_matches = [i for i in contains if _contains_town(i.get("address_snippet"), town_city)]
    pool = town_matches or contains
    if len(pool) == 1:
        return _to_match(pool[0], "medium")
    return None  # ambiguous


def _to_match(item: dict[str, Any], confidence: str) -> dict[str, Any]:
    return {
        "company_number": str(item.get("company_number") or "").strip().upper(),
        "title": item.get("title"),
        "confidence": confidence,
    }


async def match_company(
    company_name: str,
    town_city: str = "",
    *,
    injected_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    from keprix.integrations.companies_house.client import CompaniesHouseClient
    from keprix.integrations.companies_house.config import is_configured

    if injected_items is not None:
        return _match_from_items(injected_items, company_name, town_city)
    if not is_configured():
        return None
    client = CompaniesHouseClient()
    result = await client.search_companies(company_name, items_per_page=20)
    items = [i for i in (result.get("items") or []) if i.get("company_number")]
    return _match_from_items(items, company_name, town_city)


def _empty(value: Any) -> bool:
    return value in (None, "", [], {}, "[]", "{}")


async def enrich_lead(
    store: CrmStore,
    workspace_id: str,
    lead_id: str,
    *,
    injected_items: list[dict[str, Any]] | None = None,
    injected_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ws = store._require_workspace(workspace_id)
    lead = store.get_lead(ws, lead_id)
    if not lead:
        return {"ok": False, "error": "not_found"}

    company_name = str(lead.get("company_name") or "").strip()
    if not company_name:
        return {"ok": False, "status": "none", "reason": "lead has no company_name"}

    jurisdiction = str(lead.get("jurisdiction") or (lead.get("custom_fields") or {}).get("jurisdiction") or "").strip()
    if jurisdiction and jurisdiction.lower() not in {"uk", "gb", "united kingdom"}:
        from keprix.integrations.company_registry import lookup_company

        result = await lookup_company(company_name, jurisdiction=jurisdiction)
        entity = result.get("entity") or {}
        custom = dict(lead.get("custom_fields") or {})
        custom.setdefault("company_registry", entity)
        sources = list(custom.get("enrichment_sources") or [])
        source_record = {"provider": "company_registry", "providers": result.get("providers") or [], "entity": entity}
        if not any(item.get("provider") == "company_registry" for item in sources if isinstance(item, dict)):
            sources.append(source_record)
        custom["enrichment_sources"] = sources
        patch: dict[str, Any] = {"custom_fields": custom, "enrich_confidence": "medium" if entity else "none"}
        for field in ("website", "locality"):
            value = entity.get(field)
            if value and _empty(lead.get(field)):
                patch[field] = value
        updated = store.update_lead(ws, lead_id, **patch)
        return {"ok": True, "status": "enriched" if entity else "none", "lead": updated, "entity": entity, "providers": result.get("providers", []), "disabled": result.get("disabled", [])}

    match = await match_company(
        company_name, str(lead.get("locality") or ""), injected_items=injected_items
    )
    if match is None:
        store.update_lead(ws, lead_id, enrich_confidence="none")
        return {"ok": True, "status": "none", "reason": "ambiguous or no match"}

    if injected_profile is not None:
        profile = dict(injected_profile)
    else:
        from keprix.integrations.companies_house.client import CompaniesHouseClient

        profile = await CompaniesHouseClient().get_company_profile(
            match["company_number"], include_officers=True
        )
        profile = dict(profile)

    patch: dict[str, Any] = {"enrich_confidence": match.get("confidence") or "medium"}
    if match.get("company_number") and _empty(lead.get("company_number")):
        patch["company_number"] = match["company_number"]
    sic_codes = list(profile.get("sic_codes") or [])
    if sic_codes and _empty(lead.get("sic_codes")):
        patch["sic_codes"] = json.dumps(sic_codes)
    officers = list(profile.get("officers") or [])
    if officers and _empty(lead.get("officers")):
        patch["officers"] = json.dumps(officers)
    public_url = str(profile.get("public_url") or "")
    if public_url and _empty(lead.get("website")):
        patch["website"] = public_url

    # companies_house custom_fields record via the existing merge helper
    try:
        from keprix.crm.enrichment import merge_companies_house_profile

        merged = merge_companies_house_profile(lead, profile)
        current_custom = dict(lead.get("custom_fields") or {})
        current_custom.update(merged.get("custom_fields") or {})
        patch["custom_fields"] = current_custom
        if merged.get("company_number") and _empty(lead.get("company_number")):
            patch["company_number"] = merged["company_number"]
        if merged.get("company_name") and _empty(lead.get("company_name")):
            patch["company_name"] = merged["company_name"]
        if merged.get("locality") and _empty(lead.get("locality")):
            patch["locality"] = merged["locality"]
    except Exception:  # noqa: BLE001
        pass

    updated = store.update_lead(ws, lead_id, **patch)
    for field, value in patch.items():
        if field == "enrich_confidence":
            continue
        store.record_provenance(
            ws,
            entity_type="lead",
            entity_id=lead_id,
            field_name=field,
            value=value,
            kind=ProvenanceKind.OBSERVED,
            source_url=public_url,
            adapter="companies_house",
            verification_state="unverified",
        )
    # Auto-rescore after enrichment (prompt 09).
    try:
        from keprix.crm.ab_attribution import rescore_after_enrichment

        rescore_after_enrichment(store, ws, lead_id, reason="companies_house_enrich")
    except Exception:  # noqa: BLE001
        pass
    return {
        "ok": True,
        "status": "enriched",
        "lead": updated,
        "company_number": match.get("company_number"),
        "confidence": match.get("confidence"),
    }


async def enrich_leads_batch(
    store: CrmStore,
    workspace_id: str,
    lead_ids: list[str],
) -> dict[str, Any]:
    ws = store._require_workspace(workspace_id)
    enriched = 0
    none = 0
    failed = 0
    skipped = 0
    results: list[dict[str, Any]] = []
    for lead_id in lead_ids:
        if not store.get_lead(ws, lead_id):
            skipped += 1
            continue
        try:
            result = await enrich_lead(store, ws, lead_id)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            results.append({"lead_id": lead_id, "error": str(exc)})
            continue
        if result.get("status") == "enriched":
            enriched += 1
        elif result.get("status") == "none":
            none += 1
        results.append(
            {
                "lead_id": lead_id,
                "status": result.get("status"),
                "company_number": result.get("company_number"),
            }
        )
    return {
        "ok": True,
        "enriched": enriched,
        "none": none,
        "failed": failed,
        "skipped": skipped,
        "results": results,
    }


def match_company_sync(company_name: str, town_city: str = "") -> dict[str, Any] | None:
    return asyncio.run(match_company(company_name, town_city))


def enrich_lead_sync(store: CrmStore, workspace_id: str, lead_id: str) -> dict[str, Any]:
    return asyncio.run(enrich_lead(store, workspace_id, lead_id))
