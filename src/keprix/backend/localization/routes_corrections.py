"""API routes for localization corrections and flywheel (Prompt 50)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user, require_admin
from keprix.backend.localization.corrections import CORRECTION_TYPES, get_correction_queue
from keprix.backend.localization.flywheel import get_flywheel, get_quality_metrics

router = APIRouter(prefix="/api/localization", tags=["localization-corrections"])


def _user_id(user: dict[str, Any]) -> str:
    return str(user.get("id") or user.get("username") or "default")


class CorrectionSubmitBody(BaseModel):
    audit_record_id: str
    correction_type: str
    original_value: str
    corrected_value: str
    source_language: str
    target_language: str | None = None
    domain: str = "generic"
    workspace_id: str = "default"


class OperatorCorrectionBody(CorrectionSubmitBody):
    auto_approve: bool = True


class ApproveBody(BaseModel):
    quality_score: int = Field(default=3, ge=1, le=5)
    corrected_value: str | None = None


class RejectBody(BaseModel):
    reason: str = Field(..., min_length=1)


class BatchApproveBody(BaseModel):
    correction_ids: list[str] = Field(..., min_length=1)
    quality_score: int = Field(default=3, ge=1, le=5)


class ExportBody(BaseModel):
    output_path: str
    workspace_id: str = "default"
    domain: str | None = None
    task_type: str | None = None
    min_quality_score: int = Field(default=3, ge=1, le=5)
    since: str | None = None


@router.get("/corrections")
async def list_corrections(
    workspace_id: str = "default",
    status: str | None = None,
    correction_type: str | None = None,
    source_language: str | None = None,
    domain: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    rows = await get_correction_queue().list_corrections(
        workspace_id,
        status=status,
        correction_type=correction_type,
        source_language=source_language,
        domain=domain,
        limit=limit,
        offset=offset,
    )
    return {"corrections": rows, "count": len(rows)}


@router.post("/corrections")
async def submit_correction(
    body: CorrectionSubmitBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    if body.correction_type not in CORRECTION_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported correction_type")
    record = await get_correction_queue().submit_user_correction(
        audit_record_id=body.audit_record_id,
        correction_type=body.correction_type,
        original_value=body.original_value,
        corrected_value=body.corrected_value,
        workspace_id=body.workspace_id,
        source_language=body.source_language,
        target_language=body.target_language,
        domain=body.domain,
    )
    return {"correction": record.__dict__}


@router.post("/corrections/operator")
async def submit_operator_correction(
    body: OperatorCorrectionBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    if body.correction_type not in CORRECTION_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported correction_type")
    record = await get_correction_queue().submit_operator_correction(
        audit_record_id=body.audit_record_id,
        correction_type=body.correction_type,
        original_value=body.original_value,
        corrected_value=body.corrected_value,
        workspace_id=body.workspace_id,
        operator_user_id=_user_id(user),
        source_language=body.source_language,
        target_language=body.target_language,
        domain=body.domain,
        auto_approve=body.auto_approve,
    )
    return {"correction": record.__dict__}


@router.get("/corrections/{correction_id}")
async def get_correction(
    correction_id: str,
    workspace_id: str = "default",
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    record = await get_correction_queue().get(correction_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Correction not found")
    from keprix.backend.localization.audit import get_audit_service

    audit_record = await get_audit_service().get_record(workspace_id, record.audit_record_id)
    return {"correction": record.__dict__, "audit_record": audit_record}


@router.post("/corrections/{correction_id}/approve")
async def approve_correction(
    correction_id: str,
    body: ApproveBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    record = await get_correction_queue().approve_correction(
        correction_id,
        _user_id(user),
        quality_score=body.quality_score,
        corrected_value=body.corrected_value,
    )
    return {"correction": record.__dict__}


@router.post("/corrections/{correction_id}/reject")
async def reject_correction(
    correction_id: str,
    body: RejectBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    if not body.reason.strip():
        raise HTTPException(status_code=422, detail="Rejection reason is required")
    record = await get_correction_queue().reject_correction(
        correction_id,
        _user_id(user),
        reason=body.reason.strip(),
    )
    return {"correction": record.__dict__}


@router.post("/corrections/batch/approve")
async def batch_approve_corrections(
    body: BatchApproveBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    records = await get_correction_queue().batch_approve(
        body.correction_ids,
        _user_id(user),
        quality_score=body.quality_score,
    )
    return {"corrections": [record.__dict__ for record in records]}


@router.get("/metrics")
async def localization_metrics(
    workspace_id: str = "default",
    language_code: str | None = None,
    since: str | None = None,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    since_dt = datetime.fromisoformat(since.replace("Z", "+00:00")) if since else None
    metrics = get_quality_metrics()
    return {
        "correction_rate": await metrics.get_correction_rate(
            workspace_id,
            language_code=language_code,
            since=since_dt,
        ),
        "coverage": await metrics.get_coverage_summary(workspace_id),
        "provider_accuracy": await metrics.get_provider_accuracy_by_language(workspace_id),
    }


@router.get("/metrics/top-errors")
async def top_corrected_terms(
    domain: str,
    language_code: str,
    workspace_id: str = "default",
    limit: int = Query(default=20, ge=1, le=100),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    terms = await get_quality_metrics().get_most_corrected_terms(
        workspace_id=workspace_id,
        domain=domain,
        language_code=language_code,
        limit=limit,
    )
    return {"terms": terms}


@router.post("/flywheel/export")
async def export_flywheel_data(
    body: ExportBody,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    since_dt = datetime.fromisoformat(body.since.replace("Z", "+00:00")) if body.since else None
    output_dir = Path(body.output_path)
    flywheel = get_flywheel()
    sm4t = await flywheel.export_sm4t_training_data(
        output_dir,
        workspace_id=body.workspace_id,
        domain=body.domain,
        task_type=body.task_type,
        min_quality_score=body.min_quality_score,
        since=since_dt,
    )
    llm = await flywheel.export_llm_correction_data(
        output_dir,
        workspace_id=body.workspace_id,
        domain=body.domain,
        since=since_dt,
    )
    return {"sm4t": sm4t.__dict__, "llm": llm, "output_path": str(output_dir)}
