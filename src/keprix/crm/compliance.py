"""Consent, suppression, and PECR/GDPR policy helpers (prompt 448)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

POLICY_VERSION = "uk-crm-defaults-2026.1"

# Documented UK defaults (not legal advice).
UK_DEFAULT_POLICY: dict[str, Any] = {
    "jurisdiction": "UK",
    "policy_version": POLICY_VERSION,
    "cold_email": {
        "allowed_bases": ["legitimate_interest", "soft_opt_in", "consent", "contract"],
        "require_basis_record": True,
        "suppression_always_wins": True,
        "discovery_is_not_consent": True,
    },
    "prohibited": {
        "special_category_inference": True,
        "minors": True,
        "vulnerable_person_targeting": True,
        "discriminatory_filters": True,
        "health_care_recipient_lead_gen": True,
    },
    "note": "Workspace defaults for UK outreach. Not legal advice. Operators must confirm lawful basis.",
}

LAWFUL_BASES = frozenset(
    {"legitimate_interest", "soft_opt_in", "contract", "consent"}
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_compliance_columns(store: Any) -> None:
    """Additive columns: permanent suppression flag."""
    cols = {r[1] for r in store._conn.execute("PRAGMA table_info(crm_suppression_entries)").fetchall()}
    alters = []
    if "permanent" not in cols:
        alters.append("ALTER TABLE crm_suppression_entries ADD COLUMN permanent INTEGER NOT NULL DEFAULT 0")
    # Policy decision records table
    store._conn.execute(
        """
        CREATE TABLE IF NOT EXISTS crm_policy_decisions (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            subject_type TEXT,
            subject_id TEXT,
            purpose TEXT,
            channel TEXT,
            jurisdiction TEXT,
            policy_version TEXT,
            decision TEXT NOT NULL,
            evidence TEXT,
            explanation TEXT,
            expires_at TEXT,
            actor_type TEXT,
            actor_id TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    if alters:
        with store._lock:
            for stmt in alters:
                store._conn.execute(stmt)
            store._conn.commit()


def get_workspace_policy(store: Any, workspace_id: str) -> dict[str, Any]:
    """Return UK defaults merged with optional workspace override in kill-switch style settings."""
    policy = dict(UK_DEFAULT_POLICY)
    try:
        # Reuse sender readiness / settings blob if present via kill switch scope=policy
        rows = store.list_kill_switches(workspace_id)
        for row in rows:
            if str(row.get("scope")) == "compliance_policy" and row.get("reason"):
                try:
                    override = json.loads(str(row["reason"]))
                    if isinstance(override, dict):
                        policy.update(override)
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    return policy


def evaluate_send_policy(
    store: Any,
    workspace_id: str,
    *,
    subject_type: str,
    subject_id: str,
    channel: str,
    address: str,
    purpose: str = "cold_outreach",
    actor_type: str | None = None,
    actor_id: str | None = None,
) -> dict[str, Any]:
    """Suppression wins; discovery is not consent; record decision."""
    ensure_compliance_columns(store)
    policy = get_workspace_policy(store, workspace_id)
    addr = str(address or "").strip().lower()

    if addr and store.is_suppressed(workspace_id, channel=channel, address=addr):
        decision = {
            "decision": "deny",
            "reason": "suppression_wins",
            "policy_version": policy["policy_version"],
            "jurisdiction": policy["jurisdiction"],
            "purpose": purpose,
            "channel": channel,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "explanation": "SuppressionEntry blocks send regardless of consent or discovery.",
            "evidence": f"suppressed:{channel}:{addr}",
            "expires_at": None,
        }
        _record_decision(store, workspace_id, decision, actor_type=actor_type, actor_id=actor_id)
        return decision

    # Contactability deny
    for d in store.list_contactability(workspace_id):
        if (
            str(d.get("subject_id")) == subject_id
            and str(d.get("decision")) == "deny"
            and str(d.get("channel") or channel) in {channel, "any", "*"}
        ):
            decision = {
                "decision": "deny",
                "reason": "contactability_deny",
                "policy_version": policy["policy_version"],
                "jurisdiction": policy["jurisdiction"],
                "purpose": purpose,
                "channel": channel,
                "subject_type": subject_type,
                "subject_id": subject_id,
                "explanation": str(d.get("reason") or "Contactability deny"),
                "evidence": d.get("id"),
                "expires_at": None,
            }
            _record_decision(store, workspace_id, decision, actor_type=actor_type, actor_id=actor_id)
            return decision

    consents = [
        c
        for c in store.list_consent_records(workspace_id)
        if str(c.get("subject_id")) == subject_id
        and str(c.get("channel") or channel) in {channel, "any", "*"}
        and not c.get("withdrawn_at")
    ]
    basis = None
    evidence = None
    for c in consents:
        b = str(c.get("lawful_basis") or "")
        if b in LAWFUL_BASES:
            basis = b
            evidence = c.get("id")
            break

    if purpose == "cold_outreach" and policy.get("cold_email", {}).get("require_basis_record") and not basis:
        # Soft allow for Soft Wall review: needs_review rather than hard deny when LI assessment pending
        decision = {
            "decision": "needs_review",
            "reason": "missing_lawful_basis_record",
            "policy_version": policy["policy_version"],
            "jurisdiction": policy["jurisdiction"],
            "purpose": purpose,
            "channel": channel,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "explanation": "Discovery is not consent. Record a lawful basis before cold send, or Soft Wall review.",
            "evidence": None,
            "expires_at": None,
            "discovery_is_not_consent": True,
        }
        _record_decision(store, workspace_id, decision, actor_type=actor_type, actor_id=actor_id)
        return decision

    decision = {
        "decision": "allow",
        "reason": basis or "policy_allow",
        "policy_version": policy["policy_version"],
        "jurisdiction": policy["jurisdiction"],
        "purpose": purpose,
        "channel": channel,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "explanation": f"Allowed under {basis or 'workspace policy'}",
        "evidence": evidence,
        "expires_at": None,
        "discovery_is_not_consent": True,
    }
    _record_decision(store, workspace_id, decision, actor_type=actor_type, actor_id=actor_id)
    return decision


def _record_decision(
    store: Any,
    workspace_id: str,
    decision: dict[str, Any],
    *,
    actor_type: str | None = None,
    actor_id: str | None = None,
) -> None:
    import uuid

    try:
        with store._lock:
            store._conn.execute(
                """
                INSERT INTO crm_policy_decisions (
                    id, workspace_id, subject_type, subject_id, purpose, channel,
                    jurisdiction, policy_version, decision, evidence, explanation,
                    expires_at, actor_type, actor_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    workspace_id,
                    decision.get("subject_type"),
                    decision.get("subject_id"),
                    decision.get("purpose"),
                    decision.get("channel"),
                    decision.get("jurisdiction"),
                    decision.get("policy_version"),
                    decision.get("decision"),
                    str(decision.get("evidence") or ""),
                    decision.get("explanation"),
                    decision.get("expires_at"),
                    actor_type,
                    actor_id,
                    _utcnow(),
                ),
            )
            store._conn.commit()
    except Exception:
        pass


def check_prohibited_targeting(params: dict[str, Any] | None) -> dict[str, Any]:
    """Refuse special-category / minors / health recipient targeting."""
    blob = json.dumps(params or {}, default=str).lower()
    hits = []
    needles = {
        "special_category_inference": ("ethnicity", "religion", "sexual orientation", "political opinion"),
        "minors": ("under 16", "under16", "child lead", "school pupil", "minor "),
        "vulnerable_person_targeting": ("vulnerable adult", "safeguarding target"),
        "health_care_recipient_lead_gen": ("patient list", "care recipient", "nhs patient", "diagnosis lead"),
        "discriminatory_filters": ("no immigrants", "whites only", "exclude disability"),
    }
    for code, words in needles.items():
        if any(w in blob for w in words):
            hits.append(code)
    if hits:
        return {"allowed": False, "reasons": hits, "message": "Prohibited targeting filter refused"}
    return {"allowed": True, "reasons": []}


def create_consent(
    store: Any,
    workspace_id: str,
    *,
    subject_type: str,
    subject_id: str,
    channel: str,
    lawful_basis: str,
    purpose: str = "outreach",
    evidence: str | None = None,
    source: str | None = None,
    actor_type: str | None = None,
    actor_id: str | None = None,
) -> dict[str, Any]:
    if lawful_basis not in LAWFUL_BASES:
        raise ValueError(f"invalid lawful_basis; expected one of {sorted(LAWFUL_BASES)}")
    row = store.create_consent_record(
        workspace_id,
        subject_type=subject_type,
        subject_id=subject_id,
        channel=channel,
        purpose=purpose,
        jurisdiction="UK",
        lawful_basis=lawful_basis,
        evidence=evidence or source,
        assessment_version=POLICY_VERSION,
        obtained_at=_utcnow(),
        actor_type=actor_type,
        actor_id=actor_id,
    )
    try:
        store.create_activity(
            workspace_id,
            entity_type=subject_type,
            entity_id=subject_id,
            activity_type="consent_change",
            channel=channel,
            subject=f"Consent recorded: {lawful_basis}",
            body=evidence or source or "",
            actor_type=actor_type,
            actor_id=actor_id,
        )
    except Exception:
        pass
    return row


def suppress_address(
    store: Any,
    workspace_id: str,
    *,
    address: str,
    channel: str = "email",
    reason: str = "unsubscribe",
    source: str = "engagement",
    permanent: bool = False,
    subject_type: str | None = None,
    subject_id: str | None = None,
    actor_type: str | None = None,
    actor_id: str | None = None,
) -> dict[str, Any]:
    ensure_compliance_columns(store)
    row = store.create_suppression_entry(
        workspace_id,
        address=address,
        channel=channel,
        reason=reason,
        source=source,
        subject_type=subject_type,
        subject_id=subject_id,
        actor_type=actor_type,
        actor_id=actor_id,
    )
    if permanent and row:
        try:
            with store._lock:
                store._conn.execute(
                    "UPDATE crm_suppression_entries SET permanent = 1 WHERE id = ? AND workspace_id = ?",
                    (row["id"], workspace_id),
                )
                store._conn.commit()
            row = store._get("crm_suppression_entries", workspace_id, row["id"]) or row
        except Exception:
            pass
    if subject_type and subject_id:
        try:
            from keprix.crm.stages import apply_stage
            from keprix.crm.models import CrmStage

            apply_stage(
                store,
                workspace_id,
                entity_type=subject_type,
                entity_id=subject_id,
                to_stage=CrmStage.SUPPRESSED if reason != "bounce" else CrmStage.BOUNCED,
                force=True,
                actor_type=actor_type,
                actor_id=actor_id,
                reason=reason,
            )
        except Exception:
            pass
    return row


def subject_access_export(store: Any, workspace_id: str, *, subject_type: str, subject_id: str) -> dict[str, Any]:
    """DSAR-style export for a CRM person (Soft Wall gated at route)."""
    getters = {
        "lead": store.get_lead,
        "contact": store.get_contact,
        "account": store.get_account,
    }
    get_fn = getters.get(subject_type)
    entity = get_fn(workspace_id, subject_id) if get_fn else None
    activities = store.list_activities(workspace_id, entity_type=subject_type, entity_id=subject_id)
    consents = [
        c
        for c in store.list_consent_records(workspace_id)
        if str(c.get("subject_id")) == subject_id
    ]
    suppressions = [
        s
        for s in store.list_suppressions(workspace_id)
        if str(s.get("subject_id") or "") == subject_id
    ]
    return {
        "workspace_id": workspace_id,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "exported_at": _utcnow(),
        "entity": entity,
        "activities": activities,
        "consents": consents,
        "suppressions": suppressions,
        "runbook": "docs/features/crm-compliance.md#subject-access-export",
    }


def erasure_plan(store: Any, workspace_id: str, *, subject_type: str, subject_id: str) -> dict[str, Any]:
    """Plan erasure while retaining minimal permanent suppression."""
    export = subject_access_export(store, workspace_id, subject_type=subject_type, subject_id=subject_id)
    emails = []
    entity = export.get("entity") or {}
    for item in entity.get("emails") or []:
        if isinstance(item, dict) and item.get("address"):
            emails.append(str(item["address"]).lower())
    return {
        "action": "erasure",
        "soft_delete_entity": True,
        "retain_permanent_suppressions": emails,
        "audit": True,
        "preview": export,
        "note": "Permanent SuppressionEntry rows retained for do-not-contact. Soft Wall required to execute.",
    }
