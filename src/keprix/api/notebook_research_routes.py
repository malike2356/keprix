"""Notebook research bridge API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.brain.graphiti_bridge import graphiti_enabled
from keprix.research.notebook_bridge import (
    NotebookExternalBridge,
    load_notebook_research_config,
)
from keprix.research.notebook_job_store import (
    NotebookJobStore,
    NotebookSource,
    NotebookResearchJob,
)
from keprix.research.notebook_native import NotebookNativeEngine, normalize_notebook_source

router = APIRouter(prefix="/api/research/notebook", tags=["research"])


class NotebookSourceBody(BaseModel):
    kind: str = Field(default="text", pattern="^(text|url|file|session_export)$")
    ref: str = Field(..., min_length=1)
    title: str | None = None
    excerpt: str | None = None


class NotebookResearchBody(BaseModel):
    query: str = Field(..., min_length=1)
    depth: str = Field(default="notebook", pattern="^(notebook|notebook-external)$")
    sources: list[NotebookSourceBody] = Field(default_factory=list)


class NotebookExportBody(BaseModel):
    path: str | None = None


def _complete_job(job: NotebookResearchJob, payload: dict[str, Any]) -> NotebookResearchJob:
    job.report_md = str(payload.get("report_md") or payload.get("report") or "")
    job.citations = list(payload.get("citations") or [])
    job.external_notebook_id = payload.get("external_notebook_id") or payload.get("notebook_id")
    job.status = "complete"
    job.completed_at = datetime.now(timezone.utc).isoformat()
    if not job.report_md:
        raise ValueError("Notebook bridge returned no report")
    return job


def _source_from_body(body: NotebookSourceBody) -> NotebookSource:
    return normalize_notebook_source(body.model_dump())


@router.get("/config")
async def notebook_config(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    config = load_notebook_research_config()
    return {
        "enabled": config.enabled,
        "native_max_sources": config.native_max_sources,
        "external_enabled": config.enabled and config.external_enabled and bool(config.external_command or config.external_mcp_url),
        "graph_ingest_enabled": graphiti_enabled(),
    }


@router.post("/sources")
async def notebook_source(body: NotebookSourceBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return {"source": _source_from_body(body).to_dict()}


@router.post("")
async def start_notebook_research(body: NotebookResearchBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    config = load_notebook_research_config()
    if not config.enabled:
        raise HTTPException(status_code=403, detail="Notebook research is disabled")
    sources = [_source_from_body(source) for source in body.sources]
    if len(sources) < 2:
        raise HTTPException(status_code=422, detail="Notebook research requires at least two sources")

    store = NotebookJobStore()
    job = store.create(depth=body.depth, sources=sources, query=body.query)
    try:
        if body.depth == "notebook-external" and config.external_enabled and (config.external_command or config.external_mcp_url):
            payload = NotebookExternalBridge(config=config).run(query=body.query, sources=sources)
        else:
            payload = NotebookNativeEngine(max_sources=config.native_max_sources).run(query=body.query, sources=sources)
            if body.depth == "notebook-external":
                job.error = "External notebook bridge unavailable; native Quick Notebook fallback used."
        _complete_job(job, payload)
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
    store.save(job)
    if job.status == "failed":
        raise HTTPException(status_code=502, detail=job.error or "Notebook research failed")
    return {"job": job.to_dict()}


@router.get("")
async def list_notebook_jobs(limit: int = 50, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return {"jobs": [job.to_dict() for job in NotebookJobStore().list(limit=limit)]}


@router.get("/{job_id}")
async def get_notebook_job(job_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    job = NotebookJobStore().get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Notebook research job not found")
    return {"job": job.to_dict()}


@router.post("/{job_id}/export")
async def export_notebook_job(job_id: str, body: NotebookExportBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    store = NotebookJobStore()
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Notebook research job not found")
    if not job.report_md:
        raise HTTPException(status_code=409, detail="Notebook report not ready")
    destination = store.export_markdown(job, body.path)
    return {"path": str(Path(destination)), "job": job.to_dict()}
