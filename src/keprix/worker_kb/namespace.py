"""Worker KB RAG namespace helpers (K03)."""

from __future__ import annotations

WORKER_KB_SOURCE_TYPE = "worker_kb"


def worker_rag_user_id(workspace_id: str, worker_id: str) -> str:
    """Isolate each worker's vectors: Worker A cannot search Worker B."""
    ws = (workspace_id or "").strip() or "_"
    wid = (worker_id or "").strip() or "_"
    return f"worker:{ws}:{wid}"
