"""Dashboard list endpoints for admin overview."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from keprix.agent.keprix.store import get_generated_tool_store
from keprix.auth.dependencies import get_current_user, require_admin
from keprix.workspace.repository import workspace_repo

router = APIRouter(tags=["dashboard"])


@router.get("/api/mutations/{record_id}/code")
async def get_mutation_code(record_id: str, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    store = get_generated_tool_store()
    record = store.get(record_id)
    if record is not None:
        code = record.tool_code or ""
        return {"id": record_id, "source_code": code, "code": code, "name": record.tool_name}

    from keprix.mutation.store import get_mutation_store

    mutation = get_mutation_store().get_generated_tool(record_id)
    if mutation is None:
        raise HTTPException(status_code=404, detail="Mutation not found")
    code = mutation.source_code or ""
    return {"id": record_id, "source_code": code, "code": code, "name": mutation.name}


@router.get("/api/mutations")
async def list_mutations(
    _admin: dict = Depends(require_admin),
    limit: int = Query(5, ge=1, le=50),
    sort: str = Query("created_at:desc"),
) -> dict[str, Any]:
    records = get_generated_tool_store().list_all()
    reverse = sort.endswith(":desc")
    records.sort(key=lambda row: row.created_at or "", reverse=reverse)
    items = [
        {
            "id": record.id,
            "tool_name": record.tool_name,
            "status": record.status,
            "requested_by": record.approver_id or "mutation_engine",
            "requested_at": record.created_at,
            "task_that_triggered": record.task_that_triggered,
        }
        for record in records[:limit]
    ]
    return {"items": items}


@router.get("/api/channels/status")
async def channels_status(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    from keprix.config.health_monitor import ConfigHealthMonitor

    monitor = ConfigHealthMonitor()
    await monitor._run_all_checks()
    channels: list[dict[str, Any]] = []
    for name, health in monitor.get_all().items():
        if not name.startswith("channel:"):
            continue
        channel_name = name.removeprefix("channel:")
        status = "connected" if health.status == "healthy" else "degraded" if health.status == "warning" else "error"
        channels.append(
            {
                "id": channel_name,
                "name": channel_name.replace("_", " ").title(),
                "status": status,
                "last_message_at": None,
                "configure_href": "/dashboard/channels",
            }
        )
    if not channels:
        channels = [
            {
                "id": "local",
                "name": "Web UI",
                "status": "connected",
                "last_message_at": None,
                "configure_href": "/dashboard/channels",
            }
        ]
    return {"channels": channels}
