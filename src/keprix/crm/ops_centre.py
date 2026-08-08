"""Real-time visual operations centre view model (prompt 513)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from keprix.crm.run_events import list_runs


DEFAULT_ALERT_RULES: list[dict[str, Any]] = [
    {"id": "complaint_spike", "severity": "high", "label": "Complaint spike", "threshold": 0.001},
    {"id": "hard_bounce_spike", "severity": "high", "label": "Hard bounce spike", "threshold": 0.05},
    {"id": "duplicate_send_risk", "severity": "high", "label": "Duplicate send risk", "threshold": 1},
    {"id": "suppression_failure", "severity": "high", "label": "Suppression failure", "threshold": 1},
    {"id": "sender_domain_failure", "severity": "high", "label": "Sender domain failure", "threshold": 1},
    {"id": "budget_breach", "severity": "high", "label": "Budget breach", "threshold": 1},
    {"id": "cross_workspace_denial", "severity": "high", "label": "Cross-workspace denial anomaly", "threshold": 1},
    {"id": "stuck_approval", "severity": "medium", "label": "Stuck approval", "threshold": 1},
    {"id": "dead_letter_growth", "severity": "medium", "label": "Dead-letter growth", "threshold": 5},
    {"id": "adapter_policy_block", "severity": "medium", "label": "Adapter policy block", "threshold": 1},
]


def build_ops_centre(workspace_id: str, *, crm_store: Any) -> dict[str, Any]:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    approvals = []
    try:
        from keprix.crm.soft_wall import pending_crm_approvals

        approvals = pending_crm_approvals(workspace_id)
    except Exception:
        approvals = []

    inbox = []
    try:
        inbox = crm_store.list_inbox(workspace_id) if hasattr(crm_store, "list_inbox") else []
    except Exception:
        inbox = []

    outbox = []
    dead = 0
    try:
        outbox = crm_store.list_outbox(workspace_id) if hasattr(crm_store, "list_outbox") else []
        dead = sum(1 for o in outbox if str(o.get("status") or "") == "dead_letter")
    except Exception:
        pass

    kills = []
    try:
        kills = crm_store.list_kill_switches(workspace_id)
    except Exception:
        kills = []

    deliverability = {}
    try:
        from keprix.crm.deliverability import compute_deliverability_snapshot

        deliverability = compute_deliverability_snapshot(crm_store, workspace_id)
    except Exception:
        deliverability = {}

    runs = list_runs(workspace_id, limit=30)
    active_runs = [r for r in runs if str(r.get("status") or "") in {"active", "waiting", "approval_required", "ready"}]
    failed_nodes = []
    for r in runs:
        for nid, st in (r.get("node_states") or {}).items():
            if str(st.get("state") or "") == "failed":
                failed_nodes.append(
                    {
                        "run_id": r["id"],
                        "node_id": nid,
                        "label": st.get("label"),
                        "href": f"/crm/runs/{r['id']}?node={nid}",
                    }
                )

    human_takeover = [i for i in inbox if str(i.get("status") or "") in {"claimed", "human", "takeover"}]
    replies = [i for i in inbox if str(i.get("kind") or i.get("type") or "") in {"reply", "replied", ""}][:20]

    alerts: list[dict[str, Any]] = []
    breaches = list(deliverability.get("breaches") or [])
    for b in breaches:
        alerts.append(
            {
                "id": f"deliv_{b}",
                "rule_id": "sender_domain_failure" if "domain" in str(b) else "complaint_spike",
                "severity": "high",
                "label": str(b),
                "acknowledged": False,
                "href": "/crm/deliverability",
                "evidence": {"deliverability": True},
            }
        )
    if dead >= 5:
        alerts.append(
            {
                "id": "dead_letter",
                "rule_id": "dead_letter_growth",
                "severity": "medium",
                "label": f"Dead letters: {dead}",
                "acknowledged": False,
                "href": "/crm/outbox",
                "evidence": {"dead_letter_count": dead},
            }
        )
    stuck = [a for a in approvals if a]
    if len(stuck) >= 1:
        alerts.append(
            {
                "id": "stuck_approvals",
                "rule_id": "stuck_approval",
                "severity": "medium",
                "label": f"Pending Soft Wall approvals: {len(stuck)}",
                "acknowledged": False,
                "href": "/crm",
                "evidence": {"count": len(stuck)},
            }
        )
    for ks in kills:
        if ks.get("enabled"):
            alerts.append(
                {
                    "id": f"kill_{ks.get('id') or ks.get('scope')}",
                    "rule_id": "budget_breach",
                    "severity": "high",
                    "label": f"Kill switch active: {ks.get('scope')}",
                    "acknowledged": False,
                    "href": "/crm/settings",
                    "evidence": ks,
                }
            )

    return {
        "workspace_id": workspace_id,
        "generated_at": now,
        "transport": {
            "preferred": "polling",
            "polling_interval_ms": 5000,
            "realtime_topics": [
                "pipeline_changes",
                "run_events",
                "approvals",
                "replies",
                "human_tasks",
                "adapter_health",
                "budgets",
                "kill_switches",
            ],
            "note": "Must-thin uses authenticated polling with last-updated time. WebSocket topics are reserved; reconnect must refresh snapshot.",
            "degraded": False,
            "last_updated": now,
        },
        "panels": {
            "active_runs": [
                {
                    "id": r["id"],
                    "status": r.get("status"),
                    "workflow_id": r.get("workflow_id"),
                    "href": f"/crm/runs/{r['id']}",
                }
                for r in active_runs
            ],
            "waiting_approvals": [
                {
                    "id": a.get("id"),
                    "subject": a.get("subject"),
                    "kind": a.get("kind"),
                    "href": a.get("object_deep_link") or "/crm",
                }
                for a in approvals[:50]
            ],
            "human_takeover": human_takeover[:50],
            "overdue_tasks": [],
            "new_replies": replies,
            "failed_nodes": failed_nodes[:50],
            "provider_health": deliverability.get("checklist") or {},
            "spend_budget": {"breaches": breaches},
            "deliverability_guardrails": {
                "block_cold_send": deliverability.get("soft_wall_block_cold_send"),
                "rates": deliverability.get("rates") or {},
            },
            "kill_switches": kills,
        },
        "alerts": alerts,
        "alert_rules": DEFAULT_ALERT_RULES,
        "presence": {
            "advisory_only": True,
            "note": "Presence is advisory; durable version checks remain required for edits.",
        },
        "telegram": {
            "actions": ["approve", "reject", "pause", "cancel", "assign", "open_in_web"],
            "signed_expiring_single_use": True,
            "sensitive_detail_in_web_only": True,
        },
        "notification_preferences": {
            "channels": ["web", "telegram"],
            "mandatory_safety_alerts": True,
            "cannot_silently_disable_safety": True,
        },
    }
