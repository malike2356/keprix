"""Lightweight channel vault workflow helpers (progress markers)."""

from __future__ import annotations

from typing import Any

from keprix.document_vault.store import DocumentVaultStore, get_document_vault_store


def start_channel_job(
    workspace_id: str,
    *,
    kind: str,
    item_id: str | None = None,
    idempotency_key: str | None = None,
    payload: dict[str, Any] | None = None,
    store: DocumentVaultStore | None = None,
) -> dict[str, Any]:
    st = store or get_document_vault_store()
    return st.enqueue_job(
        workspace_id,
        kind=f"channel:{kind}",
        item_id=item_id,
        idempotency_key=idempotency_key,
        payload=payload or {},
    )


__all__ = ["start_channel_job"]
