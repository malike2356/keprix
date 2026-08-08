"""UI-facing Aiva analytics under /api/aiva/analytics (session auth)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, Query

from keprix.aiva_analytics.service import get_analytics_service
from keprix.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/aiva/analytics", tags=["aiva-analytics-ui"])


def _resolve_workspace(workspace_id: str | None, x_workspace_id: str | None) -> str:
    return (workspace_id or x_workspace_id or "default").strip() or "default"


@router.get("/overview")
async def overview(
    days: int = Query(30, ge=1, le=365),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    return get_analytics_service().overview(_resolve_workspace(workspace_id, x_workspace_id), days=days)


@router.get("/outreach")
async def outreach(
    campaign_id: str | None = Query(default=None),
    days: int = Query(30, ge=1, le=365),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    return get_analytics_service().outreach(
        _resolve_workspace(workspace_id, x_workspace_id),
        campaign_id=campaign_id,
        days=days,
    )


@router.get("/worker")
async def worker(
    worker_id: str | None = Query(default=None),
    days: int = Query(30, ge=1, le=365),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    return get_analytics_service().worker(
        _resolve_workspace(workspace_id, x_workspace_id),
        worker_id=worker_id,
        days=days,
    )


@router.get("/usage")
async def usage(
    days: int = Query(30, ge=1, le=365),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    return get_analytics_service().usage(_resolve_workspace(workspace_id, x_workspace_id), days=days)
