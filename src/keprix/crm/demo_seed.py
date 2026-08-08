"""Local-only CRM demo seed for every core CRM model.

Hard-gated: never runs against live/production Keprix without explicit
local confirmation flags. Idempotent via external_source_id / demo keys.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from keprix.crm.models import (
    ContactabilityVerdict,
    CrmStage,
    MergeSuggestionStatus,
    OutboxStatus,
)

DEMO_TAG = "demo-seed"
DEMO_SOURCE_PREFIX = "demo-seed:"
ACTOR = "local-demo-seed"
DEMO_LIST_NAME = "Demo Warm Outbound"
DEMO_ICP_NAME = "Demo ICP"


class DemoSeedForbidden(RuntimeError):
    """Raised when seed is blocked for non-local / live environments."""


def assert_local_demo_seed_allowed() -> None:
    """Refuse to seed unless this is an explicit local demo run.

    Required:
      KEPRIX_ALLOW_CRM_DEMO_SEED=1
      KEPRIX_DEMO_SEED_CONFIRM=local-only

    Blocked when any production marker is present.
    """
    allow = os.environ.get("KEPRIX_ALLOW_CRM_DEMO_SEED", "").strip() == "1"
    confirm = os.environ.get("KEPRIX_DEMO_SEED_CONFIRM", "").strip().lower()
    if not allow or confirm != "local-only":
        raise DemoSeedForbidden(
            "CRM demo seed refused. Set KEPRIX_ALLOW_CRM_DEMO_SEED=1 and "
            "KEPRIX_DEMO_SEED_CONFIRM=local-only (local only; never live)."
        )

    env_markers = [
        os.environ.get("KEPRIX_ENV", ""),
        os.environ.get("APP_ENV", ""),
        os.environ.get("NODE_ENV", ""),
        os.environ.get("KEPRIX_DEPLOYMENT", ""),
        os.environ.get("KEPRIX_RUNTIME", ""),
    ]
    blocked = {"production", "prod", "staging", "live", "canary"}
    for raw in env_markers:
        if str(raw).strip().lower() in blocked:
            raise DemoSeedForbidden(f"CRM demo seed blocked by env marker: {raw}")

    instance = (
        os.environ.get("KEPRIX_INSTANCE_URL", "")
        or os.environ.get("KEPRIX_PUBLIC_URL", "")
        or os.environ.get("PUBLIC_URL", "")
    ).strip().lower()
    live_hosts = (
        "keprix.ai",
        "app.keprix",
        "cloud.keprix",
        "carinaai.uk",
        "hireaiva.com",
        "80.190.81.208",
    )
    if any(host in instance for host in live_hosts):
        raise DemoSeedForbidden(f"CRM demo seed blocked for instance URL: {instance}")

    if os.environ.get("KEPRIX_LIVE", "").strip().lower() in {"1", "true", "yes"}:
        raise DemoSeedForbidden("CRM demo seed blocked: KEPRIX_LIVE is set")


def _ext(key: str) -> str:
    return f"{DEMO_SOURCE_PREFIX}{key}"


def seed_crm_demo(
    workspace_id: str = "default",
    *,
    activate_icp: bool = True,
) -> dict[str, Any]:
    """Seed every CRM entity family into ``workspace_id`` (idempotent)."""
    assert_local_demo_seed_allowed()

    from keprix.crm import icp as icp_mod
    from keprix.crm.assignment import assign_owner
    from keprix.crm.experiments import create_experiment
    from keprix.crm.nice_schema import ensure_nice_schema
    from keprix.crm.store import get_crm_store

    store = get_crm_store()
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    summary: dict[str, Any] = {"workspace_id": ws, "created": {}, "reused": {}, "ids": {}}

    def _count(key: str, *, created: bool) -> None:
        bucket = "created" if created else "reused"
        summary[bucket][key] = int(summary[bucket].get(key, 0)) + 1

    def _by_ext(table: str, key: str) -> dict[str, Any] | None:
        return store._fetchone(
            f"SELECT * FROM {table} WHERE workspace_id = ? AND external_source_id = ? "
            "AND deleted_at IS NULL",
            (ws, _ext(key)),
        )

    # ── Accounts ──────────────────────────────────────────────
    account_specs = [
        ("harbour-homes", "Harbour Homes Ltd", "harbour-homes.example", CrmStage.DISCOVERED),
        ("northgate-prop", "Northgate Property", "northgate.example", CrmStage.ENRICHED),
        ("coastal-invest", "Coastal Invest PLC", "coastal-invest.example", CrmStage.QUALIFIED),
        ("paying-co", "Paying Customer Co", "paying.example", CrmStage.PAYING),
    ]
    accounts: dict[str, dict[str, Any]] = {}
    for key, name, domain, stage in account_specs:
        existing = store._find_account_key(ws, {"external_source_id": _ext(f"account:{key}")})
        if existing:
            accounts[key] = existing
            _count("accounts", created=False)
            continue
        row = store.create_account(
            ws,
            name,
            domain=domain,
            emails=[f"hello@{domain}"],
            phones=["+441234567890"],
            source="demo_seed",
            domain_pack="generic",
            stage=stage,
            tags=[DEMO_TAG, key],
            external_source_id=_ext(f"account:{key}"),
            actor_type="system",
            actor_id=ACTOR,
            scores={"fit": 0.72},
        )
        accounts[key] = row
        _count("accounts", created=True)
    summary["ids"]["accounts"] = {k: v["id"] for k, v in accounts.items()}

    # ── Leads (fill pipeline stages) ──────────────────────────
    lead_stages = [
        CrmStage.DISCOVERED,
        CrmStage.ENRICHED,
        CrmStage.LISTED,
        CrmStage.APPROVED,
        CrmStage.ENROLLED,
        CrmStage.CONTACTED,
        CrmStage.ENGAGED,
        CrmStage.QUALIFIED,
        CrmStage.BOOKED,
        CrmStage.CUSTOMER,
        CrmStage.PAYING,
        CrmStage.LOST,
    ]
    leads: list[dict[str, Any]] = []
    for idx, stage in enumerate(lead_stages):
        key = f"lead:{stage}"
        existing = _by_ext("crm_leads", key)
        if existing:
            leads.append(existing)
            _count("leads", created=False)
            continue
        account = accounts["harbour-homes" if idx % 2 == 0 else "northgate-prop"]
        row = store.create_lead(
            ws,
            name=f"Demo Lead {str(stage).replace('_', ' ').title()}",
            emails=[f"{str(stage).replace('_', '.')}@demo-lead.example"],
            phones=[f"+447700900{idx:02d}"],
            account_id=account["id"],
            company_name=account["name"],
            source="demo_seed",
            stage=stage,
            tags=[DEMO_TAG, "pipeline"],
            external_source_id=_ext(key),
            actor_type="system",
            actor_id=ACTOR,
            scores={"interest": round(0.4 + idx * 0.04, 2)},
        )
        leads.append(row)
        _count("leads", created=True)
    summary["ids"]["leads"] = [r["id"] for r in leads]

    # ── Contacts ──────────────────────────────────────────────
    contacts: list[dict[str, Any]] = []
    for idx, (key, account_key) in enumerate(
        (("alex-buyer", "harbour-homes"), ("sam-ops", "northgate-prop"), ("jordan-cfo", "coastal-invest"))
    ):
        existing = _by_ext("crm_contacts", f"contact:{key}")
        if existing:
            contacts.append(existing)
            _count("contacts", created=False)
            continue
        account = accounts[account_key]
        row = store.create_contact(
            ws,
            key.replace("-", " ").title(),
            emails=[f"{key}@demo-contact.example"],
            phones=[f"+447711200{idx:02d}"],
            account_id=account["id"],
            source="demo_seed",
            stage=CrmStage.ENGAGED if idx else CrmStage.CONTACTED,
            tags=[DEMO_TAG],
            external_source_id=_ext(f"contact:{key}"),
            actor_type="system",
            actor_id=ACTOR,
        )
        contacts.append(row)
        _count("contacts", created=True)
    summary["ids"]["contacts"] = [r["id"] for r in contacts]

    # ── Deals ─────────────────────────────────────────────────
    deals: list[dict[str, Any]] = []
    for key, account_key, stage, amount in (
        ("deal-harbour", "harbour-homes", CrmStage.QUALIFIED, 12000),
        ("deal-coastal", "coastal-invest", CrmStage.BOOKED, 48000),
        ("deal-paying", "paying-co", CrmStage.PAYING, 96000),
    ):
        existing = _by_ext("crm_deals", f"deal:{key}")
        if existing:
            deals.append(existing)
            _count("deals", created=False)
            continue
        account = accounts[account_key]
        row = store.create_deal(
            ws,
            f"Demo {key}",
            account_id=account["id"],
            contact_id=contacts[0]["id"] if contacts else None,
            amount=amount,
            currency="GBP",
            stage=stage,
            source="demo_seed",
            tags=[DEMO_TAG],
            external_source_id=_ext(f"deal:{key}"),
            actor_type="system",
            actor_id=ACTOR,
        )
        deals.append(row)
        _count("deals", created=True)
    summary["ids"]["deals"] = [r["id"] for r in deals]

    # ── Lists + memberships ───────────────────────────────────
    existing_lists = [row for row in store.list_lists(ws, limit=200) if row.get("name") == DEMO_LIST_NAME]
    if existing_lists:
        crm_list = existing_lists[0]
        _count("lists", created=False)
    else:
        crm_list = store.create_list(
            ws,
            DEMO_LIST_NAME,
            description="Local demo list for Soft Wall enroll practice",
            source="demo_seed",
            stage=CrmStage.LISTED,
            tags=[DEMO_TAG],
            actor_type="system",
            actor_id=ACTOR,
        )
        _count("lists", created=True)
    summary["ids"]["list_id"] = crm_list["id"]

    for lead in leads[:4]:
        before = len(store.list_memberships(ws, crm_list["id"]))
        store.add_list_member(
            ws,
            crm_list["id"],
            member_type="lead",
            member_id=lead["id"],
            stage=lead.get("stage"),
        )
        after = len(store.list_memberships(ws, crm_list["id"]))
        _count("list_memberships", created=after > before)

    # ── Activities ────────────────────────────────────────────
    for idx, lead in enumerate(leads[:5]):
        subject = f"[demo-seed] touch {idx + 1}"
        existing_acts = [
            a
            for a in store.list_activities(ws, entity_type="lead", entity_id=lead["id"], limit=50)
            if a.get("subject") == subject
        ]
        if existing_acts:
            _count("activities", created=False)
            continue
        store.create_activity(
            ws,
            entity_type="lead",
            entity_id=lead["id"],
            activity_type="note",
            subject=subject,
            body="Seeded local demo activity",
            actor_type="system",
            actor_id=ACTOR,
            metadata={"demo": True},
        )
        _count("activities", created=True)

    # ── Discovery + enrichment jobs ───────────────────────────
    demo_jobs = [
        j
        for j in store.list_discovery_jobs(ws, limit=100)
        if (j.get("params") or j.get("params_json") or {}).get("demo") is True
        or (isinstance(j.get("params_json"), dict) and j["params_json"].get("demo"))
    ]
    # params may already be parsed dict from store
    if not demo_jobs:
        for j in store.list_discovery_jobs(ws, limit=100):
            params = j.get("params") or j.get("params_json") or {}
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except json.JSONDecodeError:
                    params = {}
            if isinstance(params, dict) and params.get("demo"):
                demo_jobs.append(j)
    if demo_jobs:
        discovery_job = demo_jobs[0]
        _count("discovery_jobs", created=False)
    else:
        discovery_job = store.create_discovery_job(
            ws,
            "companies_house",
            status="completed",
            params={"query": "property Portsmouth", "demo": True},
            result_counts={"candidates": 12, "materialized": 4},
            list_id=crm_list["id"],
            actor_type="system",
            actor_id=ACTOR,
        )
        _count("discovery_jobs", created=True)
    summary["ids"]["discovery_job_id"] = discovery_job["id"]

    demo_enrich = [
        j
        for j in store.list_enrichment_jobs(ws, limit=100)
        if str(j.get("source_path") or "") == "demo-seed://sheet"
    ]
    if demo_enrich:
        _count("enrichment_jobs", created=False)
    else:
        store.create_enrichment_job(
            ws,
            status="completed",
            sheet_type="leads",
            source_path="demo-seed://sheet",
            output_path="demo-seed://sheet-out",
            proposal={"fields": {"linkedin": "https://example.com/in/demo"}, "demo": True},
            cells_filled=8,
            cells_skipped=1,
            actor_type="system",
            actor_id=ACTOR,
        )
        _count("enrichment_jobs", created=True)

    # ── Consent + suppression ─────────────────────────────────
    if contacts:
        existing_consent = [
            c
            for c in store.list_consent_records(ws, limit=100)
            if c.get("subject_id") == contacts[0]["id"] and c.get("purpose") == "marketing"
        ]
        if existing_consent:
            _count("consent_records", created=False)
        else:
            store.create_consent_record(
                ws,
                subject_type="contact",
                subject_id=contacts[0]["id"],
                channel="email",
                purpose="marketing",
                lawful_basis="consent",
                evidence="demo-seed local consent",
                actor_type="system",
                actor_id=ACTOR,
            )
            _count("consent_records", created=True)

    store.create_suppression_entry(
        ws,
        channel="email",
        address="suppressed@demo-seed.example",
        reason="demo_seed_unsubscribe",
        source="demo_seed",
        actor_type="system",
        actor_id=ACTOR,
    )
    _count("suppressions", created=True)

    # ── Source record + merge suggestion ──────────────────────
    if len(leads) >= 2:
        store.create_source_record(
            ws,
            adapter="demo_seed",
            external_id=_ext("source:lead-0"),
            snapshot={"display_name": leads[0].get("name")},
            content_hash="demo-seed-hash-0",
        )
        _count("source_records", created=True)

        existing_merges = [
            m
            for m in store.list_merge_suggestions(ws, status=None, limit=100)
            if m.get("left_id") == leads[0]["id"] and m.get("right_id") == leads[1]["id"]
        ]
        if existing_merges:
            _count("merge_suggestions", created=False)
        else:
            store.create_merge_suggestion(
                ws,
                entity_type="lead",
                left_id=leads[0]["id"],
                right_id=leads[1]["id"],
                status=MergeSuggestionStatus.PENDING,
                score=0.81,
                match_keys=["email_domain"],
                explanation="Demo seed overlap",
                field_diff={"emails": "overlap"},
                actor_type="system",
                actor_id=ACTOR,
            )
            _count("merge_suggestions", created=True)

    # ── Outbox ────────────────────────────────────────────────
    store.enqueue_outbox(
        ws,
        kind="email.send",
        idempotency_key=_ext("outbox:pending-1"),
        payload={"to": "alex@demo-lead.example", "subject": "Demo intro"},
        status=OutboxStatus.PENDING,
        entity_type="lead",
        entity_id=leads[0]["id"] if leads else None,
        correlation_id="demo-seed-corr-1",
    )
    _count("outbox", created=True)
    dead = store.enqueue_outbox(
        ws,
        kind="email.send",
        idempotency_key=_ext("outbox:dead-1"),
        payload={"to": "bounce@demo-lead.example", "subject": "Demo retry"},
        status=OutboxStatus.DEAD_LETTER,
        entity_type="lead",
        entity_id=leads[1]["id"] if len(leads) > 1 else None,
        correlation_id="demo-seed-corr-2",
    )
    store.update_outbox(ws, dead["id"], last_error="demo seeded dead letter", attempts=3)
    _count("outbox", created=True)

    # ── Contactability + sender + kill switch ─────────────────
    if leads:
        store.upsert_contactability(
            ws,
            subject_type="lead",
            subject_id=leads[0]["id"],
            channel="email",
            purpose="cold_outreach",
            decision=ContactabilityVerdict.ALLOW,
            reason="demo seed allow",
            policy_version="demo-1",
            jurisdiction="UK",
            actor_type="system",
            actor_id=ACTOR,
        )
        store.upsert_contactability(
            ws,
            subject_type="lead",
            subject_id=leads[-1]["id"],
            channel="email",
            purpose="cold_outreach",
            decision=ContactabilityVerdict.DENY,
            reason="demo seed deny",
            policy_version="demo-1",
            jurisdiction="UK",
            actor_type="system",
            actor_id=ACTOR,
        )
        _count("contactability", created=True)

    store.upsert_sender_readiness(
        ws,
        domain="demo-seed.local",
        verified=True,
        spf_ok=True,
        dkim_ok=True,
        dmarc_ok=True,
        notes="Local demo sender domain (not live mail)",
        actor_type="system",
        actor_id=ACTOR,
    )
    _count("sender_readiness", created=True)

    store.upsert_kill_switch(
        ws,
        scope="workspace",
        enabled=False,
        reason="demo seed default off",
        actor_type="system",
        actor_id=ACTOR,
    )
    _count("kill_switches", created=True)

    # ── ICP ───────────────────────────────────────────────────
    icps = icp_mod.list_icps(store, ws, name=DEMO_ICP_NAME)
    if icps:
        icp = icps[0]
        _count("icp", created=False)
    else:
        icp = icp_mod.create_icp(
            store,
            ws,
            name=DEMO_ICP_NAME,
            pack="generic",
            include_rules=[{"field": "keyword", "value": "property"}],
            exclude_rules=[{"field": "keyword", "value": "student"}],
            keywords=["investor", "landlord"],
            geography=["UK", "Portsmouth"],
            notes="Local demo ICP",
            actor_type="system",
            actor_id=ACTOR,
        )
        _count("icp", created=True)
    summary["ids"]["icp_id"] = icp["id"]
    if activate_icp and not icp.get("active"):
        activated = icp_mod.activate_icp(
            store,
            ws,
            icp["id"],
            actor_id=ACTOR,
            force=True,
        )
        summary["icp_activation"] = {
            "ok": activated.get("ok"),
            "blocked": activated.get("blocked"),
        }

    # ── Experiment ────────────────────────────────────────────
    try:
        create_experiment(
            store,
            ws,
            name="Demo Subject Line A/B",
            variants=[
                {"id": "a", "name": "Control", "subject": "Quick intro"},
                {"id": "b", "name": "Variant", "subject": "Worth 10 minutes?"},
            ],
            traffic_split={"a": 0.5, "b": 0.5},
            min_sample=10,
            actor_id=ACTOR,
        )
        _count("experiments", created=True)
    except Exception as exc:
        # Re-run may hit unique name; treat as reused.
        summary["experiments_note"] = str(exc)[:200]
        _count("experiments", created=False)

    # ── SLA assignment ────────────────────────────────────────
    if leads:
        try:
            assign_owner(
                store,
                ws,
                entity_type="lead",
                entity_id=leads[0]["id"],
                owner_user_id="demo-owner",
                mode="manual",
                sla_hours=24,
                actor_id=ACTOR,
                force=True,
            )
            _count("sla_assignments", created=True)
        except Exception as exc:
            summary["sla_error"] = str(exc)[:200]

    summary["ok"] = True
    summary["hint"] = (
        "Refresh /crm and /crm/pipeline. Sender domain demo-seed.local clears the "
        "empty-domain deliverability gate for local demos only."
    )
    return summary


def _parse_jsonish(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _has_demo_tag(row: dict[str, Any]) -> bool:
    tags = _parse_jsonish(row.get("tags") or row.get("tags_json") or [])
    if isinstance(tags, list):
        return DEMO_TAG in {str(t) for t in tags}
    return False


def _is_demo_ext(row: dict[str, Any]) -> bool:
    ext = str(row.get("external_source_id") or "")
    return ext.startswith(DEMO_SOURCE_PREFIX)


def _demo_params(row: dict[str, Any]) -> bool:
    params = _parse_jsonish(row.get("params") or row.get("params_json") or {})
    return isinstance(params, dict) and bool(params.get("demo"))


def demo_seed_status(workspace_id: str = "default") -> dict[str, Any]:
    """Count demo-seed rows visible in CRM lists (read-only)."""
    from keprix.crm import icp as icp_mod
    from keprix.crm.experiments import list_experiments
    from keprix.crm.nice_schema import ensure_nice_schema
    from keprix.crm.store import get_crm_store

    store = get_crm_store()
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)

    accounts = [r for r in store.list_accounts(ws, limit=500) if _is_demo_ext(r) or _has_demo_tag(r)]
    leads = [r for r in store.list_leads(ws, limit=500) if _is_demo_ext(r) or _has_demo_tag(r)]
    contacts = [r for r in store.list_contacts(ws, limit=500) if _is_demo_ext(r) or _has_demo_tag(r)]
    deals = [r for r in store.list_deals(ws, limit=500) if _is_demo_ext(r) or _has_demo_tag(r)]
    lists = [
        r
        for r in store.list_lists(ws, limit=200)
        if r.get("name") == DEMO_LIST_NAME or _has_demo_tag(r) or str(r.get("source") or "") == "demo_seed"
    ]
    enrichment = [
        j for j in store.list_enrichment_jobs(ws, limit=200) if str(j.get("source_path") or "") == "demo-seed://sheet"
    ]
    discovery = [j for j in store.list_discovery_jobs(ws, limit=200) if _demo_params(j)]
    suppressions = [
        s
        for s in store.list_suppressions(ws, limit=200)
        if str(s.get("address") or "") == "suppressed@demo-seed.example"
        or str(s.get("source") or "") == "demo_seed"
    ]
    readiness = [r for r in store.list_sender_readiness(ws, limit=50) if r.get("domain") == "demo-seed.local"]
    icps = icp_mod.list_icps(store, ws, name=DEMO_ICP_NAME)
    experiments = [e for e in list_experiments(store, ws) if e.get("name") == "Demo Subject Line A/B"]
    outbox = [
        o
        for o in store.list_outbox(ws, limit=200)
        if str(o.get("idempotency_key") or "").startswith(DEMO_SOURCE_PREFIX)
        or str(o.get("correlation_id") or "").startswith("demo-seed-")
    ]

    counts = {
        "accounts": len(accounts),
        "leads": len(leads),
        "contacts": len(contacts),
        "deals": len(deals),
        "lists": len(lists),
        "enrichment_jobs": len(enrichment),
        "discovery_jobs": len(discovery),
        "suppressions": len(suppressions),
        "sender_readiness": len(readiness),
        "icp": len(icps),
        "experiments": len(experiments),
        "outbox": len(outbox),
    }
    present = any(v > 0 for v in counts.values())
    return {
        "ok": True,
        "workspace_id": ws,
        "present": present,
        "counts": counts,
        "hint": (
            "Remove via Soft Wall on /crm/settings (Demo data), or "
            "POST /api/crm/demo-seed/purge."
            if present
            else "No demo-seed CRM rows found."
        ),
    }


def purge_crm_demo(workspace_id: str = "default") -> dict[str, Any]:
    """Soft-delete (or hard-delete) only rows marked as local demo-seed."""
    from keprix.crm import icp as icp_mod
    from keprix.crm.experiments import list_experiments
    from keprix.crm.nice_schema import ensure_nice_schema
    from keprix.crm.store import get_crm_store

    store = get_crm_store()
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    removed: dict[str, int] = {}

    def _bump(key: str) -> None:
        removed[key] = int(removed.get(key, 0)) + 1

    # Collect core party ids first
    accounts = [r for r in store.list_accounts(ws, limit=500) if _is_demo_ext(r) or _has_demo_tag(r)]
    leads = [r for r in store.list_leads(ws, limit=500) if _is_demo_ext(r) or _has_demo_tag(r)]
    contacts = [r for r in store.list_contacts(ws, limit=500) if _is_demo_ext(r) or _has_demo_tag(r)]
    deals = [r for r in store.list_deals(ws, limit=500) if _is_demo_ext(r) or _has_demo_tag(r)]
    lists = [
        r
        for r in store.list_lists(ws, limit=200)
        if r.get("name") == DEMO_LIST_NAME or _has_demo_tag(r) or str(r.get("source") or "") == "demo_seed"
    ]
    lead_ids = {str(r["id"]) for r in leads}

    for lst in lists:
        for mem in store.list_memberships(ws, lst["id"]):
            store._soft_delete("crm_list_memberships", ws, mem["id"])
            _bump("list_memberships")

    for lead in leads:
        for act in store.list_activities(ws, entity_type="lead", entity_id=lead["id"], limit=100):
            subject = str(act.get("subject") or "")
            meta = _parse_jsonish(act.get("metadata") or act.get("metadata_json") or {})
            if subject.startswith("[demo-seed]") or (isinstance(meta, dict) and meta.get("demo")):
                store._soft_delete("crm_activities", ws, act["id"])
                _bump("activities")

    for contact in contacts:
        for c in store.list_consent_records(ws, limit=200):
            if c.get("subject_id") == contact["id"] and "demo-seed" in str(c.get("evidence") or ""):
                store._soft_delete("crm_consent_records", ws, c["id"])
                _bump("consent_records")

    for row in store.list_merge_suggestions(ws, status=None, limit=200):
        if row.get("left_id") in lead_ids or row.get("right_id") in lead_ids:
            store._soft_delete("crm_merge_suggestions", ws, row["id"])
            _bump("merge_suggestions")

    for row in store.list_outbox(ws, limit=500):
        key = str(row.get("idempotency_key") or "")
        corr = str(row.get("correlation_id") or "")
        if key.startswith(DEMO_SOURCE_PREFIX) or corr.startswith("demo-seed-"):
            store._conn.execute("DELETE FROM crm_outbox WHERE id = ? AND workspace_id = ?", (row["id"], ws))
            store._conn.commit()
            _bump("outbox")

    # Contactability tied to demo leads
    contactability = store._fetchall(
        "SELECT * FROM crm_contactability_decisions WHERE workspace_id = ? AND deleted_at IS NULL",
        (ws,),
    )
    for row in contactability:
        if str(row.get("subject_id") or "") in lead_ids or "demo seed" in str(row.get("reason") or "").lower():
            store._soft_delete("crm_contactability_decisions", ws, row["id"])
            _bump("contactability")

    for row in store.list_enrichment_jobs(ws, limit=200):
        if str(row.get("source_path") or "") == "demo-seed://sheet":
            store._soft_delete("crm_enrichment_jobs", ws, row["id"])
            _bump("enrichment_jobs")

    for row in store.list_discovery_jobs(ws, limit=200):
        if _demo_params(row):
            store._soft_delete("crm_discovery_jobs", ws, row["id"])
            _bump("discovery_jobs")

    sources = store._fetchall(
        "SELECT * FROM crm_source_records WHERE workspace_id = ? AND adapter = ?",
        (ws, "demo_seed"),
    )
    for row in sources:
        store._conn.execute("DELETE FROM crm_source_records WHERE id = ? AND workspace_id = ?", (row["id"], ws))
        store._conn.commit()
        _bump("source_records")

    for row in store.list_suppressions(ws, limit=200):
        if (
            str(row.get("address") or "") == "suppressed@demo-seed.example"
            or str(row.get("source") or "") == "demo_seed"
        ):
            store.delete_suppression_entry(ws, row["id"])
            _bump("suppressions")

    for row in deals:
        store.delete_deal(ws, row["id"])
        _bump("deals")
    for row in contacts:
        store.delete_contact(ws, row["id"])
        _bump("contacts")
    for row in leads:
        store.delete_lead(ws, row["id"])
        _bump("leads")
    for row in lists:
        store.delete_list(ws, row["id"])
        _bump("lists")
    for row in accounts:
        store.delete_account(ws, row["id"])
        _bump("accounts")

    for row in store.list_sender_readiness(ws, limit=50):
        if row.get("domain") == "demo-seed.local":
            store._soft_delete("crm_sender_readiness", ws, row["id"])
            _bump("sender_readiness")

    for icp in icp_mod.list_icps(store, ws, name=DEMO_ICP_NAME):
        with store._lock:
            store._conn.execute(
                "UPDATE crm_icp_definitions SET active = 0, updated_at = datetime('now') "
                "WHERE workspace_id = ? AND id = ?",
                (ws, icp["id"]),
            )
            store._conn.execute(
                "DELETE FROM crm_icp_definitions WHERE workspace_id = ? AND id = ?",
                (ws, icp["id"]),
            )
            store._conn.commit()
        _bump("icp")

    for exp in list_experiments(store, ws):
        if exp.get("name") != "Demo Subject Line A/B":
            continue
        with store._lock:
            store._conn.execute(
                "DELETE FROM crm_experiment_assignments WHERE workspace_id = ? AND experiment_id = ?",
                (ws, exp["id"]),
            )
            store._conn.execute(
                "DELETE FROM crm_experiments WHERE workspace_id = ? AND id = ?",
                (ws, exp["id"]),
            )
            store._conn.commit()
        _bump("experiments")

    # Drop leftover demo idempotency keys
    with store._lock:
        store._conn.execute(
            "DELETE FROM crm_idempotency WHERE workspace_id = ? AND idempotency_key LIKE ?",
            (ws, f"{DEMO_SOURCE_PREFIX}%"),
        )
        store._conn.commit()

    status = demo_seed_status(ws)
    return {
        "ok": True,
        "workspace_id": ws,
        "removed": removed,
        "remaining": status.get("counts"),
        "present": status.get("present"),
        "hint": "Demo data removed. Refresh /crm and /crm/pipeline.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed or purge local CRM demo data (never live).")
    parser.add_argument("--workspace", default="default")
    parser.add_argument("--no-activate-icp", action="store_true")
    parser.add_argument("--purge", action="store_true", help="Remove demo-seed rows instead of seeding")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.purge:
            result = purge_crm_demo(args.workspace)
        else:
            result = seed_crm_demo(
                args.workspace,
                activate_icp=not args.no_activate_icp,
            )
    except DemoSeedForbidden as exc:
        print(f"FORBIDDEN: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    elif args.purge:
        print(f"Purged workspace={result['workspace_id']}")
        print(f"removed={result.get('removed')}")
        print(result.get("hint"))
    else:
        print(f"Seeded workspace={result['workspace_id']}")
        print(f"created={result.get('created')}")
        print(f"reused={result.get('reused')}")
        print(result.get("hint"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
