"""Brain health API routes."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.brain.health import BrainHealthService

router = APIRouter(prefix="/api/brain/health", tags=["brain-health"])

_CACHE_TTL_SECONDS = 300
_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _workspace_id(workspace_id: str | None, user: dict[str, Any]) -> str:
    requested = workspace_id or str(user.get("workspace_id") or "default")
    allowed = user.get("workspace_id")
    if allowed and requested != allowed and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="workspace access denied")
    return requested


def _invalidate_cache(workspace_id: str) -> None:
    keys = [key for key in _cache if key.startswith(f"{workspace_id}:")]
    for key in keys:
        _cache.pop(key, None)


class DeleteOrphansBody(BaseModel):
    confirm: bool = False


class MergeDuplicatesBody(BaseModel):
    keep_id: str = Field(min_length=1)
    delete_id: str = Field(min_length=1)


class ArchiveStaleBody(BaseModel):
    node_ids: list[str] = Field(default_factory=list)
    node_kind: str = "memory"
    confirm: bool = False


@router.get("")
async def brain_health(
    workspace_id: str | None = None,
    refresh: bool = Query(default=False),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    resolved = _workspace_id(workspace_id, user)
    cache_key = f"{resolved}:report"
    now = time.time()
    if not refresh:
        cached = _cache.get(cache_key)
        if cached and now - cached[0] < _CACHE_TTL_SECONDS:
            return cached[1]
    report = await BrainHealthService().build_report(resolved)
    payload = report.to_dict()
    _cache[cache_key] = (now, payload)
    return payload


@router.post("/delete-orphans")
async def delete_orphans(
    body: DeleteOrphansBody,
    workspace_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, int]:
    if not body.confirm:
        raise HTTPException(status_code=400, detail="confirm=true is required")
    resolved = _workspace_id(workspace_id, user)
    deleted = await BrainHealthService().delete_orphans(resolved)
    _invalidate_cache(resolved)
    return {"deleted": deleted}


@router.post("/merge-duplicates")
async def merge_duplicates(
    body: MergeDuplicatesBody,
    workspace_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, int]:
    if body.keep_id == body.delete_id:
        raise HTTPException(status_code=400, detail="keep_id and delete_id must differ")
    resolved = _workspace_id(workspace_id, user)
    result = await BrainHealthService().merge_duplicates(
        resolved,
        keep_id=body.keep_id,
        delete_id=body.delete_id,
    )
    _invalidate_cache(resolved)
    return result


@router.post("/archive-stale")
async def archive_stale(
    body: ArchiveStaleBody,
    workspace_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, int]:
    if not body.confirm:
        raise HTTPException(status_code=400, detail="confirm=true is required")
    if not body.node_ids:
        raise HTTPException(status_code=400, detail="node_ids is required")
    resolved = _workspace_id(workspace_id, user)
    archived = await BrainHealthService().archive_stale(
        resolved,
        [(body.node_kind, node_id) for node_id in body.node_ids],
    )
    _invalidate_cache(resolved)
    return {"archived": archived}
