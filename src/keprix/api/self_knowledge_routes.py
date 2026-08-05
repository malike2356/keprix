"""Admin API routes for Keprix self-knowledge RAG management."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from keprix.api.auth import require_admin

router = APIRouter(prefix="/api/self-knowledge", tags=["self-knowledge"])


class SearchRequest(BaseModel):
    query: str
    limit: int = 8
    hybrid: bool = True


@router.get("/status")
async def get_status(_: None = Depends(require_admin)) -> dict[str, Any]:
    """Return current self-knowledge index status."""
    try:
        from keprix.memory.rag.self_knowledge import (
            SELF_KNOWLEDGE_SOURCE_TYPE,
            SELF_KNOWLEDGE_USER_ID,
        )
        from keprix.memory.rag.indexer import RagIndexer

        indexer = RagIndexer()
        sources = await indexer.list_sources(SELF_KNOWLEDGE_USER_ID)
        self_sources = [s for s in sources if s.get("source_type") == SELF_KNOWLEDGE_SOURCE_TYPE]
        total_chunks = sum(s.get("chunk_count", 0) for s in self_sources)
        return {
            "indexed": len(self_sources) > 0,
            "document_count": len(self_sources),
            "total_chunks": total_chunks,
            "user_id": SELF_KNOWLEDGE_USER_ID,
            "source_type": SELF_KNOWLEDGE_SOURCE_TYPE,
            "sources": self_sources[:50],
        }
    except Exception as exc:
        return {
            "indexed": False,
            "document_count": 0,
            "total_chunks": 0,
            "error": str(exc),
        }


@router.post("/ingest")
async def trigger_ingest(
    include_codebase: bool = True,
    include_docs: bool = True,
    max_files: int = 1500,
    _: None = Depends(require_admin),
) -> dict[str, Any]:
    """Trigger a full self-knowledge re-ingestion (runs in background)."""
    from keprix.self_knowledge.ingestor import SelfKnowledgeIngestor

    ingestor = SelfKnowledgeIngestor(
        include_codebase=include_codebase,
        include_docs=include_docs,
        max_files=max_files,
    )

    async def _run() -> None:
        await ingestor.ingest()

    asyncio.create_task(_run())
    return {"status": "ingestion_started", "include_codebase": include_codebase, "include_docs": include_docs}


@router.post("/ingest/wait")
async def trigger_ingest_wait(
    include_codebase: bool = False,
    include_docs: bool = True,
    max_files: int = 500,
    _: None = Depends(require_admin),
) -> dict[str, Any]:
    """Trigger ingestion and wait for completion (synthetic docs + selected layers only)."""
    from keprix.self_knowledge.ingestor import SelfKnowledgeIngestor

    result = await SelfKnowledgeIngestor(
        include_codebase=include_codebase,
        include_docs=include_docs,
        max_files=max_files,
    ).ingest()
    return result.to_dict()


@router.post("/search")
async def search_self_knowledge(
    body: SearchRequest,
    _: None = Depends(require_admin),
) -> dict[str, Any]:
    """Search the self-knowledge store."""
    from keprix.memory.rag.self_knowledge import retrieve_self_knowledge, format_self_knowledge_context

    results = await retrieve_self_knowledge(
        body.query,
        limit=body.limit,
        hybrid=body.hybrid,
    )
    return {
        "query": body.query,
        "results": results,
        "formatted": format_self_knowledge_context(results, max_chars=8_000),
    }
