"""Channel export delivery: attach in-channel or short-lived authenticated URL."""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from keprix.document_vault.agent_context import VaultAgentContext
from keprix.document_vault.channel.contract import channel_max_attach_bytes
from keprix.document_vault.models import VaultError
from keprix.document_vault.service import DocumentVaultService, get_document_vault_service
from keprix.document_vault.soft_wall import gate_vault_action
from keprix.document_vault.store import DocumentVaultStore, get_document_vault_store

_CLASSIFIED = frozenset({"secret", "restricted", "confidential"})


def plan_export_delivery(
    ctx: VaultAgentContext,
    item_id: str,
    *,
    fmt: str = "markdown",
    approval_id: str | None = None,
    store: DocumentVaultStore | None = None,
    service: DocumentVaultService | None = None,
    public_base_url: str | None = None,
) -> dict[str, Any]:
    """Return attach payload or short-lived download URL within channel limits."""
    st = store or get_document_vault_store()
    svc = service or get_document_vault_service()
    item = st.get_item(ctx.workspace_id, item_id, include_trashed=False)
    if not item:
        raise VaultError("not_found", "item not found")

    classification = str(item.get("classification") or "internal").lower()
    if classification in _CLASSIFIED:
        gate = gate_vault_action(
            ctx.workspace_id,
            kind="document_vault.classified_export",
            subject=f"Channel export classified item {item_id}",
            payload={"item_id": item_id, "format": fmt, "channel": ctx.channel},
            object_id=item_id,
            actor_id=ctx.actor_id,
            approval_id=approval_id,
        )
        if gate.get("blocked"):
            return {
                "ok": False,
                "blocked": True,
                "error_code": gate.get("error_code") or "soft_wall_required",
                "approval": gate.get("approval"),
            }

    exported = svc.export_item(ctx.workspace_id, item_id, target_format=fmt, actor_id=ctx.actor_id)
    export = exported.get("export") or {}
    data = export.get("data") or b""
    if isinstance(data, str):
        raw = data.encode("utf-8")
    else:
        raw = bytes(data)
    nbytes = len(raw)
    limit = channel_max_attach_bytes(ctx.channel)

    if limit and nbytes <= limit and classification not in _CLASSIFIED:
        return {
            "ok": True,
            "mode": "attach",
            "item_id": item_id,
            "byte_size": nbytes,
            "mime": export.get("mime"),
            "filename": item.get("name") or f"{item_id}.{fmt}",
            "content_base64": base64.b64encode(raw).decode("ascii"),
            "receipt": f"Exported item_id={item_id} ({nbytes} bytes) as channel attachment",
        }

    token = secrets.token_urlsafe(24)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires = (datetime.now(timezone.utc) + timedelta(minutes=30)).replace(microsecond=0).isoformat()
    st.create_delivery_token(
        ctx.workspace_id,
        item_id=item_id,
        token_hash=token_hash,
        expires_at=expires,
        created_by=ctx.actor_id,
    )
    base = (public_base_url or os.environ.get("KEPRIX_PUBLIC_BASE_URL") or "").rstrip("/")
    url = f"{base}/api/document-vault/delivery/{token}" if base else f"/api/document-vault/delivery/{token}"
    return {
        "ok": True,
        "mode": "url",
        "item_id": item_id,
        "byte_size": nbytes,
        "expires_at": expires,
        "download_url": url,
        "receipt": f"Export exceeds channel attach limit or is classified; short-lived URL issued for item_id={item_id}",
    }


__all__ = ["plan_export_delivery"]
