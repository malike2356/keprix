"""Deep research HTTP routes."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from keprix.research.export import ResearchExportFormat, export_research_job

from keprix.research.registry import TASK_ID_RE, get_research_registry
from keprix.research.pipeline import schedule_research_job
from keprix.research.search import web_search
from keprix.research.store import get_research_store
from keprix.research.errors import ResearchConfigError, ResearchPipelineError
from keprix.security.validation import ValidationError, default_validator

router = APIRouter(prefix="/api/research", tags=["research"])


def _validate_task_id(task_id: str) -> None:
    if not TASK_ID_RE.fullmatch(task_id):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid task ID format: {task_id!r}. Expected rsch-[a-z0-9]{{8}}",
        )


def _user_id(request: Request) -> str:
    header = request.headers.get("x-user-id", "").strip()
    if header:
        return header
    return "local"


class ResearchStartBody(BaseModel):
    query: str = Field(..., min_length=1)
    depth: str = "standard"
    model: str | None = None

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        return default_validator.validate_string(value, "query")

    @field_validator("depth")
    @classmethod
    def validate_depth(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"quick", "standard", "deep"}:
            raise ValueError("depth must be quick, standard, or deep")
        return value


class SearchBody(BaseModel):
    query: str = Field(..., min_length=1)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        return default_validator.validate_string(value, "query")


class ResearchExportBody(BaseModel):
    format: ResearchExportFormat = "pdf"
    include_cover: bool = True
    prepared_by: str | None = None
    classification: str = ""


def _export_response(job_id: str, result: dict[str, Any]) -> Response:
    content = result["content"]
    filename = result.get("filename") or f"research-{job_id}.{result['format']}"
    if isinstance(content, str):
        body: str | bytes = content
    else:
        body = content
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if result.get("setup_instructions"):
        headers["X-Export-Fallback"] = str(result["setup_instructions"])[:500]
    if result.get("format_returned"):
        headers["X-Format-Returned"] = str(result["format_returned"])
    if result.get("renderer"):
        headers["X-PDF-Renderer"] = str(result["renderer"])
    return Response(content=body, media_type=result["mime"], headers=headers)


async def _load_job_for_export(job_id: str, request: Request):
    _validate_task_id(job_id)
    store = get_research_store()
    user = _user_id(request)
    job = await store.get(job_id, user)
    if job is None:
        raise HTTPException(404, "Job not found")
    if job.status == "running" or not job.report_markdown:
        raise HTTPException(409, "Report not ready")
    return job


@router.post("/start")
async def start_research(body: ResearchStartBody, request: Request) -> dict[str, str]:
    store = get_research_store()
    user = _user_id(request)
    job = await store.create(
        user_id=user,
        query=body.query,
        depth=body.depth,
        model=body.model,
    )
    schedule_research_job(job)
    return {"job_id": job.id, "status": "running"}


@router.get("/jobs")
async def list_jobs(request: Request) -> dict[str, Any]:
    store = get_research_store()
    user = _user_id(request)
    jobs = await store.list_for_user(user)
    return {
        "jobs": [
            {k: v for k, v in job.to_dict(include_report=False).items() if k != "report_markdown"}
            for job in jobs
        ]
    }


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, request: Request) -> dict[str, Any]:
    _validate_task_id(job_id)
    store = get_research_store()
    user = _user_id(request)
    job = await store.get(job_id, user)
    if job is None:
        raise HTTPException(404, "Job not found")
    return job.to_dict(include_report=False)


@router.get("/jobs/{job_id}/report")
async def get_report(job_id: str, request: Request) -> dict[str, str]:
    _validate_task_id(job_id)
    store = get_research_store()
    user = _user_id(request)
    job = await store.get(job_id, user)
    if job is None:
        raise HTTPException(404, "Job not found")
    if not job.report_markdown:
        raise HTTPException(404, "Report not ready")
    return {"report_markdown": job.report_markdown}


@router.get("/jobs/{job_id}/export")
async def export_job_get(
    job_id: str,
    request: Request,
    format: ResearchExportFormat = Query("pdf"),
    include_cover: bool = Query(True),
    prepared_by: str | None = Query(None),
    classification: str = Query(""),
) -> Response:
    job = await _load_job_for_export(job_id, request)
    try:
        result = export_research_job(
            job,
            format=format,
            include_cover=include_cover,
            prepared_by=prepared_by,
            classification=classification,
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return _export_response(job_id, result)


@router.post("/jobs/{job_id}/export")
async def export_job_post(job_id: str, body: ResearchExportBody, request: Request) -> Response:
    job = await _load_job_for_export(job_id, request)
    try:
        result = export_research_job(
            job,
            format=body.format,
            include_cover=body.include_cover,
            prepared_by=body.prepared_by,
            classification=body.classification,
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return _export_response(job_id, result)


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, request: Request) -> dict[str, bool]:
    _validate_task_id(job_id)
    store = get_research_store()
    user = _user_id(request)
    deleted = await store.delete(job_id, user)
    if not deleted:
        raise HTTPException(404, "Job not found")
    return {"deleted": True}


@router.post("/tasks")
async def start_task(body: ResearchStartBody, request: Request) -> dict[str, str]:
    return await start_research(body, request)


@router.get("/tasks")
async def list_tasks(request: Request) -> dict[str, Any]:
    return await list_jobs(request)


@router.get("/tasks/{job_id}")
async def get_task(job_id: str, request: Request) -> dict[str, Any]:
    _validate_task_id(job_id)
    return await get_job(job_id, request)


@router.post("/tasks/{job_id}/cancel")
async def cancel_task(job_id: str, request: Request) -> dict[str, Any]:
    _validate_task_id(job_id)
    store = get_research_store()
    user = _user_id(request)
    from keprix.research.registry import get_research_registry

    cancelled = get_research_registry().cancel(job_id, user)
    if not cancelled:
        raise HTTPException(404, "Job not found")
    job = await store.get(job_id, user)
    if job:
        job._cancelled = True
        job.status = "cancelled"
        await store.persist(job)
    return {"cancelled": True, "job_id": job_id}


@router.get("/tasks/{job_id}/events")
async def task_events(job_id: str, request: Request, since_id: int = 0) -> dict[str, Any]:
    _validate_task_id(job_id)
    store = get_research_store()
    user = _user_id(request)
    job = await store.get(job_id, user)
    if job is None:
        raise HTTPException(404, "Job not found")
    from keprix.research.registry import get_research_registry

    events = get_research_registry().list_events(job_id, since_id=since_id)
    return {"events": events}


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str, request: Request) -> StreamingResponse:
    _validate_task_id(job_id)
    store = get_research_store()
    user = _user_id(request)
    job = await store.get(job_id, user)
    if job is None:
        raise HTTPException(404, "Job not found")

    async def generate():
        async for event in store.stream_events(job):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


search_router = APIRouter(prefix="/api/search", tags=["search"])


@search_router.post("")
async def single_search(body: SearchBody) -> dict[str, Any]:
    try:
        results = await web_search(body.query, limit=8)
    except ValidationError as exc:
        raise HTTPException(400, str(exc)) from exc
    except ResearchConfigError as exc:
        raise HTTPException(503, str(exc)) from exc
    except ResearchPipelineError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"query": body.query, "results": results}
