"""UI-facing worker knowledge base under /api/worker-kb (session auth)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from keprix.api.auth import require_api_auth
from keprix.worker_kb.service import get_worker_kb_service

router = APIRouter(prefix="/api/worker-kb", tags=["worker-kb-ui"])


def _workspace(workspace_id: str | None, x_workspace_id: str | None) -> str:
    return (workspace_id or x_workspace_id or "default").strip() or "default"


@router.get("/entries")
async def list_entries(
    worker_id: str = Query(...),
    workspace_id: str | None = Query(default=None),
    enabled_only: bool = Query(False),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    wid = worker_id.strip()
    if not wid:
        raise HTTPException(status_code=422, detail="worker_id is required")
    return get_worker_kb_service().list_entries(ws, wid, enabled_only=enabled_only)


@router.post("/entries")
async def add_entry(
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id)
    worker_id = str(body.get("worker_id") or "").strip()
    content = str(body.get("content") or "").strip()
    if not worker_id or not content:
        raise HTTPException(status_code=422, detail="worker_id and content are required")
    try:
        return await get_worker_kb_service().add_entry(
            ws,
            worker_id,
            content=content,
            entry_type=str(body.get("entry_type") or "faq"),
            title=body.get("title"),
            source=body.get("source") or "manual",
            source_file=body.get("source_file"),
            kb_name=str(body.get("kb_name") or "Default"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/search")
async def search_entries(
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id)
    worker_id = str(body.get("worker_id") or "").strip()
    query = str(body.get("query") or "").strip()
    if not worker_id or not query:
        raise HTTPException(status_code=422, detail="worker_id and query are required")
    return await get_worker_kb_service().search(
        ws,
        worker_id,
        query,
        limit=int(body.get("limit") or 5),
        hybrid=bool(body.get("hybrid", True)),
    )


@router.post("/entries/{entry_id}/toggle")
async def toggle_entry(
    entry_id: str,
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id)
    worker_id = str(body.get("worker_id") or "").strip()
    if not worker_id:
        raise HTTPException(status_code=422, detail="worker_id is required")
    try:
        return await get_worker_kb_service().toggle_entry(
            ws,
            worker_id,
            entry_id,
            enabled=body.get("enabled"),
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.delete("/entries/{entry_id}")
async def delete_entry(
    entry_id: str,
    worker_id: str = Query(...),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    try:
        return await get_worker_kb_service().delete_entry(ws, worker_id.strip(), entry_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
