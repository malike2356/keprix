"""A/B reply auto-attribution + ICP auto-rescore (prompt 09).

Two wiring gaps closed here:
1. A reply must be attributed to the variant that sent it. attribute_reply
   resolves the exact outbound message (outreach store), its experiment + sticky
   variant (crm store), and records the reply metric automatically.
2. A lead must be re-scored at the end of every enrichment stage, not only on
   explicit score_entity. rescore_after_enrichment re-runs ICP scoring, logs the
   delta + reason, and returns a suppression recommendation.

Two stores are involved: OutreachStore (outreach_messages/enrollments/sequences)
and CrmStore (crm_leads/crm_experiments/crm_icp_definitions). Both are passed
explicitly. Analytics informs; it never auto-selects sends. Soft Wall approves.
"""

from __future__ import annotations

from typing import Any

from keprix.crm.store import CrmStore


def _outreach_email(outreach_lead: dict[str, Any]) -> str:
    email = outreach_lead.get("email")
    if isinstance(email, list):
        for item in email:
            if isinstance(item, dict) and item.get("address"):
                return str(item["address"])
            if isinstance(item, str) and item:
                return item
        return ""
    return str(email or "")


def _running_experiment_for_sequence(
    crm_store: CrmStore, workspace_id: str, sequence_id: str
) -> dict[str, Any] | None:
    ws = crm_store._require_workspace(workspace_id)
    rows = crm_store._conn.execute(
        "SELECT * FROM crm_experiments WHERE workspace_id = ? AND sequence_id = ? AND status = 'running' ORDER BY created_at DESC LIMIT 1",
        (ws, sequence_id),
    ).fetchall()
    return dict(rows[0]) if rows else None


def attribute_reply(
    outreach_store: Any,
    crm_store: CrmStore,
    workspace_id: str,
    lead_id: str,
    *,
    matched_message_id: str | None = None,
) -> dict[str, Any]:
    """Attribute an inbound reply to the variant that sent the last message.

    Resolves the exact message (not just the lead), so a lead enrolled in two
    campaigns only attributes to the most recent send.
    """
    ws = str(workspace_id or "").strip()
    outreach_lead = outreach_store.get_lead(ws, lead_id)
    if not outreach_lead:
        return {"ok": False, "error": "not_found"}

    message = None
    if matched_message_id:
        message = outreach_store.get_message(ws, matched_message_id)
    if message is None:
        # most recent sent message for this lead via its enrollments
        conn = getattr(outreach_store, "_conn", None)
        if conn is not None:
            rows = conn.execute(
                """
                SELECT m.* FROM outreach_messages m
                JOIN outreach_enrollments e ON e.id = m.enrollment_id
                WHERE e.workspace_id = ? AND e.lead_id = ? AND m.sent_at IS NOT NULL
                ORDER BY m.sent_at DESC, m.created_at DESC LIMIT 1
                """,
                (ws, lead_id),
            ).fetchall()
            message = dict(rows[0]) if rows else None
    if message is None:
        return {"ok": True, "status": "unmatched", "reason": "no sent message found"}

    enrollment = outreach_store.get_enrollment(
        str(message.get("enrollment_id") or ""), workspace_id=ws
    )
    sequence_id = str((enrollment or {}).get("sequence_id") or "")
    if not sequence_id:
        return {"ok": True, "status": "unmatched", "reason": "no sequence on enrollment"}

    experiment = _running_experiment_for_sequence(crm_store, ws, sequence_id)
    if experiment is None:
        return {"ok": True, "status": "unmatched", "reason": "no running experiment for sequence"}

    from keprix.crm.experiments import assign_variant, record_metric

    contact_key = _outreach_email(outreach_lead) or str(outreach_lead.get("id"))
    variant = assign_variant(crm_store, ws, str(experiment["id"]), contact_key)
    result = record_metric(
        crm_store, ws, str(experiment["id"]), variant=variant, metric="reply", amount=1
    )
    return {
        "ok": result.get("ok", False),
        "status": "attributed",
        "experiment_id": experiment["id"],
        "variant": variant,
        "message_id": message.get("id"),
    }


def rescore_after_enrichment(
    crm_store: CrmStore,
    workspace_id: str,
    lead_id: str,
    *,
    reason: str,
    icp_id: str | None = None,
    suppress_below: int | None = None,
) -> dict[str, Any]:
    """Re-score a lead against its active ICP and log any delta.

    Returns old/new score and whether the suppression threshold was crossed.
    Does NOT send or suppress on its own; the send layer enforces the
    recommendation.
    """
    from keprix.crm.icp import get_active_icp, get_icp
    from keprix.crm.icp_scoring import score_entity

    ws = crm_store._require_workspace(workspace_id)
    lead = crm_store.get_lead(ws, lead_id)
    if not lead:
        return {"ok": False, "error": "not_found"}

    active = get_icp(crm_store, ws, icp_id) if icp_id else get_active_icp(crm_store, ws)
    if not active:
        return {"ok": True, "status": "unchanged", "reason": "no_active_icp"}

    old_scores = lead.get("scores") or {}
    old_score = old_scores.get("icp_score") if isinstance(old_scores, dict) else None

    result = score_entity(crm_store, ws, entity_type="lead", entity_id=lead_id, icp_id=active["id"])
    if not result.get("ok"):
        return {"ok": True, "status": "unchanged", "reason": result.get("error")}

    new_score = result.get("icp_score")
    if old_score is not None and old_score == new_score:
        return {
            "ok": True,
            "status": "unchanged",
            "old": old_score,
            "new": new_score,
            "reason": reason,
        }

    crm_store.record_provenance(
        ws,
        entity_type="lead",
        entity_id=lead_id,
        field_name="icp_score",
        value=new_score,
        kind="observed",
        adapter=f"rescore:{reason}",
        verification_state="unverified",
    )

    recommend_suppress = False
    if suppress_below is not None and int(new_score) < int(suppress_below):
        recommend_suppress = True

    return {
        "ok": True,
        "status": "rescored",
        "old": old_score,
        "new": new_score,
        "delta": (int(new_score) - int(old_score)) if old_score is not None else None,
        "reason": reason,
        "recommend_suppress": recommend_suppress,
        "threshold": suppress_below,
    }
