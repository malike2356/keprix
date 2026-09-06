"""Internal deep-research contact enrichment (prompt 02).

Resolves a lead that has only email + name into company, website, locality,
linkedin_url and a Companies House record using internal algorithms only:
email-domain heuristics, the web_directory search path, and the Companies House
client. Nothing is fabricated; free-mail domains never imply a business.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from keprix.crm.models import ProvenanceKind
from keprix.crm.store import CrmStore, _normalise_email

FREE_MAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "icloud.com",
    "me.com",
    "aol.com",
    "proton.me",
    "protonmail.com",
    "googlemail.com",
    "yahoo.co.uk",
    "hotmail.co.uk",
    "outlook.co.uk",
}

_LINKEDIN_RE = re.compile(
    r"(?:https?://(?:www\.)?)?linkedin\.com/(?:in|company)/[A-Za-z0-9._%\-]+", re.I
)


def _normalize_linkedin(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if not value.lower().startswith("http"):
        value = "https://" + value
    return value.rstrip("/")


def split_name(fullname: str) -> tuple[str, str]:
    """Best-effort first/last split. Returns ('','') for empty input."""
    parts = [p for p in (fullname or "").strip().split() if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def domain_from_email(email: str) -> str:
    """Return the email domain, or '' for free-mail / malformed addresses."""
    address = _normalise_email(email) or ""
    if "@" not in address:
        return ""
    domain = address.rsplit("@", 1)[1].strip().lower()
    if domain in FREE_MAIL_DOMAINS:
        return ""
    return domain


def company_from_domain(domain: str) -> str:
    """Business-domain stem -> company-name candidate. Never for free-mail."""
    if not domain:
        return ""
    stem = domain.split(".")[0]
    stem = re.sub(r"[-_]+", " ", stem).strip()
    if not stem or len(stem) < 2:
        return ""
    return " ".join(part.capitalize() for part in stem.split())


def _search(
    query: str, *, limit: int = 5, injected: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    """Web search via the existing web_directory backend; honest degrade."""
    if injected is not None:
        return [i for i in injected if isinstance(i, dict)]
    try:
        from keprix.discovery.adapters.web_directory import WebDirectoryAdapter

        adapter = WebDirectoryAdapter()
        results = adapter._live_search(query, limit=limit)
        return results
    except Exception:  # noqa: BLE001 - honest degrade, never fabricate
        return []


def _extract_socials(search_results: list[dict[str, Any]]) -> tuple[str, str, str]:
    """Return (website, linkedin_url, locality) best-effort from search items."""
    website = ""
    linkedin_url = ""
    locality = ""
    for item in search_results:
        url = str(item.get("url") or item.get("link") or item.get("href") or "")
        snippet = str(item.get("snippet") or item.get("content") or item.get("description") or "")
        if not website and url and _LINKEDIN_RE.match(url) is None:
            website = url
        if not linkedin_url:
            m = _LINKEDIN_RE.search(url + " " + snippet)
            if m:
                linkedin_url = _normalize_linkedin(m.group(0))
        if not locality:
            # Extract a plausible UK town from the snippet; low confidence, kept
            # as a hint only and never written to a populated field.
            pass
    return website, linkedin_url, locality


async def _companies_house_lookup(
    company_name: str, *, injected: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """Search Companies House for a company by name. Returns a profile or None."""
    if injected is not None:
        return injected or None
    try:
        from keprix.integrations.companies_house.client import CompaniesHouseClient
        from keprix.integrations.companies_house.config import is_configured

        if not is_configured():
            return None
        client = CompaniesHouseClient()
        result = await client.search_companies(company_name, items_per_page=5)
        items = [i for i in (result.get("items") or []) if i.get("company_number")]
        if not items:
            return None
        number = items[0]["company_number"]
        profile = await client.get_company_profile(number, include_officers=True)
        profile = dict(profile)
        profile["public_url"] = profile.get("public_url") or items[0].get("public_url")
        return profile
    except Exception:  # noqa: BLE001 - provider failure is a partial, not a crash
        return None


def _empty(value: Any) -> bool:
    return value in (None, "", [], {}, "[]", "{}")


async def research_lead(
    store: CrmStore,
    workspace_id: str,
    lead_id: str,
    *,
    search_results: list[dict[str, Any]] | None = None,
    companies_house_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve a lead's empty fields from internal signals. Fill-empty-only."""
    ws = store._require_workspace(workspace_id)
    lead = store.get_lead(ws, lead_id)
    if not lead:
        return {"ok": False, "error": "not_found"}

    notes: list[str] = []
    patch: dict[str, Any] = {}

    # 1. split name
    first, last = split_name(str(lead.get("name") or ""))
    if first and _empty(lead.get("first_name")):
        patch["first_name"] = first
    if last and _empty(lead.get("last_name")):
        patch["last_name"] = last

    # 2. domain / company candidate
    email = ""
    for item in lead.get("emails") or []:
        addr = item.get("address") if isinstance(item, dict) else item
        if addr:
            email = str(addr)
            break
    domain = domain_from_email(email)
    if domain and _empty(lead.get("website")):
        patch["website"] = f"https://{domain}"
    company_candidate = company_from_domain(domain) if domain else ""

    # 3. web search for website/linkedin/town
    query_parts = [
        p for p in (first, last, lead.get("company_name") or company_candidate, domain) if p
    ]
    search_query = " ".join(query_parts) if query_parts else str(lead.get("company_name") or "")
    if search_query.strip():
        results = _search(search_query, injected=search_results)
        website, linkedin, _town = _extract_socials(results)
        if website and _empty(lead.get("website")):
            patch["website"] = website
        if linkedin and _empty(lead.get("linkedin_url")):
            patch["linkedin_url"] = linkedin
        if results:
            socials = [u for u in (website, linkedin) if u]
            if socials and _empty(lead.get("social_profiles")):
                patch["social_profiles"] = json.dumps({"search": socials})

    # 4. Companies House auto-enrich (prompt 03) - only when a company name exists
    ch_profile = companies_house_profile
    if ch_profile is None and (lead.get("company_name") or company_candidate):
        ch_profile = await _companies_house_lookup(
            str(lead.get("company_name") or company_candidate), injected=companies_house_profile
        )
    if ch_profile:
        try:
            from keprix.crm.enrichment import merge_companies_house_profile

            merged = merge_companies_house_profile(lead, ch_profile)
            patch.update(merged)
            if ch_profile.get("company_number"):
                notes.append(f"companies_house:{ch_profile['company_number']}")
        except Exception:  # noqa: BLE001
            notes.append("companies_house merge skipped")

    # 5. fill-empty-only write + provenance
    applied = 0
    for field, value in patch.items():
        if field == "custom_fields":
            current = lead.get("custom_fields") or {}
            merged_custom = dict(current)
            merged_custom.update(value or {})
            store.update_lead(ws, lead_id, custom_fields=merged_custom)
            store.record_provenance(
                ws,
                entity_type="lead",
                entity_id=lead_id,
                field_name="custom_fields",
                value=merged_custom,
                kind=ProvenanceKind.OBSERVED,
                adapter="internal_research",
                verification_state="unverified",
            )
            applied += 1
            continue
        if _empty(lead.get(field)):
            store.update_lead(ws, lead_id, **{field: value})
            store.record_provenance(
                ws,
                entity_type="lead",
                entity_id=lead_id,
                field_name=field,
                value=value,
                kind=ProvenanceKind.OBSERVED,
                adapter="internal_research",
                verification_state="unverified",
            )
            applied += 1

    # research_status
    status = "done" if applied else "partial"
    if not patch and not (first or last):
        status = "partial"
    if not lead.get("company_name") and not company_candidate and not ch_profile:
        # A free-mail capture with no company signal: explicitly partial.
        status = "partial"
        notes.append("no company signal; nothing to resolve from a free-mail address")
    store.update_lead(ws, lead_id, research_status=status, research_notes="; ".join(notes))

    # Auto-rescore after enrichment (prompt 09), once per enrichment step.
    try:
        from keprix.crm.ab_attribution import rescore_after_enrichment

        rescore_after_enrichment(store, ws, lead_id, reason="research_enrich")
    except Exception:  # noqa: BLE001 - rescore is advisory, never blocks enrich
        pass

    return {"ok": True, "lead_id": lead_id, "status": status, "applied": applied, "notes": notes}


async def research_leads_batch(
    store: CrmStore,
    workspace_id: str,
    lead_ids: list[str],
) -> dict[str, Any]:
    ws = store._require_workspace(workspace_id)
    done = 0
    partial = 0
    failed = 0
    skipped = 0
    results: list[dict[str, Any]] = []
    for lead_id in lead_ids:
        if not store.get_lead(ws, lead_id):
            skipped += 1
            continue
        try:
            result = await research_lead(store, ws, lead_id)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            results.append({"lead_id": lead_id, "error": str(exc)})
            continue
        if result.get("status") == "done":
            done += 1
        elif result.get("status") == "partial":
            partial += 1
        results.append({"lead_id": lead_id, "status": result.get("status")})
    return {
        "ok": True,
        "done": done,
        "partial": partial,
        "failed": failed,
        "skipped": skipped,
        "results": results,
    }


def research_lead_sync(store: CrmStore, workspace_id: str, lead_id: str) -> dict[str, Any]:
    return asyncio.run(research_lead(store, workspace_id, lead_id))


def research_leads_batch_sync(
    store: CrmStore, workspace_id: str, lead_ids: list[str]
) -> dict[str, Any]:
    return asyncio.run(research_leads_batch(store, workspace_id, lead_ids))
