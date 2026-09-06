"""Scoped Document Vault export routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.document_vault.channel.scoped_export import destination_status, export_scoped

router = APIRouter(prefix="/api/workspace/export", tags=["workspace-export"])


class WorkspaceExportBody(BaseModel):
    workspace_id: str | None = None
    kinds: str = Field(default="all", pattern="^(documents|notes|research|all)$")
    destination: str = "local"


def _workspace(body: WorkspaceExportBody, user: dict[str, Any]) -> str:
    current = str(user.get("workspace_id") or "default")
    requested = body.workspace_id or current
    role = str(user.get("role") or "").lower()
    if requested != current and role not in {"admin", "owner", "developer"}:
        raise HTTPException(status_code=403, detail="workspace access denied")
    return requested


@router.get("/settings")
async def export_settings(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return {"destinations": destination_status()}


@router.put("/settings")
async def update_export_settings(
    body: dict[str, Any], user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    _ = user
    # Credentials remain server-side environment configuration. This endpoint is a
    # read-back contract and deliberately does not accept or persist access tokens.
    return {"ok": True, "destinations": destination_status(), "ignored": sorted(body)}


@router.post("", response_model=None)
async def workspace_export(
    body: WorkspaceExportBody, user: dict[str, Any] = Depends(get_current_user)
) -> Response | dict[str, Any]:
    workspace_id = _workspace(body, user)
    try:
        result = export_scoped(workspace_id, body.kinds, body.destination)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if body.destination == "local" and result.get("ok"):
        data = result.pop("bytes")
        return Response(
            content=data,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={result['filename']}"},
        )
    return result
