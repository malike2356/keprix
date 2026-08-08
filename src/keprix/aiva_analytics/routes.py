"""HTTP routes for Aiva analytics under /carina/analytics (K04)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query

from keprix.aiva_analytics.service import get_analytics_service

router = APIRouter(prefix="/analytics", tags=["aiva-analytics"])


def _workspace(x_workspace_id: str | None) -> str:
    ws = (x_workspace_id or "").strip()
    if not ws:
        raise HTTPException(status_code=400, detail="X-Workspace-Id header required")
    return ws


@router.get("/overview")
async def analytics_overview(
    days: int = Query(30, ge=1, le=365),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
) -> dict[str, Any]:
    return get_analytics_service().overview(_workspace(x_workspace_id), days=days)


@router.get("/outreach")
async def analytics_outreach(
    campaign_id: str | None = Query(default=None),
    days: int = Query(30, ge=1, le=365),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
) -> dict[str, Any]:
    return get_analytics_service().outreach(_workspace(x_workspace_id), campaign_id=campaign_id, days=days)


@router.get("/worker")
async def analytics_worker(
    worker_id: str | None = Query(default=None),
    days: int = Query(30, ge=1, le=365),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
) -> dict[str, Any]:
    return get_analytics_service().worker(_workspace(x_workspace_id), worker_id=worker_id, days=days)


@router.get("/usage")
async def analytics_usage(
    days: int = Query(30, ge=1, le=365),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
) -> dict[str, Any]:
    return get_analytics_service().usage(_workspace(x_workspace_id), days=days)
