"""Clinical event taxonomy, signing, and dispatch."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from keprix.governance.audit_store import get_audit_event_store
from keprix.governance.event_reporter import queue_audit_event
from keprix.governance.store import get_governance_store
from keprix.security.audit import audit_log

AUDIT_EVENT_TYPES: dict[str, str] = {
    "hazard_log_created": "A new hazard log entry was created",
    "hazard_log_updated": "A hazard log entry was updated",
    "hazard_log_closed": "A hazard log entry was closed/resolved",
    "hazard_log_exported": "A hazard log was exported to PDF",
    "cso_review_assigned": "A clinical safety officer was assigned to review a hazard log",
    "cso_review_reminder_sent": "A reminder was sent to a CSO for a pending review",
    "cso_review_approved": "A CSO approved a hazard log",
    "cso_review_rejected": "A CSO rejected a hazard log",
    "cso_review_change_requested": "A CSO requested changes to a hazard log",
    "cso_review_expired": "A CSO review request expired without a decision",
    "compliance_scan_started": "A compliance scan was triggered",
    "compliance_scan_complete": "A compliance scan completed",
    "compliance_scan_failed": "A compliance scan failed or errored",
    "compliance_finding_raised": "A compliance issue or finding was identified",
    "compliance_finding_resolved": "A compliance finding was marked resolved",
    "evidence_pack_generated": "An evidence pack was assembled and stored",
    "evidence_pack_exported": "An evidence pack was downloaded or sent to governance provider",
    "gdpr_dsar_requested": "A data subject access request was triggered",
    "gdpr_dsar_complete": "A DSAR export was completed",
    "gdpr_erasure_complete": "A right-to-erasure request was completed",
    "gdpr_consent_withdrawn": "Consent was withdrawn for a processing purpose",
    "gdpr_retention_run": "Automated retention enforcement ran",
    "legal_acceptance_recorded": "A user accepted the current legal policies",
    "legal_policy_published": "A new legal policy version was published",
    "pack_gate_approved": "A pack version was approved for activation",
    "pack_gate_rejected": "A pack version sign-off was rejected",
}


class AuditEvent(BaseModel):
    event_id: str
    event_type: str
    workspace_id: str
    instance_id: str
    timestamp: str
    actor_type: str
    actor_id: str | None = None
    subject_type: str | None = None
    subject_id: str | None = None
    summary: str
    detail: dict[str, Any] | None = None
    severity: str = "info"
    domain_pack: str | None = None
    signature: str = ""


def get_audit_hmac_secret() -> str:
    return os.environ.get("KEPRIX_AUDIT_EVENT_HMAC_SECRET", "keprix-dev-clinical-hmac-secret")


def canonical_event_payload(event: dict[str, Any]) -> bytes:
    payload = {key: event[key] for key in sorted(event.keys()) if key != "signature"}
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def sign_event(event: dict[str, Any], *, secret: str | None = None) -> str:
    key = (secret or get_audit_hmac_secret()).encode("utf-8")
    return hmac.new(key, canonical_event_payload(event), hashlib.sha256).hexdigest()


def verify_event_signature(event: dict[str, Any], *, secret: str | None = None) -> bool:
    provided = str(event.get("signature") or "")
    if not provided:
        return False
    expected = sign_event(event, secret=secret)
    return hmac.compare_digest(expected, provided)


async def _resolve_instance_id() -> str:
    cfg = await get_governance_store().get_config()
    return str(cfg.get("instance_id") or "local-instance")


async def emit_audit_event(
    event_type: str,
    *,
    workspace_id: str,
    actor_type: str,
    summary: str,
    actor_id: str | None = None,
    subject_type: str | None = None,
    subject_id: str | None = None,
    detail: dict[str, Any] | None = None,
    severity: str = "info",
    domain_pack: str | None = None,
) -> str:
    if event_type not in AUDIT_EVENT_TYPES:
        raise ValueError(f"Invalid clinical event_type: {event_type}")

    event_id = str(uuid.uuid4())
    event = AuditEvent(
        event_id=event_id,
        event_type=event_type,
        workspace_id=workspace_id,
        instance_id=await _resolve_instance_id(),
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        actor_type=actor_type,
        actor_id=actor_id,
        subject_type=subject_type,
        subject_id=subject_id,
        summary=summary,
        detail=detail or {},
        severity=severity,
        domain_pack=domain_pack,
        signature="",
    )
    payload = event.model_dump()
    payload["signature"] = sign_event(payload)
    get_audit_event_store().append(workspace_id, payload)

    await audit_log(
        event_type,
        user_id=actor_id,
        event_data={
            "audit_event_id": event_id,
            "workspace_id": workspace_id,
            "summary": summary,
            "severity": severity,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "detail": detail or {},
        },
    )
    await queue_audit_event(event_type, payload)
    return event_id
