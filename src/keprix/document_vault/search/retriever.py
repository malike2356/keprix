"""Content retrieval with policy, trash, grants, and revision citations."""

from __future__ import annotations

from typing import Any, Sequence

from keprix.document_vault.search.citations import VaultCitation, make_source_id
from keprix.document_vault.search.policy import should_index_item
from keprix.document_vault.security.grants import require_grant
from keprix.document_vault.store import DocumentVaultStore


def content_search(
    store: DocumentVaultStore,
    workspace_id: str,
    query: str,
    *,
    limit: int = 20,
    grants: Sequence[str] | None = None,
) -> dict[str, Any]:
    require_grant(grants, "vault.search")
    q = str(query or "").strip()
    if not q:
        return {"ok": True, "query": q, "hits": [], "count": 0}

    rows = store.search_index_chunks(workspace_id, q, limit=max(1, min(limit, 100)))
    hits: list[dict[str, Any]] = []
    for row in rows:
        item = store.get_item(workspace_id, row["item_id"], include_trashed=False)
        if not item:
            continue
        if not should_index_item(store, workspace_id, item):
            continue
        # Prefer current revision only; stale indexed revisions are ignored.
        current_rev = int(item.get("current_revision") or 0)
        chunk_rev = int(row.get("revision") or 0)
        if chunk_rev != current_rev:
            continue
        citation = VaultCitation(
            item_id=str(item["id"]),
            revision=current_rev,
            name=str(item.get("name") or ""),
            snippet=str(row.get("text") or "")[:280],
            score=float(row.get("score") or 0.0),
            source_id=make_source_id(workspace_id, str(item["id"]), current_rev),
            workspace_id=workspace_id,
        )
        hits.append(citation.as_dict())
        if len(hits) >= limit:
            break
    return {"ok": True, "query": q, "hits": hits, "count": len(hits)}


__all__ = ["content_search"]
