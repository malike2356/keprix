"""Soft Wall gates for CRM risky writes (reuse Soft Wall, no parallel approvals)."""

from __future__ import annotations

import json
import os
from typing import Any

from keprix.outreach.ops import get_outreach_ops_store

# Gates that require Soft Wall when enabled (workspace default: on).
CRM_GATES = frozenset(
    {
        "apply_enrichment",
        "sheet.preprocess.apply",
        "approve_list_enroll",
        "crm.list.enroll",
        "stage_customer_paying",
        "nurture_plan_adjust",
        "merge_identity",
        "kill_switch_off",
        "budget_raise",
        "mass_update",
        "delete",
        "suppress_undo",
        "outbox_retry",
        "suppress_bulk_import",
        "materialize_discovery_list",
        "discovery_homepage_fetch",
        "social_oauth_connect",
        "property_portal_enable",
        "crm_subject_export",
        "crm_subject_erasure",
        "consent_policy_change",
        "icp_activate",
        "deal_reassign_paying",
        "crm_integration_import",
        "experiment_promote_winner",
        "locale_template_publish",
        "channel_template_approve",
        "first_whatsapp_sms_send",
        "whatsapp_sms_enable",
        "data_quality_reverify",
        "mass_account_brief",
        "voice_transcript_share",
        "property_portal_checklist",
        "social_api_sync",
        "crm_demo_purge",
        "lead_convert_contact",
        "funnel_orchestrate",
        "funnel_nba_execute",
        "funnel_draft_reply",
        "funnel_request_approval",
        "channel_journey_campaign",
        "nurture_branch_sequence",
    }
)

# Gates that stay on even when KEPRIX_CRM_SOFT_WALL is loosened (high-risk).
CRM_ALWAYS_ON_GATES = frozenset(
    {
        "approve_list_enroll_high_risk",
        "first_whatsapp_sms_send",
    }
)

PAYING_STAGES = frozenset({"customer", "paying"})


def soft_wall_gates_enabled(workspace_id: str | None = None) -> bool:
    raw = os.environ.get("KEPRIX_CRM_SOFT_WALL", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _ops():
    return get_outreach_ops_store()


def ensure_crm_approval_columns() -> None:
    """Extend Soft Wall approvals with typed CRM payload (additive)."""
    ops = _ops()
    cols = {r[1] for r in ops._conn.execute("PRAGMA table_info(outreach_approvals)").fetchall()}
    alters: list[str] = []
    if "approval_kind" not in cols:
        alters.append("ALTER TABLE outreach_approvals ADD COLUMN approval_kind TEXT")
    if "payload_json" not in cols:
        alters.append("ALTER TABLE outreach_approvals ADD COLUMN payload_json TEXT")
    if "object_type" not in cols:
        alters.append("ALTER TABLE outreach_approvals ADD COLUMN object_type TEXT")
    if "object_id" not in cols:
        alters.append("ALTER TABLE outreach_approvals ADD COLUMN object_id TEXT")
    if not alters:
        return
    with ops._lock:
        for stmt in alters:
            ops._conn.execute(stmt)
        ops._conn.commit()


def create_crm_approval(
    workspace_id: str,
    *,
    kind: str,
    subject: str,
    payload: dict[str, Any],
    object_type: str | None = None,
    object_id: str | None = None,
    recipient: str | None = None,
    actor_id: str | None = None,
) -> dict[str, Any]:
    ensure_crm_approval_columns()
    ops = _ops()
    body = json.dumps(
        {
            "kind": kind,
            "payload": payload,
            "object_type": object_type,
            "object_id": object_id,
            "actor_id": actor_id,
            "version": 1,
        },
        default=str,
    )
    approval = ops.create_approval(
        workspace_id,
        recipient=recipient or f"crm:{kind}",
        subject=subject[:200],
        draft_body=body,
        lead_id=object_id if object_type == "lead" else None,
        campaign_id=payload.get("campaign_id"),
    )
    # Stamp CRM columns when present.
    with ops._lock:
        ops._conn.execute(
            """
            UPDATE outreach_approvals
            SET approval_kind = ?, payload_json = ?, object_type = ?, object_id = ?
            WHERE id = ? AND workspace_id = ?
            """,
            (
                kind,
                json.dumps(payload, default=str),
                object_type,
                object_id,
                approval["id"],
                workspace_id,
            ),
        )
        ops._conn.commit()
    row = ops._fetchone(
        "SELECT * FROM outreach_approvals WHERE id = ? AND workspace_id = ?",
        (approval["id"], workspace_id),
    )
    return _with_deeplink(row or approval)


def _with_deeplink(approval: dict[str, Any]) -> dict[str, Any]:
    out = dict(approval)
    aid = out.get("id")
    obj_type = out.get("object_type")
    obj_id = out.get("object_id")
    out["deep_link"] = f"/crm?approval={aid}"
    if obj_type and obj_id:
        if str(obj_type) == "enrichment_job":
            out["object_deep_link"] = f"/crm/enrich?job={obj_id}&approval={aid}"
            out["deep_link"] = out["object_deep_link"]
        elif str(obj_type) == "discovery_job":
            out["object_deep_link"] = f"/crm/jobs/{obj_id}?approval={aid}"
            out["deep_link"] = out["object_deep_link"]
        elif str(obj_type) == "demo_seed":
            out["object_deep_link"] = f"/crm/settings#demo-data&approval={aid}"
            out["deep_link"] = out["object_deep_link"]
        else:
            plural = {
                "lead": "leads",
                "contact": "contacts",
                "account": "accounts",
                "deal": "deals",
                "list": "lists",
                "merge_suggestion": "merges",
            }.get(str(obj_type), obj_type)
            out["object_deep_link"] = f"/crm/{plural}/{obj_id}?approval={aid}"
    if isinstance(out.get("payload_json"), str):
        try:
            out["payload"] = json.loads(out["payload_json"])
        except json.JSONDecodeError:
            out["payload"] = {}
    return out


def pending_crm_approvals(workspace_id: str, *, kind: str | None = None) -> list[dict[str, Any]]:
    ensure_crm_approval_columns()
    ops = _ops()
    rows = ops.list_approvals(workspace_id, status="pending")
    out: list[dict[str, Any]] = []
    for row in rows:
        if row.get("approval_kind") or str(row.get("recipient") or "").startswith("crm:"):
            if kind and row.get("approval_kind") != kind and not str(row.get("recipient") or "").endswith(kind):
                continue
            out.append(_with_deeplink(row))
    return out


def resolve_crm_approval(
    workspace_id: str,
    approval_id: str,
    *,
    status: str,
) -> dict[str, Any] | None:
    ensure_crm_approval_columns()
    ops = _ops()
    row = ops.resolve_approval(workspace_id, approval_id, status)
    return _with_deeplink(row) if row else None


def gate_or_approve(
    workspace_id: str,
    *,
    kind: str,
    subject: str,
    payload: dict[str, Any],
    object_type: str | None = None,
    object_id: str | None = None,
    actor_id: str | None = None,
    force: bool = False,
    approval_id: str | None = None,
    always_require: bool = False,
) -> dict[str, Any]:
    """Return {blocked, approval} or {allowed: True} when gate passes.

    ``always_require`` forces Soft Wall even when workspace gates are loosened
    (used for health/social care enroll). ``force`` still bypasses unless
    ``always_require`` is set.
    """
    if always_require or kind in CRM_ALWAYS_ON_GATES:
        # High-risk: ignore loosened workspace Soft Wall and ignore force bypass.
        pass
    elif not soft_wall_gates_enabled(workspace_id) or force:
        return {"allowed": True, "blocked": False}

    if approval_id:
        ops = _ops()
        existing = ops._fetchone(
            "SELECT * FROM outreach_approvals WHERE id = ? AND workspace_id = ?",
            (approval_id, workspace_id),
        )
        if existing and existing.get("status") == "approved":
            return {"allowed": True, "blocked": False, "approval": _with_deeplink(existing)}
        if existing and existing.get("status") == "pending":
            return {
                "allowed": False,
                "blocked": True,
                "error_code": "soft_wall_pending",
                "approval": _with_deeplink(existing),
            }
        return {
            "allowed": False,
            "blocked": True,
            "error_code": "soft_wall_approval_invalid",
            "approval": None,
        }

    approval = create_crm_approval(
        workspace_id,
        kind=kind,
        subject=subject,
        payload=payload,
        object_type=object_type,
        object_id=object_id,
        actor_id=actor_id,
    )
    return {
        "allowed": False,
        "blocked": True,
        "error_code": "soft_wall_required",
        "approval": approval,
    }
