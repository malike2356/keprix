"""Cron job HTTP routes for the community API server."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import require_admin

router = APIRouter(prefix="/api/cron", tags=["cron"])


class CronJobCreateBody(BaseModel):
    name: str = ""
    schedule: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1)
    deliver: str = "local"


def _cron_jobs_module():
    """Import cron.jobs with the legacy src/keprix package root on sys.path."""
    root = Path(__file__).resolve().parents[1]
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    from cron import jobs as cron_jobs
    from keprix_constants import get_keprix_home

    home = get_keprix_home().resolve()
    cron_jobs.KEPRIX_DIR = home
    cron_jobs.CRON_DIR = home / "cron"
    cron_jobs.JOBS_FILE = cron_jobs.CRON_DIR / "jobs.json"
    cron_jobs.OUTPUT_DIR = cron_jobs.CRON_DIR / "output"
    return cron_jobs


def _public_job(job: dict[str, Any]) -> dict[str, Any]:
    schedule = str(job.get("schedule_display") or "")
    if not schedule:
        raw = job.get("schedule")
        if isinstance(raw, dict):
            schedule = str(raw.get("display") or raw.get("value") or raw.get("expr") or "")
        elif raw is not None:
            schedule = str(raw)
    source = None
    source_href = None
    try:
        from keprix.agent_apps.automation import cron_job_source

        source_info = cron_job_source(job)
        if source_info:
            source = source_info["label"]
            source_href = source_info["href"]
    except Exception:
        pass
    return {
        "id": job.get("id"),
        "name": job.get("name") or job.get("id"),
        "schedule": schedule or "?",
        "prompt": job.get("prompt") or "",
        "enabled": job.get("enabled", True),
        "deliver": job.get("deliver"),
        "next_run_at": job.get("next_run_at"),
        "last_run_at": job.get("last_run_at"),
        "state": job.get("state"),
        "source": source,
        "source_href": source_href,
    }


def _list_runs(job_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    cron_jobs = _cron_jobs_module()
    job = cron_jobs.get_job(job_id)
    if job is None:
        return []
    output_dir = cron_jobs.OUTPUT_DIR / str(job_id)
    if not output_dir.is_dir():
        return []
    files = sorted(output_dir.glob("*.md"), key=lambda path: path.stat().st_mtime, reverse=True)
    runs: list[dict[str, Any]] = []
    for path in files[:limit]:
        mtime = path.stat().st_mtime
        runs.append(
            {
                "id": path.stem,
                "started_at": int(mtime),
                "ended_at": int(mtime),
                "is_active": False,
            }
        )
    return runs


@router.get("/jobs")
async def list_cron_jobs(_admin: dict = Depends(require_admin)) -> list[dict[str, Any]]:
    cron_jobs = _cron_jobs_module()
    return [_public_job(job) for job in cron_jobs.list_jobs(include_disabled=True)]


@router.get("/jobs/{job_id}")
async def get_cron_job(job_id: str, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    cron_jobs = _cron_jobs_module()
    job = cron_jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _public_job(job)


@router.get("/jobs/{job_id}/runs")
async def list_cron_job_runs(
    job_id: str,
    limit: int = 20,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    cron_jobs = _cron_jobs_module()
    if cron_jobs.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    limit_n = max(1, min(int(limit), 100))
    return {"runs": _list_runs(job_id, limit=limit_n), "limit": limit_n}


@router.post("/jobs")
async def create_cron_job(
    body: CronJobCreateBody,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    cron_jobs = _cron_jobs_module()
    try:
        job = cron_jobs.create_job(
            prompt=body.prompt,
            schedule=body.schedule,
            name=body.name,
            deliver=body.deliver or "local",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _public_job(job)


@router.post("/jobs/{job_id}/pause")
async def pause_cron_job(job_id: str, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    cron_jobs = _cron_jobs_module()
    job = cron_jobs.pause_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _public_job(job)


@router.post("/jobs/{job_id}/resume")
async def resume_cron_job(job_id: str, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    cron_jobs = _cron_jobs_module()
    job = cron_jobs.resume_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _public_job(job)


@router.post("/jobs/{job_id}/trigger")
async def trigger_cron_job(job_id: str, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    cron_jobs = _cron_jobs_module()
    job = cron_jobs.trigger_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _public_job(job)


@router.delete("/jobs/{job_id}")
async def delete_cron_job(job_id: str, _admin: dict = Depends(require_admin)) -> dict[str, bool]:
    cron_jobs = _cron_jobs_module()
    try:
        removed = cron_jobs.remove_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not removed:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True}
