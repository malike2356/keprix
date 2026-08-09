"""Sync content indexer for Document Vault (Prompt 652).

Uses local chunk table for CE offline. Optional RagIndexer mirror when available.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from keprix.document_vault.models import sha256_text
from keprix.document_vault.search.citations import make_source_id
from keprix.document_vault.search.policy import should_index_item
from keprix.document_vault.service import DocumentVaultService
from keprix.document_vault.store import DocumentVaultStore


def chunk_text(text: str, *, chunk_words: int = 200, overlap: int = 40) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + chunk_words)
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(words):
            break
        start = max(0, end - overlap)
    return chunks


def extract_indexable_text(data: bytes, *, kind: str = "", filename: str = "") -> str:
    """Best-effort plaintext for indexing; never execute content."""
    name = (filename or "").lower()
    if kind == "html" or name.endswith((".html", ".htm")):
        text = data.decode("utf-8", errors="ignore")
        text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", text)
        text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        return " ".join(text.split())
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        # Lightweight PDF-ish literals
        raw = data.decode("latin-1", errors="ignore")
        literals = re.findall(r"\(([^()\\]{3,})\)", raw)
        if literals:
            return " ".join(literals)
        return ""


class VaultContentIndexer:
    def __init__(
        self,
        store: DocumentVaultStore,
        service: DocumentVaultService | None = None,
    ) -> None:
        self.store = store
        self.service = service

    def index_item(self, workspace_id: str, item_id: str, *, actor_id: str | None = None) -> dict[str, Any]:
        item = self.store.get_item(workspace_id, item_id, include_trashed=True)
        if not item:
            return {"ok": False, "error_code": "not_found"}
        if not should_index_item(self.store, workspace_id, item):
            self.deindex_item(workspace_id, item_id)
            self.store.upsert_index_entry(
                workspace_id,
                item_id=item_id,
                revision=int(item.get("current_revision") or 0),
                source_id=make_source_id(workspace_id, item_id, int(item.get("current_revision") or 0)),
                status="skipped",
                chunk_count=0,
            )
            return {"ok": True, "status": "skipped", "item_id": item_id}

        revision = int(item.get("current_revision") or 0)
        source_id = make_source_id(workspace_id, item_id, revision)
        text = ""
        checksum = None
        if self.service and item.get("kind") != "folder":
            try:
                data = self.service.read_bytes(workspace_id, item_id)
                text = extract_indexable_text(data, kind=str(item.get("kind") or ""), filename=str(item.get("name") or ""))
                checksum = sha256_text(text) if text else None
            except Exception as exc:
                self.store.upsert_index_entry(
                    workspace_id,
                    item_id=item_id,
                    revision=revision,
                    source_id=source_id,
                    status="error",
                    chunk_count=0,
                    error=str(exc)[:500],
                )
                return {"ok": False, "error_code": "extract_failed", "error": str(exc)}

        # Strip obvious prompt-injection control lines from indexed text (defense in depth).
        text = _sanitize_indexed_text(text)
        chunks = chunk_text(text)
        self.store.replace_index_chunks(workspace_id, item_id, revision, chunks)
        self.store.upsert_index_entry(
            workspace_id,
            item_id=item_id,
            revision=revision,
            source_id=source_id,
            status="indexed",
            chunk_count=len(chunks),
            content_checksum=checksum,
        )
        _mirror_rag(workspace_id, source_id, text)
        return {
            "ok": True,
            "status": "indexed",
            "item_id": item_id,
            "revision": revision,
            "chunk_count": len(chunks),
            "source_id": source_id,
        }

    def deindex_item(self, workspace_id: str, item_id: str) -> dict[str, Any]:
        removed = self.store.delete_index_for_item(workspace_id, item_id)
        # Best-effort RagIndexer cleanup for known revisions is handled by delete_index_for_item
        return {"ok": True, "removed": removed, "item_id": item_id}


def _sanitize_indexed_text(text: str) -> str:
    lines = []
    for line in (text or "").splitlines():
        lower = line.strip().lower()
        if lower.startswith("ignore previous instructions") or lower.startswith("system:"):
            continue
        lines.append(line)
    return "\n".join(lines)


def _mirror_rag(workspace_id: str, source_id: str, text: str) -> None:
    if not text.strip():
        return
    try:
        from keprix.memory.rag.indexer import RagIndexer

        indexer = RagIndexer()

        async def _run() -> None:
            await indexer.delete_source(workspace_id, source_id)
            await indexer.ingest(
                user_id=workspace_id,
                source_type="document_vault",
                source_id=source_id,
                content=text,
                trust="trusted",
            )

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return
            loop.run_until_complete(_run())
        except RuntimeError:
            asyncio.run(_run())
    except Exception:
        # Local chunk table remains source of truth for vault content search.
        return


__all__ = ["VaultContentIndexer", "chunk_text", "extract_indexable_text"]
