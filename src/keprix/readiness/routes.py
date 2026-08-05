"""Admin API for market / upgrade / recovery readiness."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from keprix.auth.dependencies import require_admin
from keprix.readiness.backup_ops import create_backup_safe
from keprix.readiness.restore_evidence import get_restore_evidence_store
from keprix.readiness.service import build_report

router = APIRouter(prefix="/api/admin/readiness", tags=["readiness"])


class RestoreEvidenceBody(BaseModel):
    ok: bool = True
    backup_id: str | None = None
    restored_files: int = 0
    encrypted: bool = False
    note: str | None = None


class BackupCreateBody(BaseModel):
    password: str | None = None
    timeout_sec: float | None = Field(default=None, ge=5, le=3600)


@router.get("")
async def get_readiness(
    target_version: str | None = Query(default=None),
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    report = build_report(target_version=target_version)
    return report.to_dict()


@router.get("/checks/{check_id}")
async def get_check(check_id: str, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    report = build_report()
    for check in report.checks:
        if check.id == check_id:
            return {"check": check.to_dict()}
    from fastapi import HTTPException

    raise HTTPException(status_code=404, detail="Check not found")


@router.post("/backup")
async def readiness_backup(body: BackupCreateBody, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    """Create a backup with timeout; returns failure_reason instead of hanging."""
    return create_backup_safe(password=body.password, timeout_sec=body.timeout_sec)


@router.get("/restore-evidence")
async def list_restore_evidence(
    limit: int = Query(default=20, ge=1, le=100),
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    return {"evidence": get_restore_evidence_store().list(limit=limit)}


@router.post("/restore-evidence")
async def record_restore_evidence(
    body: RestoreEvidenceBody,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    row = get_restore_evidence_store().record(
        ok=body.ok,
        backup_id=body.backup_id,
        restored_files=body.restored_files,
        encrypted=body.encrypted,
        note=body.note,
    )
    return {"evidence": row}
