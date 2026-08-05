"""Memory and RAG HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.memory.episodic.store import create_episodic_store
from keprix.memory.rag.codebase_indexer import CODEBASE_SOURCE_TYPE, CodebaseRagIndexer
from keprix.memory.rag.indexer import RagIndexer
from keprix.memory.rag.retriever import RagRetriever
from keprix.security.ingest_poison_gate import evaluate_ingest_text
from keprix.memory.rag.self_knowledge import (
    SELF_KNOWLEDGE_SOURCE_TYPE,
    SELF_KNOWLEDGE_USER_ID,
    SelfKnowledgeIndexer,
    retrieve_self_knowledge,
)

router = APIRouter(tags=["memory"])
_episodic_store = create_episodic_store()
_rag_indexer = RagIndexer()
_rag_retriever = RagRetriever(indexer=_rag_indexer)


def _uid(user: dict, x_user_id: str | None = None) -> str:
    if x_user_id:
        return x_user_id
    return str(user.get("id") or user.get("username") or "default")


class SaveMemoryRequest(BaseModel):
    content: str
    tags: list[str] = Field(default_factory=list)
    session_id: str | None = None


class UpdateMemoryRequest(BaseModel):
    content: str | None = None
    tags: list[str] | None = None


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
    source_types: list[str] | None = None


class CodebaseIndexRequest(BaseModel):
    include_roots: list[str] | None = None
    max_files: int = Field(default=2000, ge=1, le=10000)
    max_file_bytes: int = Field(default=250_000, ge=1024, le=1_000_000)


class CodebaseSearchRequest(BaseModel):
    query: str
    limit: int = Field(default=8, ge=1, le=50)
    hybrid: bool = True


class SelfKnowledgeIndexRequest(BaseModel):
    include_codebase: bool = True
    include_docs: bool = True
    include_capabilities: bool = True
    max_files: int = Field(default=2000, ge=1, le=10000)
    max_file_bytes: int = Field(default=250_000, ge=1024, le=1_000_000)


class SelfKnowledgeSearchRequest(BaseModel):
    query: str
    limit: int = Field(default=8, ge=1, le=50)
    hybrid: bool = True


@router.get("/api/memory/list")
async def list_memories(
    user: dict = Depends(get_current_user),
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    memories = await _episodic_store.list_all(_uid(user, x_user_id))
    return {"memories": [memory.to_dict() for memory in memories]}


@router.post("/api/memory/save")
async def save_memory(
    body: SaveMemoryRequest,
    user: dict = Depends(get_current_user),
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    memory_id = await _episodic_store.save(
        _uid(user, x_user_id),
        content,
        metadata={"tags": body.tags, "session_id": body.session_id, "source": "manual", "memory_type": "semantic"},
    )
    return {"ok": True, "memory_id": memory_id}


@router.patch("/api/memory/{memory_id}")
async def update_memory(
    memory_id: str,
    body: UpdateMemoryRequest,
    user: dict = Depends(get_current_user),
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    content = body.content.strip() if isinstance(body.content, str) else None
    if content is not None and not content:
        raise HTTPException(status_code=400, detail="content cannot be empty")
    if content is None and body.tags is None:
        raise HTTPException(status_code=400, detail="Nothing to update")
    updated = await _episodic_store.update(
        _uid(user, x_user_id),
        memory_id,
        content=content,
        tags=body.tags,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"ok": True, "memory_id": memory_id}


@router.delete("/api/memory/{memory_id}")
async def delete_memory(
    memory_id: str,
    user: dict = Depends(get_current_user),
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    await _episodic_store.delete(_uid(user, x_user_id), memory_id)
    return {"ok": True}


@router.post("/api/memory/search")
async def search_memories(
    body: SearchMemoryRequest,
    user: dict = Depends(get_current_user),
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    results = await _episodic_store.search(_uid(user, x_user_id), query, limit=body.limit)
    return {"results": [memory.to_dict() for memory in results]}


@router.post("/api/memory/clear")
async def clear_memories(
    user: dict = Depends(get_current_user),
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    await _episodic_store.clear(_uid(user, x_user_id))
    return {"ok": True}


@router.post("/api/rag/ingest")
async def ingest_rag_source(
    body: RagIngestRequest,
    user: dict = Depends(get_current_user),
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    user_id = _uid(user, x_user_id)
    if not body.source_id.strip() or not body.content.strip():
        raise HTTPException(status_code=400, detail="source_id and content are required")
    verdict = evaluate_ingest_text(
        body.content,
        source_type=body.source_type,
        source_ref=body.source_id,
        metadata={"user_id": user_id},
    )
    if verdict.rejected:
        raise HTTPException(status_code=400, detail={"error": "ingest_rejected", **verdict.to_dict()})
    chunks = await _rag_indexer.ingest(
        user_id=user_id,
        source_type=body.source_type,
        source_id=body.source_id,
        content=body.content,
        trust=verdict.trust,
    )
    return {"ok": True, "chunks": chunks, "verdict": verdict.to_dict()}


@router.get("/api/rag/sources")
async def list_rag_sources(
    user: dict = Depends(get_current_user),
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    sources = await _rag_indexer.list_sources(_uid(user, x_user_id))
    return {"sources": sources}


@router.delete("/api/rag/source/{source_id}")
async def delete_rag_source(
    source_id: str,
    user: dict = Depends(get_current_user),
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    deleted = await _rag_indexer.delete_source(_uid(user, x_user_id), source_id)
    return {"ok": True, "deleted_chunks": deleted}


@router.post("/api/rag/search")
async def search_rag(
    body: RagSearchRequest,
    user: dict = Depends(get_current_user),
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    user_id = _uid(user, x_user_id)
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    if body.hybrid:
        results = await _rag_retriever.hybrid_search(
            user_id,
            query,
            limit=body.limit,
            source_types=body.source_types,
        )
    else:
        results = await _rag_retriever.search(
            user_id,
            query,
            limit=body.limit,
            source_types=body.source_types,
        )
    return {"results": results}


@router.post("/api/rag/codebase/index")
async def index_codebase(
    body: CodebaseIndexRequest,
    user: dict = Depends(get_current_user),
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    user_id = _uid(user, x_user_id)
    stats = await CodebaseRagIndexer(_rag_indexer).index(
        user_id=user_id,
        include_roots=body.include_roots,
        max_files=body.max_files,
        max_file_bytes=body.max_file_bytes,
    )
    return {"ok": True, **stats.to_dict()}


@router.post("/api/rag/codebase/search")
async def search_codebase(
    body: CodebaseSearchRequest,
    user: dict = Depends(get_current_user),
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    user_id = _uid(user, x_user_id)
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    if body.hybrid:
        results = await _rag_retriever.hybrid_search(
            user_id,
            query,
            limit=body.limit,
            source_types=[CODEBASE_SOURCE_TYPE],
        )
    else:
        results = await _rag_retriever.search(
            user_id,
            query,
            limit=body.limit,
            source_types=[CODEBASE_SOURCE_TYPE],
        )
    return {"results": results}


@router.post("/api/rag/self-knowledge/index")
async def index_self_knowledge(
    body: SelfKnowledgeIndexRequest,
) -> dict[str, Any]:
    """Index Keprix docs, capabilities, and codebase into the shared system RAG user."""
    stats = await SelfKnowledgeIndexer(_rag_indexer).index(
        include_codebase=body.include_codebase,
        include_docs=body.include_docs,
        include_capabilities=body.include_capabilities,
        max_files=body.max_files,
        max_file_bytes=body.max_file_bytes,
        user_id=SELF_KNOWLEDGE_USER_ID,
    )
    return {"ok": True, **stats.to_dict()}


@router.post("/api/rag/self-knowledge/search")
async def search_self_knowledge(body: SelfKnowledgeSearchRequest) -> dict[str, Any]:
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    results = await retrieve_self_knowledge(
        query,
        limit=body.limit,
        hybrid=body.hybrid,
        user_id=SELF_KNOWLEDGE_USER_ID,
        retriever=_rag_retriever,
    )
    return {
        "results": results,
        "user_id": SELF_KNOWLEDGE_USER_ID,
        "source_types": [SELF_KNOWLEDGE_SOURCE_TYPE, CODEBASE_SOURCE_TYPE],
    }
