"""Funnel analytics metrics and digests (prompt 447)."""

from __future__ import annotations

from typing import Any

FUNNEL_METRICS = (
    "lists_created",
    "leads_discovered",
    "enrolled",
    "replied",
    "booked",
    "customers",
    "paying",
    "complaints",
    "unsubscribes",
    "enrichment_cost",
)

METRIC_PREFIX = "crm_funnel_"


def record_funnel_event(
    workspace_id: str,
    metric: str,
    value: float = 1.0,
    *,
    campaign_id: str | None = None,
    pack: str | None = None,
    labels: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    name = metric if metric.startswith("crm_funnel_") else f"{METRIC_PREFIX}{metric}"
    short = name.replace(METRIC_PREFIX, "")
    if short not in FUNNEL_METRICS and metric not in FUNNEL_METRICS:
        # still record custom
        pass
    try:
        from keprix.aiva_analytics.metrics import record_metric

        return record_metric(
            workspace_id,
            name,
            float(value),
            labels={
                "workspace_id": workspace_id,
                "campaign_id": campaign_id or "",
                "pack": pack or "",
                **(labels or {}),
            },
        )
    except Exception:
        return None


def funnel_snapshot(
    workspace_id: str,
    *,
    campaign_id: str | None = None,
    pack: str | None = None,
    crm_store: Any = None,
    days: int = 30,
) -> dict[str, Any]:
    """Live funnel numbers; empty workspace returns zeros (no demo data)."""
    if crm_store is None:
        from keprix.crm.store import get_crm_store

        crm_store = get_crm_store()

    leads = crm_store.list_leads(workspace_id, limit=5000)
    contacts = crm_store.list_contacts(workspace_id, limit=5000)
    lists = crm_store.list_lists(workspace_id, limit=5000)
    deals = crm_store.list_deals(workspace_id, limit=5000)
    suppressions = crm_store.list_suppressions(workspace_id, limit=5000)
    jobs = []
    try:
        jobs = crm_store.list_discovery_jobs(workspace_id) if hasattr(crm_store, "list_discovery_jobs") else []
    except Exception:
        jobs = []
    enrich_jobs = []
    try:
        enrich_jobs = crm_store.list_enrichment_jobs(workspace_id) if hasattr(crm_store, "list_enrichment_jobs") else []
    except Exception:
        enrich_jobs = []

    def _stage_count(rows: list[dict[str, Any]], stage: str) -> int:
        return sum(1 for r in rows if str(r.get("stage") or "") == stage)

    def _filter(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = rows
        if pack:
            out = [r for r in out if str(r.get("domain_pack") or "") == pack]
        return out

    leads_f = _filter(leads)
    enrichment_cost = 0.0
    for job in enrich_jobs:
        try:
            enrichment_cost += float(job.get("cost_estimate") or job.get("token_estimate") or 0)
        except Exception:
            pass

    # Analytics store increments (optional overlay)
    analytics_counts: dict[str, float] = {m: 0.0 for m in FUNNEL_METRICS}
    try:
        from keprix.aiva_analytics.store import get_analytics_store

        store = get_analytics_store()
        events = store.list_events(workspace_id, limit=5000) if hasattr(store, "list_events") else []
        if not events and hasattr(store, "_fetchall"):
            events = store._fetchall(
                "SELECT * FROM aiva_analytics_events WHERE workspace_id = ? ORDER BY recorded_at DESC LIMIT 5000",
                (workspace_id,),
            )
        for ev in events or []:
            name = str(ev.get("metric_name") or "")
            if not name.startswith(METRIC_PREFIX):
                continue
            short = name[len(METRIC_PREFIX) :]
            if short not in analytics_counts:
                continue
            labels = ev.get("labels") or {}
            if isinstance(labels, str):
                import json

                try:
                    labels = json.loads(labels)
                except Exception:
                    labels = {}
            if campaign_id and str(labels.get("campaign_id") or "") not in {campaign_id, ""}:
                continue
            if pack and str(labels.get("pack") or "") not in {pack, ""}:
                continue
            analytics_counts[short] += float(ev.get("metric_value") or 0)
    except Exception:
        pass

    enrolled_live = _stage_count(leads_f, "enrolled") + _stage_count(leads_f, "contacted")
    unsub_live = sum(
        1 for s in suppressions if str(s.get("reason") or "").lower() in {"unsubscribe", "opt_out"}
    )
    counts = {
        "lists_created": len(lists) if lists else int(analytics_counts["lists_created"]),
        "leads_discovered": len(leads_f) if leads_f else int(analytics_counts["leads_discovered"]),
        "enrolled": enrolled_live if enrolled_live else int(analytics_counts["enrolled"]),
        "replied": _stage_count(leads_f, "engaged") or int(analytics_counts["replied"]),
        "booked": _stage_count(leads_f, "booked") or int(analytics_counts["booked"]),
        "customers": _stage_count(leads_f, "customer") or int(analytics_counts["customers"]),
        "paying": _stage_count(leads_f, "paying") or int(analytics_counts["paying"]),
        "complaints": int(analytics_counts["complaints"]),
        "unsubscribes": unsub_live if unsub_live else int(analytics_counts["unsubscribes"]),
        "enrichment_cost": enrichment_cost if enrichment_cost else float(analytics_counts["enrichment_cost"]),
    }

    # Prefer live CRM stage counts when non-zero; analytics fill gaps
    for key in FUNNEL_METRICS:
        if key == "enrichment_cost":
            continue
        if counts[key] == 0 and analytics_counts.get(key):
            counts[key] = int(analytics_counts[key])

    deliverability = {}
    try:
        from keprix.crm.deliverability import compute_deliverability_snapshot

        deliverability = compute_deliverability_snapshot(crm_store, workspace_id)
    except Exception:
        deliverability = {}

    return {
        "workspace_id": workspace_id,
        "period_days": days,
        "campaign_id": campaign_id,
        "pack": pack,
        "metrics": counts,
        "object_counts": {
            "leads": len(leads),
            "contacts": len(contacts),
            "lists": len(lists),
            "deals": len(deals),
            "discovery_jobs": len(jobs),
            "enrichment_jobs": len(enrich_jobs),
        },
        "deliverability_strip": {
            "breaches": deliverability.get("breaches") or [],
            "soft_wall_block_cold_send": deliverability.get("soft_wall_block_cold_send"),
            "href": "/crm/deliverability",
        },
        "deep_links": {
            "crm": "/crm",
            "lists": "/crm/lists",
            "jobs": "/crm/jobs",
            "inbox": "/crm/inbox",
            "deliverability": "/crm/deliverability",
            "analytics": "/analytics",
        },
    }


def build_digest(workspace_id: str, *, hours: int = 24, crm_store: Any = None) -> dict[str, Any]:
    snap = funnel_snapshot(workspace_id, crm_store=crm_store)
    pending = 0
    try:
        from keprix.crm.soft_wall import pending_crm_approvals

        pending = len(pending_crm_approvals(workspace_id))
    except Exception:
        pass
    replies = 0
    try:
        from keprix.crm.engagement import list_inbox

        if crm_store is None:
            from keprix.crm.store import get_crm_store

            crm_store = get_crm_store()
        replies = len(list_inbox(crm_store, workspace_id, status="open"))
    except Exception:
        pass

    message = (
        f"CRM digest ({hours}h) for {workspace_id}: "
        f"{snap['metrics']['leads_discovered']} leads, "
        f"{snap['metrics']['enrolled']} enrolled, "
        f"{snap['metrics']['replied']} engaged, "
        f"{snap['metrics']['booked']} booked, "
        f"{pending} Soft Wall pending, "
        f"{replies} inbox open. "
        f"Open /crm"
    )
    return {
        "workspace_id": workspace_id,
        "hours": hours,
        "message": message,
        "funnel": snap["metrics"],
        "pending_soft_wall": pending,
        "inbox_open": replies,
        "deep_links": snap["deep_links"],
        "deliverability": snap["deliverability_strip"],
    }
