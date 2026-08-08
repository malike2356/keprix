"""Interactive CRM pipeline board view model (prompt 507)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from keprix.crm.models import FORWARD_STAGES, TERMINAL_STAGES
from keprix.crm.stages import can_transition

BOARD_STAGES: tuple[str, ...] = FORWARD_STAGES + TERMINAL_STAGES

SAVED_VIEWS: dict[str, dict[str, Any]] = {
    "my_pipeline": {"label": "My pipeline", "filter": {"owner": "me"}},
    "needs_review": {"label": "Needs review", "filter": {"tag": "needs_review"}},
    "human_takeover": {"label": "Human takeover", "filter": {"human_owned": True}},
    "stale": {"label": "Stale", "filter": {"stale": True}},
    "awaiting_approval": {"label": "Awaiting approval", "filter": {"approval_pending": True}},
    "suppressed": {"label": "Suppressed", "filter": {"stage": "suppressed"}},
    "qualified": {"label": "Qualified", "filter": {"stage": "qualified"}},
}


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    raw = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _age_hours(value: Any) -> float | None:
    dt = _parse_ts(value)
    if not dt:
        return None
    return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0)


def _card_from_lead(lead: dict[str, Any], *, pending_ids: set[str]) -> dict[str, Any]:
    stage = str(lead.get("stage") or "discovered")
    scores = lead.get("scores") if isinstance(lead.get("scores"), dict) else {}
    fit = scores.get("fit") or scores.get("fit_score")
    engagement = scores.get("engagement") or scores.get("engagement_score")
    suppressed = stage in {"suppressed", "bounced", "do_not_contact"}
    human_owned = bool(lead.get("human_owned") or lead.get("assigned_human") or lead.get("takeover"))
    contactability = str(lead.get("contactability") or lead.get("contactability_verdict") or "unknown")
    deal_value = lead.get("deal_value") or lead.get("value") or lead.get("amount")
    return {
        "id": lead["id"],
        "entity_type": "lead",
        "title": str(lead.get("name") or lead.get("display_name") or lead.get("email") or lead["id"]),
        "subtitle": str(lead.get("company_name") or lead.get("domain") or ""),
        "stage": stage,
        "owner": lead.get("assigned_agent") or lead.get("owner_id"),
        "source": lead.get("source"),
        "domain_pack": lead.get("domain_pack"),
        "tags": lead.get("tags") or [],
        "fit_score": fit,
        "engagement_score": engagement,
        "last_touch_at": lead.get("last_touch_at"),
        "next_action": lead.get("next_action") or lead.get("next_action_at"),
        "run_state": lead.get("run_state") or lead.get("sequence_status"),
        "warnings": [
            *(["suppressed"] if suppressed else []),
            *(["human_owned"] if human_owned else []),
            *(["approval_pending"] if lead["id"] in pending_ids else []),
            *(["stale"] if (_age_hours(lead.get("last_touch_at")) or 0) > 72 else []),
        ],
        "consent_contactability": contactability,
        "deal_value": deal_value,
        "version": lead.get("version") or 1,
        "deep_links": {
            "record": f"/crm/leads/{lead['id']}",
            "activities": f"/crm/leads/{lead['id']}#activities",
            "pipeline": "/crm/pipeline",
        },
    }


def _card_from_deal(deal: dict[str, Any], *, pending_ids: set[str]) -> dict[str, Any]:
    stage = str(deal.get("stage") or "discovered")
    suppressed = stage in {"suppressed", "bounced", "do_not_contact"}
    human_owned = bool(deal.get("human_owned") or deal.get("takeover"))
    return {
        "id": deal["id"],
        "entity_type": "deal",
        "title": str(deal.get("name") or deal.get("title") or deal["id"]),
        "subtitle": str(deal.get("account_name") or deal.get("company_name") or ""),
        "stage": stage,
        "owner": deal.get("assigned_agent") or deal.get("owner_id"),
        "source": deal.get("source") or "deal",
        "domain_pack": deal.get("domain_pack"),
        "tags": deal.get("tags") or [],
        "fit_score": None,
        "engagement_score": None,
        "last_touch_at": deal.get("last_touch_at") or deal.get("updated_at"),
        "next_action": deal.get("next_action"),
        "run_state": deal.get("run_state"),
        "warnings": [
            *(["suppressed"] if suppressed else []),
            *(["human_owned"] if human_owned else []),
            *(["approval_pending"] if deal["id"] in pending_ids else []),
        ],
        "consent_contactability": str(deal.get("contactability") or "unknown"),
        "deal_value": deal.get("amount") or deal.get("value") or deal.get("deal_value"),
        "version": deal.get("version") or 1,
        "deep_links": {
            "record": f"/crm/deals/{deal['id']}",
            "activities": f"/crm/deals/{deal['id']}#activities",
            "pipeline": "/crm/pipeline",
        },
    }


def build_pipeline_board(
    workspace_id: str,
    *,
    crm_store: Any,
    filters: dict[str, Any] | None = None,
    saved_view: str | None = None,
    limit_per_lane: int = 50,
) -> dict[str, Any]:
    """Server view model for the Kanban board. Totals are accurate; cards may paginate."""
    filters = dict(filters or {})
    if saved_view and saved_view in SAVED_VIEWS:
        filters = {**SAVED_VIEWS[saved_view]["filter"], **filters}

    leads = crm_store.list_leads(workspace_id, limit=5000)
    deals: list[dict[str, Any]] = []
    try:
        deals = crm_store.list_deals(workspace_id, limit=2000)
    except Exception:
        deals = []
    pending_ids: set[str] = set()
    try:
        from keprix.crm.soft_wall import pending_crm_approvals

        for item in pending_crm_approvals(workspace_id):
            oid = str(item.get("object_id") or "")
            if oid:
                pending_ids.add(oid)
    except Exception:
        pass

    q = str(filters.get("q") or filters.get("search") or "").strip().lower()
    owner = filters.get("owner")
    source = filters.get("source")
    pack = filters.get("pack") or filters.get("domain_pack")
    stage_filter = filters.get("stage")
    tag = filters.get("tag")
    contactability = filters.get("contactability")
    human_owned = filters.get("human_owned")
    stale = filters.get("stale")
    approval_pending = filters.get("approval_pending")

    filtered: list[dict[str, Any]] = []
    for lead in leads:
        if stage_filter and str(lead.get("stage") or "") != stage_filter:
            continue
        if source and str(lead.get("source") or "") != str(source):
            continue
        if pack and str(lead.get("domain_pack") or "") != str(pack):
            continue
        if owner and owner != "me" and str(lead.get("assigned_agent") or "") != str(owner):
            continue
        if tag:
            tags = lead.get("tags") or []
            if tag not in tags and str(tag) not in [str(t) for t in tags]:
                continue
        if contactability:
            verdict = str(lead.get("contactability") or lead.get("contactability_verdict") or "")
            if verdict != str(contactability):
                continue
        if human_owned and not (lead.get("human_owned") or lead.get("takeover")):
            continue
        if approval_pending and lead.get("id") not in pending_ids:
            continue
        if stale and (_age_hours(lead.get("last_touch_at")) or 0) <= 72:
            continue
        if q:
            hay = " ".join(
                str(lead.get(k) or "")
                for k in ("name", "display_name", "company_name", "domain", "email", "id")
            ).lower()
            if q not in hay:
                continue
        filtered.append(lead)

    for deal in deals:
        if stage_filter and str(deal.get("stage") or "") != stage_filter:
            continue
        if q:
            hay = " ".join(
                str(deal.get(k) or "") for k in ("name", "title", "account_name", "company_name", "id")
            ).lower()
            if q not in hay:
                continue
        # Represent deals as synthetic cards alongside leads
        filtered.append({**deal, "_entity_type": "deal"})

    lanes: list[dict[str, Any]] = []
    columns: dict[str, list[dict[str, Any]]] = {}
    for stage in BOARD_STAGES:
        stage_rows = [l for l in filtered if str(l.get("stage") or "discovered") == stage]
        total = len(stage_rows)
        ages = [_age_hours(l.get("last_touch_at") or l.get("updated_at") or l.get("created_at")) for l in stage_rows]
        ages_n = [a for a in ages if a is not None]
        avg_age = round(sum(ages_n) / len(ages_n), 1) if ages_n else None
        value_sum = 0.0
        for l in stage_rows:
            try:
                value_sum += float(l.get("deal_value") or l.get("value") or l.get("amount") or 0)
            except Exception:
                pass
        cards = []
        for row in stage_rows[:limit_per_lane]:
            if row.get("_entity_type") == "deal":
                cards.append(_card_from_deal(row, pending_ids=pending_ids))
            else:
                cards.append(_card_from_lead(row, pending_ids=pending_ids))
        columns[stage] = cards
        lanes.append(
            {
                "stage": stage,
                "label": stage.replace("_", " "),
                "count": total,
                "shown": len(cards),
                "truncated": total > len(cards),
                "total_value": value_sum,
                "average_age_hours": avg_age,
                "conversion_health": "ok" if stage not in TERMINAL_STAGES else "terminal",
            }
        )

    return {
        "workspace_id": workspace_id,
        "view_model": "pipeline_board",
        "stages": list(BOARD_STAGES),
        "lanes": lanes,
        "columns": columns,
        "filters": filters,
        "saved_view": saved_view,
        "saved_views": [{"id": k, **v} for k, v in SAVED_VIEWS.items()],
        "limit_per_lane": limit_per_lane,
        "totals": {"cards": len(filtered), "lanes": len(lanes)},
        "deep_links": {"table": "/crm/leads", "deals": "/crm/deals", "analytics": "/crm/analytics"},
    }


def preview_stage_transition(
    workspace_id: str,
    *,
    crm_store: Any,
    entity_type: str,
    entity_id: str,
    to_stage: str,
    human_confirmed: bool = False,
    soft_wall_approved: bool = False,
    expected_version: int | None = None,
) -> dict[str, Any]:
    """Validate a board move before commit. Identical rules for drag and keyboard."""
    getters = {
        "lead": crm_store.get_lead,
        "contact": crm_store.get_contact,
        "deal": crm_store.get_deal,
    }
    get_fn = getters.get(entity_type)
    if not get_fn:
        return {"allowed": False, "reason_code": "unsupported_entity", "safe_next": "Use lead, contact, or deal."}
    row = get_fn(workspace_id, entity_id)
    if not row:
        return {"allowed": False, "reason_code": "not_found", "safe_next": "Reload the board."}
    if expected_version is not None and int(row.get("version") or 1) != int(expected_version):
        return {
            "allowed": False,
            "reason_code": "version_conflict",
            "safe_next": "Compare and reload before moving again.",
            "server_version": row.get("version"),
            "client_version": expected_version,
        }
    from_stage = str(row.get("stage") or "discovered")
    stage = str(to_stage)
    if stage in {"suppressed", "do_not_contact"} and not human_confirmed:
        # Allowed but flagged: suppressed should not re-enter automation casually
        pass
    if from_stage in {"suppressed", "do_not_contact"} and stage not in TERMINAL_STAGES:
        if not (human_confirmed or soft_wall_approved):
            return {
                "allowed": False,
                "reason_code": "suppressed_requires_human",
                "from_stage": from_stage,
                "to_stage": stage,
                "safe_next": "Open Soft Wall or mark human confirmed before reactivating.",
            }
    ok, code = can_transition(
        from_stage,
        stage,
        human_confirmed=human_confirmed,
        soft_wall_approved=soft_wall_approved,
    )
    if not ok:
        return {
            "allowed": False,
            "reason_code": code or "blocked",
            "from_stage": from_stage,
            "to_stage": stage,
            "safe_next": "Use Soft Wall approval for gated customer/paying or skip moves.",
        }
    return {
        "allowed": True,
        "from_stage": from_stage,
        "to_stage": stage,
        "entity": {"id": entity_id, "type": entity_type, "version": row.get("version")},
        "requires_soft_wall": stage in {"customer", "paying"} and not soft_wall_approved,
    }


def commit_stage_transition(
    workspace_id: str,
    *,
    crm_store: Any,
    entity_type: str,
    entity_id: str,
    to_stage: str,
    human_confirmed: bool = False,
    soft_wall_approved: bool = False,
    force: bool = False,
    expected_version: int | None = None,
    actor_id: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    preview = preview_stage_transition(
        workspace_id,
        crm_store=crm_store,
        entity_type=entity_type,
        entity_id=entity_id,
        to_stage=to_stage,
        human_confirmed=human_confirmed,
        soft_wall_approved=soft_wall_approved,
        expected_version=expected_version,
    )
    if not preview.get("allowed"):
        return {"ok": False, **preview}
    if preview.get("requires_soft_wall") and not soft_wall_approved and not force:
        from keprix.crm.soft_wall import gate_or_approve

        gate = gate_or_approve(
            workspace_id,
            kind="stage_customer_paying",
            subject=f"Promote {entity_type} {entity_id} to {to_stage}",
            payload={"entity_type": entity_type, "entity_id": entity_id, "to": to_stage},
            object_type=entity_type,
            object_id=entity_id,
            actor_id=actor_id,
            force=force,
        )
        if gate.get("blocked"):
            return {
                "ok": False,
                "blocked": True,
                "reason_code": "soft_wall_required",
                "approval": gate.get("approval"),
                "safe_next": "Approve the Soft Wall item, then retry the move.",
            }
        soft_wall_approved = True

    from keprix.crm.stages import StageTransitionError, apply_stage

    try:
        result = apply_stage(
            crm_store,
            workspace_id,
            entity_type=entity_type,
            entity_id=entity_id,
            to_stage=to_stage,
            human_confirmed=human_confirmed,
            soft_wall_approved=soft_wall_approved,
            force=force,
            actor_type="user",
            actor_id=actor_id,
            reason=reason or "pipeline_board",
        )
    except StageTransitionError as exc:
        return {"ok": False, "allowed": False, "reason_code": exc.code, "safe_next": str(exc)}
    return {"ok": True, "blocked": False, **result}
