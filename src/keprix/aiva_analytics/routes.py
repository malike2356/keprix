"""HTTP routes for Aiva analytics under /carina/analytics (K04)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from keprix.auth.dependencies import require_admin
from keprix.aiva_analytics import metrics as metric_names
from keprix.aiva_analytics.service import get_analytics_service
from keprix.aiva_analytics.store import get_analytics_store

router = APIRouter(prefix="/analytics", tags=["aiva-analytics"])


def _worker_index(
    *, workspace_filter: str | None = None, status_filter: str | None = None, channel_filter: str | None = None
) -> list[dict[str, object]]:
    store = get_analytics_store()
    workspaces = [workspace_filter] if workspace_filter else store.list_workspaces_with_events()
    now = datetime.now(timezone.utc)
    indexed: dict[tuple[str, str], dict[str, object]] = {}
    for workspace_id in workspaces:
        if not workspace_id:
            continue
        for event in store.query_events(workspace_id, limit=50000):
            labels = event.get("labels") or {}
            worker_id = str(labels.get("worker_id") or "").strip()
            if not worker_id:
                continue
            key = (workspace_id, worker_id)
            item = indexed.setdefault(key, {"workspace_id": workspace_id, "worker_id": worker_id, "channels": set(), "tokens": 0.0, "cost_usd": 0.0, "messages": 0.0, "last_activity": None})
            channel = str(labels.get("channel") or "").strip()
            if channel:
                item["channels"].add(channel)  # type: ignore[union-attr]
            if event.get("metric_name") == metric_names.AIVA_AGENT_TOKENS:
                item["tokens"] = float(item["tokens"]) + float(event.get("metric_value") or 0)
            elif event.get("metric_name") == metric_names.AIVA_AGENT_COST_USD:
                item["cost_usd"] = float(item["cost_usd"]) + float(event.get("metric_value") or 0)
            elif event.get("metric_name") == metric_names.AIVA_WORKER_MESSAGES:
                item["messages"] = float(item["messages"]) + float(event.get("metric_value") or 0)
            recorded = str(event.get("recorded_at") or "")
            if recorded and (item["last_activity"] is None or recorded > str(item["last_activity"])):
                item["last_activity"] = recorded
    output = []
    for item in indexed.values():
        channels = sorted(item["channels"])  # type: ignore[arg-type]
        status = "active" if item["last_activity"] and (now - datetime.fromisoformat(str(item["last_activity"]).replace("Z", "+00:00"))).total_seconds() < 900 else "idle"
        if status_filter and status != status_filter:
            continue
        if channel_filter and channel_filter not in channels:
            continue
        output.append({**item, "channels": channels, "status": status})
    return sorted(output, key=lambda row: (str(row["workspace_id"]), str(row["worker_id"])))


@router.get("/api/admin/aivas")
async def all_aivas(
    workspace: str | None = Query(default=None),
    status: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    _admin: dict = Depends(require_admin),
) -> dict[str, object]:
    items = _worker_index(workspace_filter=workspace, status_filter=status, channel_filter=channel)
    return {"items": items, "count": len(items), "filters": {"workspace": workspace, "status": status, "channel": channel}}


@router.get("/api/admin/workspaces/{workspace_id}/workers")
async def workspace_workers(workspace_id: str, _admin: dict = Depends(require_admin)) -> dict[str, object]:
    items = _worker_index(workspace_filter=workspace_id)
    return {"workspace_id": workspace_id, "items": items, "count": len(items)}


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
