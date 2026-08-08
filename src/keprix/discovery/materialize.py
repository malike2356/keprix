"""Materialize discovery candidates into CRM Lists with Soft Wall + dedupe."""

from __future__ import annotations

import os
from typing import Any

from keprix.crm.identity import IdentityResolver
from keprix.crm.soft_wall import gate_or_approve
from keprix.crm.store import CrmStore, get_crm_store
from keprix.discovery.models import HIGH_RISK_DOMAIN_PACKS, LeadCandidate


def materialize_soft_wall_enabled() -> bool:
    raw = os.environ.get("KEPRIX_DISCOVERY_SOFT_WALL_MATERIALIZE", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def materialize_candidates(
    workspace_id: str,
    candidates: list[LeadCandidate] | list[dict[str, Any]],
    *,
    list_name: str | None = None,
    domain_pack: str = "generic",
    source: str = "discovery",
    job_id: str | None = None,
    store: CrmStore | None = None,
    approval_id: str | None = None,
    force: bool = False,
    actor_type: str = "system",
    actor_id: str | None = None,
    skip_soft_wall: bool = False,
    icp_id: str | None = None,
    icp_version: int | None = None,
) -> dict[str, Any]:
    """Create/upsert leads and attach to a draft CRM List.

    Soft Wall gates materialize when KEPRIX_DISCOVERY_SOFT_WALL_MATERIALIZE=1
    (default). Discovery never sets contactability; that is a separate decision.
    """
    store = store or get_crm_store()
    normalized = [
        c if isinstance(c, LeadCandidate) else LeadCandidate.from_dict(c) for c in candidates
    ]

    excluded_icp: list[dict[str, Any]] = []
    try:
        from keprix.crm import icp as icp_mod

        if not icp_id and job_id:
            job = store.get_discovery_job(workspace_id, job_id) or {}
            params = job.get("params") or {}
            nested = params.get("params") if isinstance(params.get("params"), dict) else {}
            icp_id = params.get("icp_id") or nested.get("icp_id") or job.get("icp_id")
            ver = params.get("icp_version") or nested.get("icp_version") or job.get("icp_version")
            if ver is not None:
                icp_version = int(ver)

        icp_row = None
        if icp_id:
            icp_row = icp_mod.get_icp(store, workspace_id, str(icp_id))
        if not icp_row:
            icp_row = icp_mod.get_active_icp(store, workspace_id)
        if icp_row:
            icp_id = str(icp_row["id"])
            icp_version = int(icp_row.get("version") or 1)
            rules = list(icp_row.get("exclude_rules") or [])
            kept_cand: list[LeadCandidate] = []
            for cand in normalized:
                fields = _candidate_to_lead_fields(cand, domain_pack=domain_pack, source=source)
                if icp_mod.candidate_matches_exclude(fields, rules):
                    excluded_icp.append(
                        {
                            "external_id": cand.external_id,
                            "company": cand.company,
                            "reason": "icp_exclude",
                            "icp_id": icp_id,
                            "icp_version": icp_version,
                        }
                    )
                else:
                    kept_cand.append(cand)
            normalized = kept_cand
    except Exception:
        pass

    if not skip_soft_wall and materialize_soft_wall_enabled():
        gate = gate_or_approve(
            workspace_id,
            kind="materialize_discovery_list",
            subject=f"Materialize {len(normalized)} discovery candidates into CRM List",
            payload={
                "candidate_count": len(normalized),
                "domain_pack": domain_pack,
                "job_id": job_id,
                "list_name": list_name,
                "source": source,
                "icp_id": icp_id,
                "icp_excluded": len(excluded_icp),
            },
            object_type="discovery_job",
            object_id=job_id,
            actor_id=actor_id,
            force=force,
            approval_id=approval_id,
        )
        if gate.get("blocked"):
            return {
                "blocked": True,
                "error_code": gate.get("error_code"),
                "approval": gate.get("approval"),
                "candidate_count": len(normalized),
                "icp_excluded": excluded_icp,
            }

    list_row = store.create_list(
        workspace_id,
        list_name or f"Discovery {source}",
        description=f"Draft list from discovery adapter {source}",
        domain_pack=domain_pack,
        source=source,
        status="draft",
        tags=["discovery", source],
        actor_type=actor_type,
        actor_id=actor_id,
    )
    if icp_id:
        try:
            from keprix.crm import icp as icp_mod

            icp_mod.stamp_entity_icp(
                store,
                workspace_id,
                entity_type="list",
                entity_id=list_row["id"],
                icp_id=str(icp_id),
                icp_version=int(icp_version or 1),
            )
            list_row = store.get_list(workspace_id, list_row["id"]) or list_row
        except Exception:
            pass

    resolver = IdentityResolver(store)
    created = 0
    reused = 0
    skipped = 0
    merge_suggestions: list[dict[str, Any]] = []
    memberships: list[dict[str, Any]] = []
    report: list[dict[str, Any]] = []

    for cand in normalized:
        cand.ensure_hashes()
        fields = _candidate_to_lead_fields(cand, domain_pack=domain_pack, source=source)
        exact = resolver.resolve_lead(workspace_id, **fields)
        exact_account = resolver.resolve_account(
            workspace_id,
            name=fields.get("company_name"),
            company_number=fields.get("company_number"),
            domain=fields.get("domain"),
        )

        action = "created"
        lead: dict[str, Any] | None = None
        if exact:
            lead = store.get_lead(workspace_id, exact.entity_id)
            reused += 1
            action = "reused"
        else:
            # Fuzzy name collision -> merge Soft Wall suggestion, still create draft lead.
            fuzzy = resolver.suggest_fuzzy_merges(
                workspace_id,
                entity_type="lead",
                name=fields.get("name") or fields.get("company_name"),
                domain=fields.get("domain"),
                persist=True,
                min_score=0.82,
            )
            if fuzzy:
                merge_suggestions.extend(fuzzy)
                action = "created_with_merge_suggestion"
            lead = store.upsert_lead(
                workspace_id,
                actor_type=actor_type,
                actor_id=actor_id,
                **fields,
            )
            created += 1

        if exact_account and lead and not lead.get("account_id"):
            store.update_lead(workspace_id, lead["id"], account_id=exact_account.entity_id)

        if not lead:
            skipped += 1
            report.append({"action": "skipped", "external_id": cand.external_id})
            continue

        if icp_id:
            try:
                from keprix.crm import icp as icp_mod

                icp_mod.stamp_entity_icp(
                    store,
                    workspace_id,
                    entity_type="lead",
                    entity_id=lead["id"],
                    icp_id=str(icp_id),
                    icp_version=int(icp_version or 1),
                )
            except Exception:
                pass

        member = store.add_list_member(
            workspace_id,
            list_row["id"],
            member_type="lead",
            member_id=lead["id"],
            stage=lead.get("stage") or "discovered",
        )
        memberships.append(member)
        report.append(
            {
                "action": action,
                "lead_id": lead["id"],
                "external_id": cand.external_id,
                "company": cand.company,
                "content_hash": cand.content_hash,
            }
        )

    return {
        "blocked": False,
        "list": list_row,
        "list_id": list_row["id"],
        "created": created,
        "reused": reused,
        "skipped": skipped,
        "member_count": len(memberships),
        "merge_suggestions": merge_suggestions,
        "merge_count": len(merge_suggestions),
        "merges_deep_link": "/crm/merges" if merge_suggestions else None,
        "list_deep_link": f"/crm/lists/{list_row['id']}",
        "report": report,
        "icp_id": icp_id,
        "icp_version": icp_version,
        "icp_excluded": excluded_icp,
        "contactability_note": (
            "Discovery materialize creates review candidates only. "
            "Contactability and outreach require a separate policy decision."
        ),
    }


def _candidate_to_lead_fields(
    cand: LeadCandidate,
    *,
    domain_pack: str,
    source: str,
) -> dict[str, Any]:
    emails = list(cand.emails)
    phones = list(cand.phones)
    for contact in cand.contacts:
        if not isinstance(contact, dict):
            continue
        if contact.get("email"):
            emails.append(str(contact["email"]))
        if contact.get("phone"):
            phones.append(str(contact["phone"]))
    # Dedupe preserve order
    emails = list(dict.fromkeys(e.strip() for e in emails if e and str(e).strip()))
    phones = list(dict.fromkeys(p.strip() for p in phones if p and str(p).strip()))

    name = cand.company
    if cand.contacts:
        first = cand.contacts[0]
        if isinstance(first, dict) and first.get("name"):
            name = str(first["name"])

    return {
        "name": name or cand.company or "Unknown",
        "company_name": cand.company,
        "company_number": cand.company_number,
        "domain": cand.domain,
        "emails": [{"address": e, "primary": i == 0} for i, e in enumerate(emails)],
        "phones": [{"number": p, "primary": i == 0} for i, p in enumerate(phones)],
        "source": source or cand.source,
        "domain_pack": cand.domain_pack or domain_pack,
        "stage": "discovered",
        "external_source_id": cand.external_id,
        "scores": {"discovery_hint": cand.score_hint} if cand.score_hint is not None else {},
        "tags": ["discovery", cand.source] if cand.source else ["discovery"],
    }


def is_high_risk_pack(domain_pack: str | None) -> bool:
    return str(domain_pack or "").strip().lower() in HIGH_RISK_DOMAIN_PACKS


def enroll_requires_soft_wall(domain_pack: str | None) -> bool:
    """Health/social care packs always require Soft Wall enroll, even if gates loosened."""
    return is_high_risk_pack(domain_pack)
