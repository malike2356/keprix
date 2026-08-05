"""Guard remote clients: pending approval before sensitive API access."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, Request, status

from keprix.security.client_approval.fingerprint import (
    build_client_fingerprint,
    client_approval_enabled,
)
from keprix.security.client_approval.store import get_client_approval_store

logger = logging.getLogger(__name__)


def _client_ip(request: Request) -> str | None:
    from keprix.security.client_ip import client_ip

    value = client_ip(request, default="")
    return value or None


def _scope_list(scopes: dict[str, Any] | None) -> list[str]:
    if not scopes:
        return []
    return sorted(str(k) for k, v in scopes.items() if v)


async def enforce_client_approval(
    request: Request,
    *,
    token_id: str,
    workspace_id: str | None = None,
    scopes: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Return approval context when allowed; raise 403 when pending/denied/revoked/expired.

    Returns None when approval gating is disabled.
    """
    if not client_approval_enabled():
        return None
    if token_id in {"env-token", "admin"}:
        return {"bypassed": True, "reason": "operator_token"}

    headers = {k: v for k, v in request.headers.items()}
    fp = build_client_fingerprint(
        user_agent=request.headers.get("user-agent"),
        ip=_client_ip(request),
        headers=headers,
        token_id=token_id,
    )
    store = get_client_approval_store()
    record = store.upsert_seen(
        fp,
        token_id=token_id,
        workspace_id=workspace_id,
        requested_scopes=_scope_list(scopes),
    )

    if record.status == "approved" and record.is_active():
        return {"approval": record.to_dict(), "fingerprint": fp.to_dict()}

    # Auto-mark expired
    if record.status == "approved" and not record.is_active():
        store.decide(fp.fingerprint, token_id, status="revoked", note="expired")
        record = store.get(fp.fingerprint, token_id) or record

    code = "client_pending_approval"
    message = "This remote client is pending owner approval."
    if record.status == "denied":
        code = "client_denied"
        message = "This remote client was denied by the owner."
    elif record.status == "revoked":
        code = "client_revoked"
        message = "This remote client approval was revoked."
    elif record.status == "expired":
        code = "client_expired"
        message = "This remote client approval expired. Request access again."

    try:
        from keprix.security.audit import audit_log

        await audit_log(
            "client_approval_blocked",
            event_data={
                "token_id": token_id,
                "fingerprint": fp.fingerprint,
                "status": record.status,
                "client_kind": fp.client_kind,
                "agent_label": fp.agent_label,
                "user_agent_summary": fp.user_agent_summary,
                "ip_hash": fp.ip_hash,
                "workspace_id": workspace_id,
            },
            severity="warning",
        )
    except Exception:
        logger.debug("client approval audit failed", exc_info=True)

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": message,
            "code": code,
            "fingerprint": fp.fingerprint,
            "client_kind": fp.client_kind,
            "agent_label": fp.agent_label,
            "user_agent_summary": fp.user_agent_summary,
            "status": record.status,
            "last_seen_at": record.last_seen_at,
            "requested_scopes": record.requested_scopes,
            "guidance": {
                "what_happened": "First-seen or unapproved remote client.",
                "what_to_do": "Approve or deny this client in Developer > Client approvals.",
                "retry_after": 300,
            },
        },
    )
