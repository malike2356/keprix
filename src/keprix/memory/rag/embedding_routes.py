"""Embedding utility routes."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from keprix.memory.embeddings import EmbeddingService

router = APIRouter(prefix="/api/rag/embeddings", tags=["rag-embeddings"])
_embedding_service = EmbeddingService(deterministic=True)


class EmbedRequest(BaseModel):
    text: str


class EmbedBatchRequest(BaseModel):
    texts: list[str] = Field(default_factory=list)


@router.post("")
async def embed_text(body: EmbedRequest) -> dict:
    vector = await _embedding_service.embed(body.text)
    return {"dimensions": len(vector), "embedding": vector}


@router.post("/batch")
async def embed_batch(body: EmbedBatchRequest) -> dict:
    vectors = await _embedding_service.embed_many(body.texts)
    return {"count": len(vectors), "embeddings": vectors}
