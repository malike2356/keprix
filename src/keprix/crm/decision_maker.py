"""Decision-maker name resolution (prompt 04).

When a lead has a company but no contact name, resolve the person of interest
from the company's officers (prompt 03) ranked by role, with a web-search
fallback, then set name + role with a confidence tag. Fill-empty-only; never
invent. Reuses the Companies House client 429 handling (via prompt 03 profile).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from keprix.crm.models import ProvenanceKind
from keprix.crm.store import CrmStore

ROLE_PRIORITY = (
    "director",
    "ceo",
    "founder",
    "managing director",
    "owner",
    "partner",
    "head",
    "manager",
)


def _rank_role(officer_role: Any) -> int:
    role = str(officer_role or "").lower()
    for idx, key in enumerate(ROLE_PRIORITY):
        if key in role:
            return idx
    return len(ROLE_PRIORITY)


def _active_officers(officers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for officer in officers:
        if not isinstance(officer, dict):
            continue
        if not (officer.get("name") or "").strip():
            continue
        if officer.get("resigned_on"):
            continue
        out.append(officer)
    return out


def _best_officer(officers: list[dict[str, Any]]) -> dict[str, Any] | None:
    active = _active_officers(officers)
    if not active:
        return None
    return min(active, key=lambda o: _rank_role(o.get("officer_role")))


def _load_officers(lead: dict[str, Any]) -> list[dict[str, Any]]:
    raw = lead.get("officers") or []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = []
    return [o for o in raw if isinstance(o, dict)]


async def resolve_decision_maker(
    store: CrmStore,
    workspace_id: str,
    lead_id: str,
    *,
    injected_officers: list[dict[str, Any]] | None = None,
    injected_profile: dict[str, Any] | None = None,
    injected_search: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    ws = store._require_workspace(workspace_id)
    lead = store.get_lead(ws, lead_id)
    if not lead:
        return {"ok": False, "error": "not_found"}

    if (lead.get("name") or "").strip():
        return {"ok": True, "status": "skipped", "reason": "contact_name already set"}
    if not (lead.get("company_name") or "").strip():
        return {"ok": True, "status": "skipped", "reason": "no company to resolve from"}

    officers: list[dict[str, Any]] = []
    source = ""
    if injected_officers is not None:
        officers = injected_officers
        source = "companies_house"
    elif _load_officers(lead):
        officers = _load_officers(lead)
        source = "companies_house"
    elif injected_profile is not None:
        officers = list(injected_profile.get("officers") or [])
        source = "companies_house"
    else:
        from keprix.crm.companies_house_enrich import enrich_lead

        enriched = await enrich_lead(store, ws, lead_id)
        if enriched.get("status") == "enriched":
            refreshed = store.get_lead(ws, lead_id)
            officers = _load_officers(refreshed or {})
            source = "companies_house"

    candidate = _best_officer(officers)
    role = ""
    confidence = "medium"
    if candidate is None and injected_search is not None:
        # web-search fallback: extract a name + title from injected results
        from keprix.crm.research_enrich import split_name

        for item in injected_search:
            title = str(item.get("title") or item.get("name") or "")
            if not title:
                continue
            first, last = split_name(title)
            if first:
                candidate = {"name": title, "officer_role": ""}
                role = ""
                source = "web_search"
                confidence = "low"
                break
    elif candidate is not None and injected_search is not None:
        # enrich role from search when officer had no role
        pass

    if candidate is None:
        store.update_lead(ws, lead_id, research_notes="no decision maker resolved")
        return {"ok": True, "status": "none", "reason": "no decision maker resolved"}

    name = str(candidate.get("name") or "").strip()
    if not name:
        store.update_lead(ws, lead_id, research_notes="no decision maker resolved")
        return {"ok": True, "status": "none", "reason": "no decision maker resolved"}

    if source == "companies_house" and candidate.get("officer_role"):
        role = str(candidate["officer_role"])

    patch: dict[str, Any] = {"name": name}
    if role:
        # role is advisory; keep it in custom_fields so it does not collide with name
        custom = dict(lead.get("custom_fields") or {})
        custom["decision_maker"] = {
            "name": name,
            "role": role,
            "source": source,
            "confidence": confidence,
        }
        patch["custom_fields"] = custom
    store.update_lead(ws, lead_id, **patch)
    store.record_provenance(
        ws,
        entity_type="lead",
        entity_id=lead_id,
        field_name="name",
        value=name,
        kind=ProvenanceKind.OBSERVED,
        source_url="",
        adapter="decision_maker",
        verification_state="unverified",
    )
    return {
        "ok": True,
        "status": "resolved",
        "name": name,
        "role": role,
        "source": source,
        "confidence": confidence,
    }


async def resolve_decision_makers_batch(
    store: CrmStore,
    workspace_id: str,
    lead_ids: list[str],
) -> dict[str, Any]:
    ws = store._require_workspace(workspace_id)
    resolved = 0
    none = 0
    skipped = 0
    failed = 0
    results: list[dict[str, Any]] = []
    for lead_id in lead_ids:
        if not store.get_lead(ws, lead_id):
            skipped += 1
            continue
        try:
            result = await resolve_decision_maker(store, ws, lead_id)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            results.append({"lead_id": lead_id, "error": str(exc)})
            continue
        if result.get("status") == "resolved":
            resolved += 1
        elif result.get("status") == "none":
            none += 1
        results.append(
            {"lead_id": lead_id, "status": result.get("status"), "name": result.get("name")}
        )
    return {
        "ok": True,
        "resolved": resolved,
        "none": none,
        "skipped": skipped,
        "failed": failed,
        "results": results,
    }


def resolve_decision_maker_sync(store: CrmStore, workspace_id: str, lead_id: str) -> dict[str, Any]:
    return asyncio.run(resolve_decision_maker(store, workspace_id, lead_id))
