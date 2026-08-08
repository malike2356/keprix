"""Worker knowledge base service: metadata + pgvector/in-memory RAG (K03)."""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

from keprix.memory.embeddings import EmbeddingService
from keprix.memory.rag.indexer import RagIndexer, estimate_tokens
from keprix.memory.rag.retriever import RagRetriever
from keprix.worker_kb.namespace import WORKER_KB_SOURCE_TYPE, worker_rag_user_id
from keprix.worker_kb.store import WorkerKbStore, get_worker_kb_store

logger = logging.getLogger(__name__)

ENTRY_TYPES = ("document", "faq", "instruction")


class WorkerKbService:
    def __init__(
        self,
        store: WorkerKbStore | None = None,
        indexer: RagIndexer | None = None,
        retriever: RagRetriever | None = None,
    ) -> None:
        self.store = store or get_worker_kb_store()
        embeddings = EmbeddingService(deterministic=True)
        self.indexer = indexer or RagIndexer(embeddings=embeddings)
        self.retriever = retriever or RagRetriever(
            indexer=self.indexer,
            embeddings=self.indexer.embeddings,
        )

    def _kb(self, workspace_id: str, worker_id: str, name: str = "Default") -> dict[str, Any]:
        return self.store.get_or_create_kb(workspace_id, worker_id, name=name)

    def _assert_entry_scope(
        self,
        entry_id: str,
        workspace_id: str,
        worker_id: str,
    ) -> dict[str, Any]:
        row = self.store.resolve_entry_scope(entry_id)
        if not row:
            raise LookupError("entry_not_found")
        if row["workspace_id"] != workspace_id or row["worker_id"] != worker_id:
            raise PermissionError("entry_not_in_worker_namespace")
        return row

    async def _embed_entry(
        self,
        *,
        workspace_id: str,
        worker_id: str,
        entry: dict[str, Any],
    ) -> int:
        user_id = worker_rag_user_id(workspace_id, worker_id)
        title = str(entry.get("title") or "").strip()
        content = str(entry.get("content") or "")
        payload = f"{title}\n\n{content}".strip() if title else content
        source_type = "markdown" if entry.get("entry_type") == "document" else "plaintext"
        return await self.indexer.ingest(
            user_id=user_id,
            source_type=source_type,
            source_id=str(entry["id"]),
            content=payload,
            trust="trusted",
        )

    async def _drop_embedding(self, workspace_id: str, worker_id: str, entry_id: str) -> int:
        user_id = worker_rag_user_id(workspace_id, worker_id)
        return await self.indexer.delete_source(user_id, entry_id)

    async def add_entry(
        self,
        workspace_id: str,
        worker_id: str,
        *,
        content: str,
        entry_type: str = "faq",
        title: str | None = None,
        source: str | None = "manual",
        source_file: str | None = None,
        kb_name: str = "Default",
    ) -> dict[str, Any]:
        et = (entry_type or "faq").strip().lower()
        if et not in ENTRY_TYPES:
            raise ValueError(f"entry_type must be one of {ENTRY_TYPES}")
        text = (content or "").strip()
        if not text:
            raise ValueError("content is required")
        kb = self._kb(workspace_id, worker_id, name=kb_name)
        entry = self.store.add_entry(
            str(kb["id"]),
            entry_type=et,
            content=text,
            title=title,
            source=source or "manual",
            source_file=source_file,
            token_count=estimate_tokens(text),
            enabled=True,
        )
        chunks = await self._embed_entry(workspace_id=workspace_id, worker_id=worker_id, entry=entry)
        return {"entry": entry, "chunks": chunks, "knowledge_base": kb}

    async def search(
        self,
        workspace_id: str,
        worker_id: str,
        query: str,
        *,
        limit: int = 5,
        hybrid: bool = True,
    ) -> dict[str, Any]:
        q = (query or "").strip()
        if not q:
            return {"results": [], "query": query}
        # Ensure KB exists (empty is fine)
        self._kb(workspace_id, worker_id)
        user_id = worker_rag_user_id(workspace_id, worker_id)
        if hybrid:
            hits = await self.retriever.hybrid_search(user_id, q, limit=limit * 2)
        else:
            hits = await self.retriever.search(user_id, q, limit=limit * 2)

        # Filter to enabled entries only (source field is source_id in memory results)
        enabled_ids = {
            str(e["id"])
            for e in self.store.list_entries(str(self._kb(workspace_id, worker_id)["id"]), enabled_only=True)
        }
        filtered: list[dict[str, Any]] = []
        for hit in hits:
            source = str(hit.get("source") or "")
            # Retriever formats source as "{source_type}:{source_id}"
            entry_id = source.split(":", 1)[-1] if source else ""
            if entry_id not in enabled_ids:
                continue
            enriched = dict(hit)
            enriched["entry_id"] = entry_id
            filtered.append(enriched)
            if len(filtered) >= limit:
                break

        return {
            "workspace_id": workspace_id,
            "worker_id": worker_id,
            "query": q,
            "results": filtered[:limit],
        }

    def list_entries(
        self,
        workspace_id: str,
        worker_id: str,
        *,
        enabled_only: bool = False,
    ) -> dict[str, Any]:
        kb = self._kb(workspace_id, worker_id)
        entries = self.store.list_entries(str(kb["id"]), enabled_only=enabled_only)
        return {"knowledge_base": kb, "entries": entries, "count": len(entries)}

    async def delete_entry(self, workspace_id: str, worker_id: str, entry_id: str) -> dict[str, Any]:
        self._assert_entry_scope(entry_id, workspace_id, worker_id)
        await self._drop_embedding(workspace_id, worker_id, entry_id)
        ok = self.store.delete_entry(entry_id)
        return {"deleted": ok, "entry_id": entry_id}

    async def toggle_entry(
        self,
        workspace_id: str,
        worker_id: str,
        entry_id: str,
        *,
        enabled: bool | None = None,
    ) -> dict[str, Any]:
        row = self._assert_entry_scope(entry_id, workspace_id, worker_id)
        new_enabled = (not bool(row.get("enabled"))) if enabled is None else bool(enabled)
        updated = self.store.set_enabled(entry_id, new_enabled)
        if not updated:
            raise LookupError("entry_not_found")
        if new_enabled:
            chunks = await self._embed_entry(workspace_id=workspace_id, worker_id=worker_id, entry=updated)
        else:
            chunks = await self._drop_embedding(workspace_id, worker_id, entry_id)
        return {"entry": updated, "chunks": chunks}

    def get_context(
        self,
        workspace_id: str,
        worker_id: str,
        *,
        max_chars: int = 8_000,
    ) -> dict[str, Any]:
        kb = self._kb(workspace_id, worker_id)
        entries = self.store.list_entries(str(kb["id"]), enabled_only=True)
        lines = [
            f"## Worker knowledge base ({worker_id})",
            "Use the following enabled knowledge when answering.",
            "",
        ]
        used = 0
        included = 0
        for entry in entries:
            title = entry.get("title") or entry.get("entry_type") or "entry"
            block = f"### {title} [{entry.get('entry_type')}]\n{entry.get('content')}\n\n"
            if used + len(block) > max_chars:
                break
            lines.append(block)
            used += len(block)
            included += 1
        text = "\n".join(lines).strip()
        return {
            "workspace_id": workspace_id,
            "worker_id": worker_id,
            "entries_included": included,
            "context": text,
        }

    async def search_context(
        self,
        workspace_id: str,
        worker_id: str,
        query: str,
        *,
        limit: int = 5,
        max_chars: int = 6_000,
    ) -> str:
        result = await self.search(workspace_id, worker_id, query, limit=limit, hybrid=True)
        hits = result.get("results") or []
        if not hits:
            return ""
        lines = [
            f"## Retrieved worker knowledge ({worker_id})",
            "Use these chunks when answering. Do not invent facts beyond this context.",
            "",
        ]
        used = 0
        for idx, item in enumerate(hits, start=1):
            content = str(item.get("content") or "").strip()
            score = item.get("score")
            header = f"### Hit {idx}"
            if isinstance(score, (int, float)):
                header += f" (score={float(score):.3f})"
            block = f"{header}\n{content}\n"
            if used + len(block) > max_chars:
                break
            lines.append(block)
            used += len(block)
        return "\n".join(lines).strip()


_service: WorkerKbService | None = None
_svc_lock = threading.Lock()


def get_worker_kb_service(store: WorkerKbStore | None = None) -> WorkerKbService:
    global _service
    if store is not None:
        return WorkerKbService(store=store)
    with _svc_lock:
        if _service is None:
            _service = WorkerKbService()
        return _service


def reset_worker_kb_service_for_tests(store: WorkerKbStore | None = None) -> WorkerKbService:
    global _service
    with _svc_lock:
        _service = WorkerKbService(store=store) if store is not None else WorkerKbService()
        return _service


def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)
