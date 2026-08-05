"""Backup and restore HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from keprix.auth.dependencies import require_admin
from keprix.security.audit import audit_log
from keprix.workspace.backup_service import backup_service

router = APIRouter(prefix="/api/admin/backup", tags=["backup"])


class CreateBackupRequest(BaseModel):
    password: str | None = None


@router.post("/create")
async def create_backup(body: CreateBackupRequest, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    meta = backup_service.create_backup(password=body.password)
    await audit_log("backup_create", user_id=admin.get("id"), event_data={"backup_id": meta["id"]})
    return meta


@router.get("/list")
async def list_backups(admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return {"backups": backup_service.list_backups()}


@router.get("/{backup_id}/download")
async def download_backup(backup_id: str, admin: dict = Depends(require_admin)) -> FileResponse:
    path = backup_service.get_backup_path(backup_id)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="Backup not found")
    return FileResponse(path, filename=path.name, media_type="application/gzip")


@router.post("/restore")
async def restore_backup(
    confirm: bool = Form(...),
    password: str | None = Form(None),
    file: UploadFile = File(...),
    admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    if not confirm:
        raise HTTPException(status_code=422, detail="confirm must be true")
    archive_bytes = await file.read()
    try:
        result = backup_service.restore_backup(archive_bytes, password=password)
    except ValueError as exc:
        try:
            from keprix.readiness.restore_evidence import get_restore_evidence_store

            get_restore_evidence_store().record(
                ok=False,
                restored_files=0,
                encrypted=bool(password),
                note=str(exc),
            )
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        from keprix.readiness.restore_evidence import get_restore_evidence_store

        get_restore_evidence_store().record(
            ok=bool(result.get("ok", True)),
            restored_files=int(result.get("restored_files") or 0),
            encrypted=bool(password),
            note="admin_restore",
            detail={"restored_at": result.get("restored_at")},
        )
    except Exception:
        pass
    await audit_log("backup_restore", user_id=admin.get("id"))
    return result


@router.delete("/{backup_id}")
async def delete_backup(backup_id: str, admin: dict = Depends(require_admin)) -> dict[str, bool]:
    if not backup_service.delete_backup(backup_id):
        raise HTTPException(status_code=404, detail="Backup not found")
    await audit_log("backup_delete", user_id=admin.get("id"), event_data={"backup_id": backup_id})
    return {"ok": True}
