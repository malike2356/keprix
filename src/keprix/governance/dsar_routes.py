"""Operator governance DSAR routes backed by real privacy export/erase."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import require_admin
from keprix.privacy.dsar import get_dsar_store
from keprix.privacy.erasure import erase_user_data

router = APIRouter(prefix="/api/governance/dsar", tags=["governance-dsar"])


class DsarBody(BaseModel):
    subject_user_id: str = Field(min_length=1)
    notes: str = ""
    fulfill_now: bool = True


class DeleteBody(BaseModel):
    subject_user_id: str = Field(min_length=1)
    notes: str = ""
    confirm: bool = False
    dry_run: bool = False


@router.get("/requests")
async def list_dsar(admin: dict = Depends(require_admin)) -> dict[str, Any]:
    store = get_dsar_store()
    # Privacy store is per-request rows; expose all via raw list.
    rows = list(getattr(store, "_requests", []) or [])
    return {"requests": rows, "count": len(rows)}


@router.post("/export")
async def request_export(body: DsarBody, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    actor = str(admin.get("id") or admin.get("username") or "admin")
    store = get_dsar_store()
    row = store.create(user_id=body.subject_user_id, request_type="access")
    row["notes"] = body.notes
    row["requested_by"] = actor
    if body.fulfill_now:
        row = await store.fulfill(row["id"])
    try:
        from keprix.governance.audit_store import get_audit_event_store
        from datetime import datetime, timezone

        get_audit_event_store().append(
            "governance",
            {
                "event_type": "dsar.export",
                "actor_user_id": actor,
                "payload": {
                    "request_id": row["id"],
                    "subject_user_id": body.subject_user_id,
                    "status": row.get("status"),
                    "export_path": row.get("export_path"),
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception:
        pass
    return {"request": row}


@router.post("/delete")
async def request_delete(body: DeleteBody, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    if not body.confirm and not body.dry_run:
        raise HTTPException(status_code=400, detail="confirm=true required (or dry_run=true)")
    actor = str(admin.get("id") or admin.get("username") or "admin")
    store = get_dsar_store()
    row = store.create(user_id=body.subject_user_id, request_type="erasure")
    row["notes"] = body.notes
    row["requested_by"] = actor
    erasure = await erase_user_data(
        body.subject_user_id,
        scope="full",
        dry_run=body.dry_run,
    )
    row["status"] = "completed" if not body.dry_run else "dry_run"
    row["erasure"] = erasure
    try:
        store._save()  # noqa: SLF001 - persist metadata on existing store
    except Exception:
        pass
    try:
        from keprix.governance.audit_store import get_audit_event_store
        from datetime import datetime, timezone

        get_audit_event_store().append(
            "governance",
            {
                "event_type": "dsar.delete",
                "actor_user_id": actor,
                "payload": {
                    "request_id": row["id"],
                    "subject_user_id": body.subject_user_id,
                    "dry_run": body.dry_run,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception:
        pass
    return {"request": row, "erasure": erasure}
