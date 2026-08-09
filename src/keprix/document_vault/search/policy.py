"""Index policy resolution for Document Vault (Prompt 652).

Effective policy walks parents. Root ``inherit`` defaults to ``skip``
(opt-in indexing; never auto-index every private file).
"""

from __future__ import annotations

from typing import Any

from keprix.document_vault.models import INDEX_POLICIES
from keprix.document_vault.store import DocumentVaultStore

ROOT_INHERIT_DEFAULT = "skip"


def resolve_effective_index_policy(
    store: DocumentVaultStore,
    workspace_id: str,
    item: dict[str, Any] | None,
) -> str:
    """Return ``index`` or ``skip`` for an item (never returns inherit)."""
    current = item
    seen: set[str] = set()
    while current:
        iid = str(current.get("id") or "")
        if iid in seen:
            break
        seen.add(iid)
        policy = str(current.get("index_policy") or "inherit").strip().lower()
        if policy not in INDEX_POLICIES:
            policy = "inherit"
        if policy in {"index", "skip"}:
            return policy
        parent_id = current.get("parent_id")
        if not parent_id:
            break
        current = store.get_item(workspace_id, str(parent_id), include_trashed=True)
    return ROOT_INHERIT_DEFAULT


def should_index_item(
    store: DocumentVaultStore,
    workspace_id: str,
    item: dict[str, Any] | None,
) -> bool:
    if not item:
        return False
    if item.get("trashed_at") or item.get("trashed"):
        return False
    if item.get("kind") == "folder":
        return False
    return resolve_effective_index_policy(store, workspace_id, item) == "index"


__all__ = [
    "ROOT_INHERIT_DEFAULT",
    "resolve_effective_index_policy",
    "should_index_item",
]
