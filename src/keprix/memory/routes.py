"""Memory and RAG HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from keprix.memory.episodic.store import create_episodic_store
from keprix.memory.rag.indexer import RagIndexer
from keprix.memory.rag.retriever import RagRetriever

router = APIRouter(tags=["memory"])
_episodic_store = create_episodic_store()
_rag_indexer = RagIndexer()
_rag_retriever = RagRetriever(indexer=_rag_indexer)


def _current_user(request: Request, x_user_id: str | None = None) -> str:
    if x_user_id:
        return x_user_id
    header_user = request.headers.get("X-User-Id")
    if header_user:
        return header_user
    return "default"


class SaveMemoryRequest(BaseModel):
    content: str
    tags: list[str] = Field(default_factory=list)
    session_id: str | None = None


class SearchMemoryRequest(BaseModel):
    query: str
    limit: int = 10


class RagIngestRequest(BaseModel):
    source_type: str = "plaintext"
    source_id: str
    content: str


class RagSearchRequest(BaseModel):
    query: str
    limit: int = 5
    hybrid: bool = True


@router.get("/api/memory/list")
async def list_memories(request: Request, x_user_id: str | None = Header(default=None)) -> dict[str, Any]:
    user_id = _current_user(request, x_user_id)
    memories = await _episodic_store.list_all(user_id)
    return {"memories": [memory.to_dict() for memory in memories]}


@router.post("/api/memory/save")
async def save_memory(
    body: SaveMemoryRequest,
    request: Request,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    user_id = _current_user(request, x_user_id)
    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    memory_id = await _episodic_store.save(
        user_id,
        content,
        metadata={"tags": body.tags, "session_id": body.session_id},
    )
    return {"ok": True, "memory_id": memory_id}


@router.delete("/api/memory/{memory_id}")
async def delete_memory(
    memory_id: str,
    request: Request,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    user_id = _current_user(request, x_user_id)
    await _episodic_store.delete(user_id, memory_id)
    return {"ok": True}


@router.post("/api/memory/search")
async def search_memories(
    body: SearchMemoryRequest,
    request: Request,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    user_id = _current_user(request, x_user_id)
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    results = await _episodic_store.search(user_id, query, limit=body.limit)
    return {"results": [memory.to_dict() for memory in results]}


@router.post("/api/memory/clear")
async def clear_memories(
    request: Request,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    user_id = _current_user(request, x_user_id)
    await _episodic_store.clear(user_id)
    return {"ok": True}


@router.post("/api/rag/ingest")
async def ingest_rag_source(
    body: RagIngestRequest,
    request: Request,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    user_id = _current_user(request, x_user_id)
    if not body.source_id.strip() or not body.content.strip():
        raise HTTPException(status_code=400, detail="source_id and content are required")
    chunks = await _rag_indexer.ingest(
        user_id=user_id,
        source_type=body.source_type,
        source_id=body.source_id,
        content=body.content,
    )
    return {"ok": True, "chunks": chunks}


@router.get("/api/rag/sources")
async def list_rag_sources(
    request: Request,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    user_id = _current_user(request, x_user_id)
    sources = await _rag_indexer.list_sources(user_id)
    return {"sources": sources}


@router.delete("/api/rag/source/{source_id}")
async def delete_rag_source(
    source_id: str,
    request: Request,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    user_id = _current_user(request, x_user_id)
    deleted = await _rag_indexer.delete_source(user_id, source_id)
    return {"ok": True, "deleted_chunks": deleted}


@router.post("/api/rag/search")
async def search_rag(
    body: RagSearchRequest,
    request: Request,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    user_id = _current_user(request, x_user_id)
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    if body.hybrid:
        results = await _rag_retriever.hybrid_search(user_id, query, limit=body.limit)
    else:
        results = await _rag_retriever.search(user_id, query, limit=body.limit)
    return {"results": results}
