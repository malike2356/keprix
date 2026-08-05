from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from dependencies import get_embedding_service
from services.embedding_service import EmbeddingService

router = APIRouter()


class EmbedRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1)
    model: str = "voyage-3"


class IngestRequest(BaseModel):
    pack_id: str
    source_uri: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    max_tokens_per_chunk: int = Field(default=512, ge=64, le=2048)
    overlap_tokens: int = Field(default=64, ge=0, le=512)


class SearchRequest(BaseModel):
    pack_id: str
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    score_threshold: float = Field(default=0.65, ge=0.0, le=1.0)


class CreatePackRequest(BaseModel):
    pack_id: str
    display_name: str
    description: str = ""


@router.post("/embed")
async def embed(req: EmbedRequest, svc: EmbeddingService = Depends(get_embedding_service)) -> dict:
    embeddings = await svc.embed_texts(req.texts, req.model)
    return {
        "embeddings": embeddings,
        "model": req.model,
        "token_count": sum(len(text.split()) for text in req.texts),
    }


@router.post("/search")
async def search(req: SearchRequest, svc: EmbeddingService = Depends(get_embedding_service)) -> dict:
    results = await svc.search(req.pack_id, req.query, req.top_k, req.score_threshold)
    return {
        "results": [result.__dict__ for result in results],
        "pack_id": req.pack_id,
        "query": req.query,
    }


@router.post("/packs", status_code=201)
async def create_pack(req: CreatePackRequest, svc: EmbeddingService = Depends(get_embedding_service)) -> dict:
    await svc.create_pack(req.pack_id, req.display_name, req.description)
    return {"pack_id": req.pack_id, "status": "created"}


@router.get("/packs")
async def list_packs(svc: EmbeddingService = Depends(get_embedding_service)) -> dict:
    return {"packs": await svc.list_packs()}


@router.delete("/packs/{pack_id}")
async def delete_pack(pack_id: str, svc: EmbeddingService = Depends(get_embedding_service)) -> dict:
    await svc.delete_pack(pack_id)
    return {"pack_id": pack_id, "status": "deleted"}


@router.post("/ingest")
async def ingest_document(req: IngestRequest, svc: EmbeddingService = Depends(get_embedding_service)) -> dict:
    chunks_stored = await svc.ingest_document(
        pack_id=req.pack_id,
        source_uri=req.source_uri,
        content=req.content,
        metadata=req.metadata,
        max_tokens_per_chunk=req.max_tokens_per_chunk,
        overlap_tokens=req.overlap_tokens,
    )
    return {
        "pack_id": req.pack_id,
        "source_uri": req.source_uri,
        "chunks_stored": chunks_stored,
    }
