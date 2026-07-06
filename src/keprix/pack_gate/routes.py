"""Pack gate HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from keprix.auth.dependencies import require_admin
from keprix.pack_gate.deps import get_pack_gate_actor, resolve_workspace_id
from keprix.pack_gate.gate import sign_off_url
from keprix.pack_gate.schemas import (
    PackGateConfigOut,
    PackGateConfigUpdate,
    PackGateRecordOut,
    PackGateRecordsPage,
    RejectBody,
    RollbackBody,
    SignOffBody,
)
from keprix.pack_gate.service import approve_record, reject_record, rollback_pack_version, save_gate_config
from keprix.pack_gate.store import get_pack_gate_store

router = APIRouter(prefix="/api/pack-gate", tags=["pack-gate"])


def _record_out(row: dict[str, Any]) -> PackGateRecordOut:
    pack_id = str(row["pack_id"])
    record_id = str(row["id"])
    return PackGateRecordOut(
        id=record_id,
        workspace_id=str(row["workspace_id"]),
        pack_id=pack_id,
        from_version=row.get("from_version"),
        to_version=str(row["to_version"]),
        changelog_text=row.get("changelog_text"),
        status=str(row["status"]),
        signed_off_by_user_id=row.get("signed_off_by_user_id"),
        signed_off_at=row.get("signed_off_at"),
        sign_off_note=row.get("sign_off_note"),
        requested_at=str(row.get("requested_at") or ""),
        requested_by_user_id=row.get("requested_by_user_id"),
        sign_off_url=sign_off_url(pack_id, record_id),
    )


@router.get("/config", response_model=PackGateConfigOut)
async def get_config(request: Request, _user: dict = Depends(get_pack_gate_actor)) -> PackGateConfigOut:
    workspace_id = resolve_workspace_id(request)
    config = await get_pack_gate_store().get_config(workspace_id)
    return PackGateConfigOut(**config)


@router.put("/config", response_model=PackGateConfigOut)
async def put_config(
    body: PackGateConfigUpdate,
    request: Request,
    _admin: dict = Depends(require_admin),
) -> PackGateConfigOut:
    workspace_id = resolve_workspace_id(request)
    try:
        config = await save_gate_config(
            workspace_id,
            enabled=body.enabled,
            approver_user_id=body.approver_user_id,
            notify_on_install=body.notify_on_install,
            require_changelog=body.require_changelog,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PackGateConfigOut(**config)


@router.get("/records", response_model=PackGateRecordsPage)
async def list_records(
    request: Request,
    status: str | None = None,
    pack_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _user: dict = Depends(get_pack_gate_actor),
) -> PackGateRecordsPage:
    workspace_id = resolve_workspace_id(request)
    rows, total = await get_pack_gate_store().list_records(
        workspace_id,
        status=status,
        pack_id=pack_id,
        limit=limit,
        offset=offset,
    )
    return PackGateRecordsPage(records=[_record_out(row) for row in rows], total=total)


@router.get("/records/{record_id}", response_model=PackGateRecordOut)
async def get_record(
    record_id: str,
    request: Request,
    _user: dict = Depends(get_pack_gate_actor),
) -> PackGateRecordOut:
    workspace_id = resolve_workspace_id(request)
    row = await get_pack_gate_store().get_record(workspace_id, record_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Gate record not found")
    return _record_out(row)


@router.post("/records/{record_id}/approve", response_model=PackGateRecordOut)
async def approve_gate_record(
    record_id: str,
    body: SignOffBody,
    request: Request,
    actor: dict = Depends(get_pack_gate_actor),
) -> PackGateRecordOut:
    workspace_id = resolve_workspace_id(request)
    try:
        row = await approve_record(
            workspace_id=workspace_id,
            record_id=record_id,
            actor=actor,
            note=body.note,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _record_out(row)


@router.post("/records/{record_id}/reject", response_model=PackGateRecordOut)
async def reject_gate_record(
    record_id: str,
    body: RejectBody,
    request: Request,
    actor: dict = Depends(get_pack_gate_actor),
) -> PackGateRecordOut:
    workspace_id = resolve_workspace_id(request)
    try:
        row = await reject_record(
            workspace_id=workspace_id,
            record_id=record_id,
            actor=actor,
            note=body.note,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _record_out(row)


@router.post("/packs/{pack_id}/rollback")
async def rollback_pack_route(
    pack_id: str,
    body: RollbackBody,
    request: Request,
    actor: dict = Depends(require_admin),
) -> dict[str, Any]:
    workspace_id = resolve_workspace_id(request)
    try:
        return await rollback_pack_version(
            workspace_id=workspace_id,
            pack_id=pack_id,
            actor=actor,
            reason=body.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/packs/{pack_id}/history", response_model=PackGateRecordsPage)
async def pack_history(
    pack_id: str,
    request: Request,
    _user: dict = Depends(get_pack_gate_actor),
) -> PackGateRecordsPage:
    workspace_id = resolve_workspace_id(request)
    rows, total = await get_pack_gate_store().list_records(workspace_id, pack_id=pack_id, limit=200)
    return PackGateRecordsPage(records=[_record_out(row) for row in rows], total=total)
