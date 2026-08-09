"""Soft Wall gates for Document Vault high-impact actions (Prompt 650)."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from keprix.crm.soft_wall import create_crm_approval, gate_or_approve, resolve_crm_approval

# Rule of Two: these always require Soft Wall approval.
DOCUMENT_VAULT_GATES = frozenset(
    {
        "document_vault.permanent_delete",
        "document_vault.external_share",
        "document_vault.permission_change",
        "document_vault.bulk_destructive",
        "document_vault.conflict_overwrite",
        "document_vault.classified_export",
    }
)


def soft_wall_enabled() -> bool:
    raw = os.environ.get("KEPRIX_DOCUMENT_VAULT_SOFT_WALL", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def payload_digest(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def gate_vault_action(
    workspace_id: str,
    *,
    kind: str,
    subject: str,
    payload: dict[str, Any],
    object_id: str | None = None,
    actor_id: str | None = None,
    approval_id: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Return Soft Wall gate result. High-impact kinds always require approval."""
    if kind not in DOCUMENT_VAULT_GATES:
        return {"allowed": True, "blocked": False}
    if not soft_wall_enabled() and not force:
        # Soft Wall flag off still keeps permanent delete / classified export gated.
        if kind not in {
            "document_vault.permanent_delete",
            "document_vault.classified_export",
            "document_vault.conflict_overwrite",
        }:
            return {"allowed": True, "blocked": False}

    stamped = dict(payload)
    stamped["digest"] = payload_digest(payload)
    stamped["gate"] = kind
    return gate_or_approve(
        workspace_id,
        kind=kind,
        subject=subject,
        payload=stamped,
        object_type="document_vault_item",
        object_id=object_id,
        actor_id=actor_id,
        approval_id=approval_id,
        always_require=True,
        force=False,
    )


def create_vault_approval(
    workspace_id: str,
    *,
    kind: str,
    subject: str,
    payload: dict[str, Any],
    object_id: str | None = None,
    actor_id: str | None = None,
) -> dict[str, Any]:
    stamped = dict(payload)
    stamped["digest"] = payload_digest(payload)
    approval = create_crm_approval(
        workspace_id,
        kind=kind,
        subject=subject,
        payload=stamped,
        object_type="document_vault_item",
        object_id=object_id,
        actor_id=actor_id,
        recipient=f"document_vault:{kind}",
    )
    if isinstance(approval, dict):
        approval["deep_link"] = f"/documents?approval={approval.get('id')}"
    return approval


def resolve_vault_approval(workspace_id: str, approval_id: str, *, status: str) -> dict[str, Any] | None:
    return resolve_crm_approval(workspace_id, approval_id, status=status)


def redact_audit_payload(payload: dict[str, Any]) -> dict[str, Any]:
    banned = {
        "access_token",
        "refresh_token",
        "content",
        "bytes",
        "file_bytes",
        "Authorization",
        "grant_ciphertext",
    }
    out: dict[str, Any] = {}
    for key, value in payload.items():
        if key in banned:
            out[key] = "[redacted]"
        elif isinstance(value, dict):
            out[key] = redact_audit_payload(value)
        elif isinstance(value, str) and len(value) > 500:
            out[key] = value[:200] + "...[truncated]"
        else:
            out[key] = value
    return out


__all__ = [
    "DOCUMENT_VAULT_GATES",
    "create_vault_approval",
    "gate_vault_action",
    "payload_digest",
    "redact_audit_payload",
    "resolve_vault_approval",
    "soft_wall_enabled",
]
