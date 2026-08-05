"""Graphiti brain bridge API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.brain.graphiti_bridge import GraphitiBridge, graphiti_enabled
from keprix.brain.graphiti_ingest_service import GraphitiIngestService
from keprix.brain.graphiti_job_store import GraphitiJobStore
from keprix.security.ingest_poison_gate import evaluate_ingest_text

router = APIRouter(prefix="/api/brain/graphiti", tags=["brain"])


class IngestBody(BaseModel):
    source_type: str = Field(..., pattern="^(research|session|vault_file|manual)$")
    source_ref: str = Field(..., min_length=1)
    content: str | None = None


class QueryBody(BaseModel):
    query: str = Field(..., min_length=1)
    max_results: int = Field(default=10, ge=1, le=50)
    include_sources: bool = True


def _guard_enabled() -> None:
    if not graphiti_enabled():
        raise HTTPException(status_code=403, detail="Graphiti bridge is disabled")


@router.get("/status")
async def graphiti_status(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return GraphitiBridge().status()


@router.post("/ingest")
async def graphiti_ingest(body: IngestBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    verdict = evaluate_ingest_text(
        body.content or body.source_ref,
        source_type=body.source_type,
        source_ref=body.source_ref,
        metadata={"graphiti": True},
    )
    if verdict.rejected:
        raise HTTPException(status_code=400, detail={"error": "ingest_rejected", **verdict.to_dict()})
    return {"job": GraphitiIngestService().ingest(source_type=body.source_type, source_ref=body.source_ref, content=body.content).to_dict()}


@router.get("/jobs")
async def graphiti_jobs(limit: int = 50, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    return {"jobs": [job.to_dict() for job in GraphitiJobStore().list(limit=limit)]}


@router.get("/jobs/{job_id}")
async def graphiti_job(job_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    job = GraphitiJobStore().get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="graphiti ingest job not found")
    return {"job": job.to_dict()}


@router.post("/query")
async def graphiti_query(body: QueryBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    return GraphitiIngestService().query(body.query, max_results=body.max_results, include_sources=body.include_sources)
