"""Job queue HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user, require_admin
from keprix.jobs.queue import get_job_queue

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class CreateJobBody(BaseModel):
    job_type: str
    payload: dict[str, Any] | None = None


class ClaimBody(BaseModel):
    worker_id: str = Field(..., min_length=1)


class TokenBody(BaseModel):
    claim_token: str = Field(..., min_length=8)


class FailBody(TokenBody):
    reason: str = "failed"


class CompleteBody(TokenBody):
    result: dict[str, Any] | None = None


@router.post("")
async def create_job(body: CreateJobBody, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    try:
        job = get_job_queue().enqueue(body.job_type, body.payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job": job}


@router.get("")
async def list_jobs(status: str | None = None, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"items": get_job_queue().list_jobs(status=status)}


@router.post("/{job_id}/claim")
async def claim_job(job_id: str, body: ClaimBody, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    get_job_queue().reclaim_stale()
    job = get_job_queue().claim_job(job_id, worker_id=body.worker_id)
    if job is None:
        existing = get_job_queue().get(job_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Job not found")
        raise HTTPException(status_code=409, detail="Job is not claimable")
    return {"job": job}


@router.post("/{job_id}/heartbeat")
async def heartbeat_job(job_id: str, body: TokenBody, _admin: dict = Depends(require_admin)) -> dict[str, bool]:
    ok = get_job_queue().heartbeat(job_id, body.claim_token)
    if not ok:
        raise HTTPException(status_code=409, detail="Heartbeat rejected")
    return {"ok": True}


@router.post("/{job_id}/complete")
async def complete_job(job_id: str, body: CompleteBody, _admin: dict = Depends(require_admin)) -> dict[str, bool]:
    ok = get_job_queue().complete(job_id, body.claim_token, result=body.result)
    if not ok:
        raise HTTPException(status_code=409, detail="Complete rejected")
    return {"ok": True}


@router.post("/{job_id}/fail")
async def fail_job(job_id: str, body: FailBody, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    job = get_job_queue().fail(job_id, body.claim_token, reason=body.reason)
    if job is None:
        raise HTTPException(status_code=409, detail="Fail rejected")
    return {"job": job}
