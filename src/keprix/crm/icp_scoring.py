"""Auto ICP scoring and account briefs (prompt 463)."""

from __future__ import annotations

import json
from typing import Any

from keprix.crm.icp import get_active_icp, get_icp
from keprix.crm.soft_wall import gate_or_approve


def _blob(entity: dict[str, Any]) -> str:
    parts = [
        str(entity.get("name") or ""),
        str(entity.get("display_name") or ""),
        str(entity.get("company_name") or ""),
        str(entity.get("domain") or ""),
        " ".join(str(t) for t in (entity.get("tags") or [])),
    ]
    emails = entity.get("emails") or []
    for item in emails:
        parts.append(str(item.get("address") if isinstance(item, dict) else item or ""))
    return " ".join(parts).lower()


def score_against_icp(entity: dict[str, Any], icp: dict[str, Any]) -> dict[str, Any]:
    """Deterministic score 0-100 with reasons."""
    score = 0
    reasons: list[dict[str, Any]] = []
    blob = _blob(entity)

    for kw in icp.get("keywords") or []:
        needle = str(kw).lower()
        if needle and needle in blob:
            score += 15
            reasons.append({"code": "keyword_hit", "value": kw, "points": 15, "kind": "verified" if entity.get("domain") else "inference"})

    for rule in icp.get("include_rules") or []:
        if isinstance(rule, dict):
            value = str(rule.get("value") or "").lower()
            if value and value in blob:
                score += 20
                reasons.append({"code": "include_rule", "value": value, "points": 20, "kind": "verified"})
        else:
            value = str(rule).lower()
            if value and value in blob:
                score += 20
                reasons.append({"code": "include_rule", "value": value, "points": 20, "kind": "verified"})

    for geo in icp.get("geography") or []:
        g = str(geo).lower()
        if g and g in blob:
            score += 10
            reasons.append({"code": "geography", "value": geo, "points": 10, "kind": "inference"})

    for rule in icp.get("exclude_rules") or []:
        value = str(rule.get("value") if isinstance(rule, dict) else rule).lower()
        if value and value in blob:
            score -= 40
            reasons.append({"code": "exclude_hit", "value": value, "points": -40, "kind": "verified"})

    size_band = str(icp.get("size_band") or "").lower()
    if size_band and size_band in blob:
        score += 10
        reasons.append({"code": "size_band", "value": size_band, "points": 10, "kind": "inference"})

    score = max(0, min(100, score))
    return {
        "icp_score": score,
        "icp_id": icp.get("id"),
        "icp_version": icp.get("version"),
        "icp_name": icp.get("name"),
        "reasons": reasons,
    }


def score_entity(
    store: Any,
    workspace_id: str,
    *,
    entity_type: str,
    entity_id: str,
    icp_id: str | None = None,
) -> dict[str, Any]:
    if entity_type == "lead":
        entity = store.get_lead(workspace_id, entity_id)
    elif entity_type == "account":
        entity = store.get_account(workspace_id, entity_id)
    elif entity_type == "contact":
        entity = store.get_contact(workspace_id, entity_id)
    else:
        return {"ok": False, "error": "unsupported_entity"}
    if not entity:
        return {"ok": False, "error": "not_found"}

    icp = get_icp(store, workspace_id, icp_id) if icp_id else get_active_icp(store, workspace_id)
    if not icp:
        return {"ok": False, "error": "no_active_icp"}

    result = score_against_icp(entity, icp)
    scores = dict(entity.get("scores") or {})
    scores["icp_score"] = result["icp_score"]
    scores["icp"] = result
    table = {"lead": "crm_leads", "account": "crm_accounts", "contact": "crm_contacts"}[entity_type]
    with store._lock:
        store._conn.execute(
            f"""
            UPDATE {table}
            SET scores = ?, icp_id = ?, icp_version = ?, updated_at = datetime('now')
            WHERE workspace_id = ? AND id = ?
            """,
            (json.dumps(scores), icp["id"], int(icp["version"]), workspace_id, entity_id),
        )
        store._conn.commit()
    return {"ok": True, **result, "entity_type": entity_type, "entity_id": entity_id}


def generate_account_brief(
    store: Any,
    workspace_id: str,
    *,
    entity_type: str,
    entity_id: str,
    icp_id: str | None = None,
) -> dict[str, Any]:
    scored = score_entity(store, workspace_id, entity_type=entity_type, entity_id=entity_id, icp_id=icp_id)
    if not scored.get("ok"):
        return scored
    if entity_type == "lead":
        entity = store.get_lead(workspace_id, entity_id)
    elif entity_type == "account":
        entity = store.get_account(workspace_id, entity_id)
    else:
        entity = store.get_contact(workspace_id, entity_id)

    provenance = store.list_provenance(workspace_id, entity_type=entity_type, entity_id=entity_id)
    evidence = [
        {
            "field": p.get("field_name"),
            "source": p.get("adapter"),
            "url": p.get("source_url"),
            "id": p.get("source_record_id"),
            "kind": p.get("kind"),
        }
        for p in provenance[:20]
    ]
    pains = [
        r for r in scored.get("reasons") or [] if r.get("code") in {"include_rule", "keyword_hit"}
    ]
    angle = None
    if pains:
        angle = f"Lead with {pains[0].get('value')} fit vs ICP {scored.get('icp_name')}"
    brief = {
        "company_summary": entity.get("company_name") or entity.get("name") or entity.get("display_name"),
        "icp_score": scored.get("icp_score"),
        "icp_version": scored.get("icp_version"),
        "pains": pains,
        "suggested_angle": angle,
        "evidence": evidence,
        "labels": {
            "inference_vs_verified": [
                {"reason": r.get("code"), "kind": r.get("kind")} for r in scored.get("reasons") or []
            ]
        },
    }
    return {"ok": True, "brief": brief, "score": scored}


def mass_attach_briefs(
    store: Any,
    workspace_id: str,
    *,
    entity_ids: list[dict[str, str]],
    actor_id: str | None = None,
    force: bool = False,
    approval_id: str | None = None,
) -> dict[str, Any]:
    gate = gate_or_approve(
        workspace_id,
        kind="mass_account_brief",
        subject=f"Mass attach {len(entity_ids)} account briefs",
        payload={"count": len(entity_ids)},
        object_type="brief_batch",
        object_id=None,
        actor_id=actor_id,
        force=force,
        approval_id=approval_id,
    )
    if gate.get("blocked"):
        return {"ok": False, "blocked": True, "approval": gate.get("approval")}
    briefs = []
    for item in entity_ids:
        briefs.append(
            generate_account_brief(
                store,
                workspace_id,
                entity_type=item.get("entity_type") or "lead",
                entity_id=str(item.get("entity_id")),
            )
        )
    return {"ok": True, "briefs": briefs}


def sort_leads_by_icp(store: Any, workspace_id: str) -> list[dict[str, Any]]:
    leads = store.list_leads(workspace_id, limit=1000)
    def key(lead: dict[str, Any]) -> float:
        scores = lead.get("scores") or {}
        if isinstance(scores, dict):
            return float(scores.get("icp_score") or 0)
        return 0.0
    return sorted(leads, key=key, reverse=True)
