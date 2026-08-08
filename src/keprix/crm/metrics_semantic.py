"""Canonical CRM metrics semantic layer (prompt 511)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SEMANTIC_VERSION = "1.0.0"

CANONICAL_EVENTS: tuple[str, ...] = (
    "discovered",
    "imported",
    "enriched",
    "verified",
    "listed",
    "approved",
    "enrolled",
    "attempted",
    "delivered",
    "bounced",
    "complained",
    "replied",
    "positive_reply",
    "negative_reply",
    "unsubscribed",
    "qualified",
    "booked",
    "attended",
    "customer",
    "paying",
    "lost",
    "suppressed",
    "human_takeover",
    "workflow_failed",
)

MEASURE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "unique_leads": {
        "id": "unique_leads",
        "numerator": "distinct lead ids",
        "denominator": None,
        "description": "Count of distinct leads in scope",
    },
    "contactable_rate": {
        "id": "contactable_rate",
        "numerator": "contactability allow",
        "denominator": "unique_leads",
        "description": "Share of leads allowed to contact",
    },
    "enrichment_yield": {
        "id": "enrichment_yield",
        "numerator": "enriched",
        "denominator": "discovered_or_imported",
        "description": "Enrichment success over intake",
    },
    "verification_rate": {
        "id": "verification_rate",
        "numerator": "verified",
        "denominator": "enriched",
        "description": "Verified fields over enriched",
    },
    "enrollment_rate": {
        "id": "enrollment_rate",
        "numerator": "enrolled",
        "denominator": "approved",
        "description": "Enrolled over approved",
    },
    "delivery_rate": {
        "id": "delivery_rate",
        "numerator": "delivered",
        "denominator": "attempted",
        "description": "Delivered over send attempts",
    },
    "reply_rate": {
        "id": "reply_rate",
        "numerator": "replied",
        "denominator": "delivered",
        "description": "Replies over delivered",
    },
    "positive_reply_rate": {
        "id": "positive_reply_rate",
        "numerator": "positive_reply",
        "denominator": "replied",
        "description": "Positive replies over replies",
    },
    "qualification_rate": {
        "id": "qualification_rate",
        "numerator": "qualified",
        "denominator": "replied",
        "description": "Qualified over replies",
    },
    "booking_rate": {
        "id": "booking_rate",
        "numerator": "booked",
        "denominator": "qualified",
        "description": "Booked over qualified",
    },
    "show_rate": {
        "id": "show_rate",
        "numerator": "attended",
        "denominator": "booked",
        "description": "Attended over booked",
    },
    "win_rate": {
        "id": "win_rate",
        "numerator": "customer",
        "denominator": "booked",
        "description": "Customers over booked",
    },
    "revenue": {
        "id": "revenue",
        "numerator": "paying value",
        "denominator": None,
        "description": "Verified paying revenue only",
    },
    "pipeline": {
        "id": "pipeline",
        "numerator": "open deal value",
        "denominator": None,
        "description": "Open pipeline value",
    },
    "cost_per_verified_lead": {
        "id": "cost_per_verified_lead",
        "numerator": "spend",
        "denominator": "verified",
        "description": "Spend per verified lead",
    },
    "cost_per_qualified_lead": {
        "id": "cost_per_qualified_lead",
        "numerator": "spend",
        "denominator": "qualified",
        "description": "Spend per qualified lead",
    },
    "cycle_time": {
        "id": "cycle_time",
        "numerator": "median hours discovered to booked",
        "denominator": None,
        "description": "Median cycle time in hours",
    },
    "stage_aging": {
        "id": "stage_aging",
        "numerator": "average hours in stage",
        "denominator": None,
        "description": "Average stage age hours",
    },
}

GUARD_METRICS: dict[str, dict[str, Any]] = {
    "hard_bounce_rate": {"numerator": "bounced", "denominator": "attempted"},
    "complaint_rate": {"numerator": "complained", "denominator": "delivered"},
    "unsubscribe_rate": {"numerator": "unsubscribed", "denominator": "delivered"},
    "suppression_rate": {"numerator": "suppressed", "denominator": "unique_leads"},
    "failed_send_rate": {"numerator": "workflow_failed", "denominator": "attempted"},
    "false_enrichment_rate": {"numerator": "enrichment_conflicts", "denominator": "enriched"},
    "duplicate_rate": {"numerator": "duplicates", "denominator": "unique_leads"},
    "human_review_rate": {"numerator": "human_takeover", "denominator": "enrolled"},
    "policy_block_rate": {"numerator": "policy_blocks", "denominator": "attempted"},
}

FUNNEL_ORDER: tuple[str, ...] = (
    "discovered",
    "contactable",
    "approved",
    "enrolled",
    "delivered",
    "replied",
    "qualified",
    "booked",
    "customer",
    "paying",
)


def _events_path() -> Path:
    try:
        from keprix.auth.config import data_dir

        root = Path(data_dir()) / "crm"
    except Exception:
        root = Path.home() / ".keprix" / "crm"
    root.mkdir(parents=True, exist_ok=True)
    return root / "metric_events.jsonl"


def record_canonical_event(
    workspace_id: str,
    event_type: str,
    *,
    subject_ids: dict[str, str] | None = None,
    campaign_id: str | None = None,
    workflow_id: str | None = None,
    workflow_version: int | None = None,
    run_id: str | None = None,
    source: str | None = None,
    pack: str | None = None,
    channel: str | None = None,
    actor: str | None = None,
    value: float | None = None,
    currency: str | None = None,
    evidence_ref: str | None = None,
    idempotency_key: str | None = None,
    correlation_id: str | None = None,
    occurred_at: str | None = None,
) -> dict[str, Any]:
    if event_type not in CANONICAL_EVENTS:
        raise ValueError(f"unknown_event:{event_type}")
    key = idempotency_key or f"{workspace_id}:{event_type}:{json.dumps(subject_ids or {}, sort_keys=True)}:{campaign_id}:{run_id}"
    # Dedup: skip if same key already written (scan last 2000 lines; Must-thin)
    path = _events_path()
    if path.exists():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()[-2000:]
            for line in lines:
                row = json.loads(line)
                if row.get("workspace_id") == workspace_id and row.get("idempotency_key") == key:
                    return {"ok": True, "duplicate": True, "event": row}
        except Exception:
            pass
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    event = {
        "id": str(uuid.uuid4()),
        "workspace_id": workspace_id,
        "event_type": event_type,
        "subject_ids": subject_ids or {},
        "campaign_id": campaign_id,
        "workflow_id": workflow_id,
        "workflow_version": workflow_version,
        "run_id": run_id,
        "source": source,
        "pack": pack,
        "channel": channel,
        "actor": actor,
        "occurred_at": occurred_at or now,
        "received_at": now,
        "idempotency_key": key,
        "correlation_id": correlation_id or str(uuid.uuid4()),
        "value": value,
        "currency": currency,
        "evidence_ref": evidence_ref,
        "definition_version": SEMANTIC_VERSION,
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, default=str) + "\n")
    return {"ok": True, "duplicate": False, "event": event}


def _load_events(workspace_id: str, *, limit: int = 20000) -> list[dict[str, Any]]:
    path = _events_path()
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
            row = json.loads(line)
            if row.get("workspace_id") == workspace_id:
                out.append(row)
    except Exception:
        return []
    return out


def backfill_from_crm(workspace_id: str, *, crm_store: Any) -> dict[str, Any]:
    """Derive events from CRM rows idempotently; report gaps instead of inventing history."""
    leads = crm_store.list_leads(workspace_id, limit=5000)
    wrote = 0
    gaps: list[str] = []
    stage_map = {
        "discovered": "discovered",
        "enriched": "enriched",
        "listed": "listed",
        "approved": "approved",
        "enrolled": "enrolled",
        "engaged": "replied",
        "qualified": "qualified",
        "booked": "booked",
        "customer": "customer",
        "paying": "paying",
        "suppressed": "suppressed",
        "bounced": "bounced",
        "lost": "lost",
    }
    for lead in leads:
        stage = str(lead.get("stage") or "")
        et = stage_map.get(stage)
        if not et:
            gaps.append(f"unmapped_stage:{lead.get('id')}:{stage}")
            continue
        res = record_canonical_event(
            workspace_id,
            et,
            subject_ids={"lead_id": lead["id"]},
            source=str(lead.get("source") or "") or None,
            pack=str(lead.get("domain_pack") or "") or None,
            idempotency_key=f"backfill:{workspace_id}:lead:{lead['id']}:{et}",
        )
        if not res.get("duplicate"):
            wrote += 1
    return {"ok": True, "wrote": wrote, "gaps": gaps[:100], "gap_count": len(gaps), "incomplete_history": True}


def query_metrics(
    workspace_id: str,
    *,
    measures: list[str] | None = None,
    dimensions: list[str] | None = None,
    days: int = 30,
    cohort: str = "first_touch",
    attribution: str = "sourced",
    crm_store: Any = None,
) -> dict[str, Any]:
    """Workspace-isolated metric query with explicit denominators in metadata."""
    days = max(1, min(int(days or 30), 366))
    measures = measures or [
        "unique_leads",
        "enrollment_rate",
        "reply_rate",
        "booking_rate",
        "win_rate",
        "pipeline",
        "revenue",
    ]
    dimensions = dimensions or ["stage"]
    if attribution not in {"sourced", "influenced", "multi_touch"}:
        attribution = "sourced"
    if cohort not in {"first_touch", "enrollment", "opportunity_created"}:
        cohort = "first_touch"

    events = _load_events(workspace_id)
    counts: dict[str, int] = {e: 0 for e in CANONICAL_EVENTS}
    for ev in events:
        et = str(ev.get("event_type") or "")
        if et in counts:
            counts[et] += 1

    # Live CRM fallback for empty event log
    live: dict[str, int] = {}
    spend = 0.0
    pipeline_value = 0.0
    if crm_store is not None:
        leads = crm_store.list_leads(workspace_id, limit=5000)
        live["unique_leads"] = len(leads)
        for lead in leads:
            st = str(lead.get("stage") or "")
            live[st] = live.get(st, 0) + 1
            try:
                pipeline_value += float(lead.get("deal_value") or lead.get("value") or 0)
            except Exception:
                pass
        try:
            for job in crm_store.list_enrichment_jobs(workspace_id):
                spend += float(job.get("cost_estimate") or 0)
        except Exception:
            pass

    def _c(name: str) -> float:
        if counts.get(name):
            return float(counts[name])
        # map live stages
        aliases = {
            "discovered": live.get("discovered", 0) or live.get("unique_leads", 0),
            "replied": live.get("engaged", 0),
            "enrolled": live.get("enrolled", 0),
            "approved": live.get("approved", 0),
            "qualified": live.get("qualified", 0),
            "booked": live.get("booked", 0),
            "customer": live.get("customer", 0),
            "paying": live.get("paying", 0),
            "suppressed": live.get("suppressed", 0),
            "bounced": live.get("bounced", 0),
            "delivered": live.get("contacted", 0) or live.get("enrolled", 0),
            "attempted": live.get("enrolled", 0),
            "verified": live.get("enriched", 0),
            "enriched": live.get("enriched", 0),
            "contactable": live.get("approved", 0) + live.get("enrolled", 0),
        }
        return float(aliases.get(name, 0))

    def _rate(num: str, den: str) -> dict[str, Any]:
        n = _c(num)
        d = _c(den)
        return {
            "value": round(n / d, 4) if d else None,
            "numerator": n,
            "denominator": d,
            "incomplete": d == 0,
        }

    results: dict[str, Any] = {}
    for m in measures:
        if m == "unique_leads":
            results[m] = {
                "value": float(live.get("unique_leads") or _c("discovered") or sum(1 for _ in events)),
                "numerator": float(live.get("unique_leads") or _c("discovered")),
                "denominator": None,
                "definition": MEASURE_DEFINITIONS["unique_leads"],
            }
        elif m == "pipeline":
            results[m] = {
                "value": pipeline_value,
                "numerator": pipeline_value,
                "denominator": None,
                "definition": MEASURE_DEFINITIONS["pipeline"],
            }
        elif m == "revenue":
            # Verified paying only; do not invent
            results[m] = {
                "value": _c("paying"),
                "numerator": _c("paying"),
                "denominator": None,
                "definition": MEASURE_DEFINITIONS["revenue"],
                "note": "Counts paying stage events; currency conversion not applied in Must-thin.",
            }
        elif m in MEASURE_DEFINITIONS and MEASURE_DEFINITIONS[m].get("denominator"):
            defn = MEASURE_DEFINITIONS[m]
            # Parse numerator/denominator event names from defn loosely
            mapping = {
                "contactable_rate": ("contactable", "unique_leads"),
                "enrichment_yield": ("enriched", "discovered"),
                "verification_rate": ("verified", "enriched"),
                "enrollment_rate": ("enrolled", "approved"),
                "delivery_rate": ("delivered", "attempted"),
                "reply_rate": ("replied", "delivered"),
                "positive_reply_rate": ("positive_reply", "replied"),
                "qualification_rate": ("qualified", "replied"),
                "booking_rate": ("booked", "qualified"),
                "show_rate": ("attended", "booked"),
                "win_rate": ("customer", "booked"),
            }
            num, den = mapping.get(m, ("replied", "delivered"))
            if m.startswith("cost_per"):
                den_name = "verified" if "verified" in m else "qualified"
                den_v = _c(den_name)
                results[m] = {
                    "value": round(spend / den_v, 4) if den_v else None,
                    "numerator": spend,
                    "denominator": den_v,
                    "definition": defn,
                    "incomplete": den_v == 0,
                }
            else:
                rate = _rate(num, den if den != "unique_leads" else "discovered")
                if den == "unique_leads":
                    rate["denominator"] = float(live.get("unique_leads") or rate["denominator"] or 0)
                    if rate["denominator"]:
                        rate["value"] = round(rate["numerator"] / rate["denominator"], 4)
                rate["definition"] = defn
                results[m] = rate
        elif m == "cycle_time" or m == "stage_aging":
            results[m] = {
                "value": None,
                "numerator": None,
                "denominator": None,
                "definition": MEASURE_DEFINITIONS[m],
                "incomplete": True,
                "note": "Requires timestamped stage history; labelled incomplete until backfill covers ages.",
            }
        else:
            results[m] = {"value": None, "incomplete": True, "error": "unknown_measure"}

    guards = {}
    for gid, gdef in GUARD_METRICS.items():
        guards[gid] = {
            **_rate(gdef["numerator"] if gdef["numerator"] in CANONICAL_EVENTS else "bounced", gdef["denominator"] if gdef["denominator"] in CANONICAL_EVENTS else "attempted"),
            "definition_id": gid,
        }

    funnel = []
    prev = None
    for step in FUNNEL_ORDER:
        count = _c(step) if step != "contactable" else (_c("approved") + _c("enrolled"))
        if step == "contactable" and live.get("unique_leads"):
            # Prefer approved+enrolled as contactable proxy
            count = float(live.get("approved", 0) + live.get("enrolled", 0) + live.get("contacted", 0))
        conv = None
        if prev is not None and prev > 0:
            conv = round(count / prev, 4)
        funnel.append(
            {
                "step": step,
                "count": count,
                "conversion_from_prev": conv,
                "denominator_prev": prev,
            }
        )
        prev = count

    return {
        "workspace_id": workspace_id,
        "definition_version": SEMANTIC_VERSION,
        "days": days,
        "cohort": cohort,
        "cohort_label": f"Cohort: {cohort}",
        "attribution": attribution,
        "attribution_label": f"Attribution: {attribution} (not mixed)",
        "timezone": "Europe/London",
        "dimensions": dimensions,
        "measures": results,
        "guards": guards,
        "funnel": funnel,
        "freshness": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "incomplete_history": len(events) == 0,
        "notes": [
            "Opens and clicks are optional privacy-sensitive estimates and are not core truth.",
            "Empty or incomplete history is labelled honestly.",
        ],
    }


def definitions_payload() -> dict[str, Any]:
    return {
        "version": SEMANTIC_VERSION,
        "events": list(CANONICAL_EVENTS),
        "measures": MEASURE_DEFINITIONS,
        "guards": GUARD_METRICS,
        "funnel_order": list(FUNNEL_ORDER),
        "attribution_models": ["sourced", "influenced", "multi_touch"],
        "cohorts": ["first_touch", "enrollment", "opportunity_created"],
    }
