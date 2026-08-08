"""Allowlisted RAG retrieve with public/private/relationship boundaries."""

from __future__ import annotations

import threading
from typing import Any

_LOCK = threading.RLock()
_CORPUS: list[dict[str, Any]] = [
    {
        "id": "fact-1",
        "tenant_id": "owner-laud",
        "sensitivity": "public",
        "label": "stated_facts",
        "text": "iLaud publishes educational content about personal branding.",
        "relationship_scope": "public",
    },
    {
        "id": "pref-1",
        "tenant_id": "owner-laud",
        "sensitivity": "private",
        "label": "inferred_preferences",
        "text": "Prefers short paragraphs and plain English.",
        "relationship_scope": "owner",
    },
    {
        "id": "priv-1",
        "tenant_id": "owner-laud",
        "sensitivity": "relationship",
        "label": "private_correspondence",
        "text": "Private note about a family member; never for public drafts.",
        "relationship_scope": "relationship",
    },
    {
        "id": "other-tenant",
        "tenant_id": "other-tenant",
        "sensitivity": "private",
        "label": "stated_facts",
        "text": "Must never appear in owner-laud retrieval.",
        "relationship_scope": "owner",
    },
]


def reset_rag() -> None:
    with _LOCK:
        pass  # fixture corpus is static; reserved for future mutation


def allowlist() -> list[str]:
    return ["stated_facts", "inferred_preferences", "private_correspondence", "generated_style"]


def search(
    *,
    query: str,
    tenant_id: str,
    audience: str = "public",
    allow_relationship: bool = False,
) -> list[dict[str, Any]]:
    q = (query or "").lower()
    hits: list[dict[str, Any]] = []
    with _LOCK:
        for row in _CORPUS:
            if row["tenant_id"] != tenant_id:
                continue
            if audience == "public" and row["sensitivity"] in {"relationship", "private"}:
                if row["sensitivity"] == "relationship" and not allow_relationship:
                    continue
                if row["sensitivity"] == "private" and audience == "public":
                    # private preferences may inform style but not be quoted as public facts
                    if row["label"] != "inferred_preferences":
                        continue
            if row["sensitivity"] == "relationship" and not allow_relationship:
                continue
            if q and q not in row["text"].lower() and q not in row["label"]:
                continue
            hits.append(
                {
                    "id": row["id"],
                    "label": row["label"],
                    "sensitivity": row["sensitivity"],
                    "text": row["text"],
                    "relationship_scope": row["relationship_scope"],
                }
            )
    return hits
