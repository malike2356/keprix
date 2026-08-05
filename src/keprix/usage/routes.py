"""REST API for LLM usage analytics (Prompt 146)."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, AsyncIterator, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user, require_admin
from keprix.usage.analytics import get_llm_usage_analytics
from keprix.usage.filters import UsageQueryFilters
from keprix.usage.pricing_bridge import list_pricing_catalog

router = APIRouter(prefix="/api/usage", tags=["usage"])


class BudgetBody(BaseModel):
    monthly_budget_usd: float | None = None
    alert_threshold_percent: int = Field(default=80, ge=1, le=100)


def _user_key(user: dict[str, Any]) -> str:
    return str(user.get("id") or user.get("username") or "unknown")


def _usage_admin(user: dict[str, Any]) -> bool:
    return str(user.get("role") or "").lower() in {"admin", "owner", "developer"}


def _resolve_filters(
    user: dict[str, Any],
    *,
    workspace_id: str = "default",
    user_id: str | None = None,
    channel: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    days: int = 30,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
    allow_user_override: bool = True,
) -> UsageQueryFilters:
    if not _usage_admin(user):
        if user_id and user_id != _user_key(user):
            raise HTTPException(status_code=403, detail="Cannot query another user's usage")
        user_id = _user_key(user)
    elif not allow_user_override:
        user_id = None
    return UsageQueryFilters.from_params(
        workspace_id=workspace_id,
        user_id=user_id,
        channel=channel,
        model=model,
        provider=provider,
        days=days,
        from_ts=from_ts,
        to_ts=to_ts,
    )


@router.get("/summary")
async def usage_summary(
    user: dict = Depends(get_current_user),
    workspace_id: str = Query(default="default"),
    user_id: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    model: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
) -> dict[str, Any]:
    filters = _resolve_filters(
        user,
        workspace_id=workspace_id,
        user_id=user_id,
        channel=channel,
        model=model,
        provider=provider,
        days=days,
    )
    return await get_llm_usage_analytics().summary(filters)


@router.get("/timeseries")
async def usage_timeseries(
    user: dict = Depends(get_current_user),
    workspace_id: str = Query(default="default"),
    user_id: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    model: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    granularity: Literal["day", "hour"] = Query(default="day"),
) -> dict[str, Any]:
    filters = _resolve_filters(
        user,
        workspace_id=workspace_id,
        user_id=user_id,
        channel=channel,
        model=model,
        provider=provider,
        days=days,
    )
    points = await get_llm_usage_analytics().timeseries(filters, granularity=granularity)
    return {"granularity": granularity, "points": points}


@router.get("/breakdown/{dimension}")
async def usage_breakdown(
    dimension: Literal[
        "models",
        "providers",
        "channels",
        "users",
        "agents",
        "model",
        "provider",
        "channel",
        "user",
        "agent",
    ],
    user: dict = Depends(get_current_user),
    workspace_id: str = Query(default="default"),
    user_id: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    model: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
) -> dict[str, Any]:
    if dimension == "users" and not _usage_admin(user):
        raise HTTPException(status_code=403, detail="Admin access required for user breakdown")
    filters = _resolve_filters(
        user,
        workspace_id=workspace_id,
        user_id=user_id,
        channel=channel,
        model=model,
        provider=provider,
        days=days,
        allow_user_override=dimension not in {"users", "user"},
    )
    dim = dimension.rstrip("s") if dimension.endswith("s") else dimension
    rows = await get_llm_usage_analytics().breakdown(filters, dimension=dim)  # type: ignore[arg-type]
    return {"dimension": dimension, "items": rows}


@router.get("/events")
async def usage_events(
    user: dict = Depends(get_current_user),
    workspace_id: str = Query(default="default"),
    user_id: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    model: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    from_ts: datetime | None = Query(default=None),
    to_ts: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    if not _usage_admin(user):
        limit = min(limit, 50)
    filters = _resolve_filters(
        user,
        workspace_id=workspace_id,
        user_id=user_id,
        channel=channel,
        model=model,
        provider=provider,
        days=days,
        from_ts=from_ts,
        to_ts=to_ts,
    )
    return await get_llm_usage_analytics().list_events(filters, limit=limit, offset=offset)


@router.get("/status")
async def usage_status(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Workspace metering status (enabled flag + role hints)."""
    from keprix.usage.config import get_llm_usage_config

    config = get_llm_usage_config()
    return {
        "enabled": config.enabled,
        "retention_days": config.retention_days,
        "is_admin": _usage_admin(user),
        "enable_hint": "Set KEPRIX_LLM_USAGE_ENABLED=true and restart the API.",
    }


@router.get("/export")
async def usage_export(
    user: dict = Depends(get_current_user),
    workspace_id: str = Query(default="default"),
    user_id: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    model: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    days: int = Query(default=90, ge=1, le=365),
    export_format: Literal["csv", "json"] = Query(default="csv", alias="format"),
) -> StreamingResponse:
    filters = _resolve_filters(
        user,
        workspace_id=workspace_id,
        user_id=user_id,
        channel=channel,
        model=model,
        provider=provider,
        days=days,
    )
    from keprix.usage.store import get_llm_usage_store

    if export_format == "json":

        async def stream_json() -> AsyncIterator[bytes]:
            yield b'{"items":['
            first = True
            for row in get_llm_usage_store().iter_export_rows_sync(filters):
                item = {
                    "recorded_at": row[0],
                    "user_id": row[1],
                    "channel": row[2],
                    "provider": row[3],
                    "model": row[4],
                    "input_tokens": row[5],
                    "output_tokens": row[6],
                    "total_tokens": row[7],
                    "cost_usd": row[8],
                    "cost_status": row[9],
                    "session_id": row[10],
                    "run_id": row[11],
                }
                chunk = (("" if first else ",") + json.dumps(item)).encode("utf-8")
                first = False
                yield chunk
            yield b"]}"

        headers = {"Content-Disposition": 'attachment; filename="llm-usage-export.json"'}
        return StreamingResponse(stream_json(), media_type="application/json", headers=headers)

    async def stream_rows() -> AsyncIterator[bytes]:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "recorded_at",
                "user_id",
                "channel",
                "provider",
                "model",
                "input_tokens",
                "output_tokens",
                "total_tokens",
                "cost_usd",
                "cost_status",
                "session_id",
                "run_id",
            ]
        )
        yield buffer.getvalue().encode("utf-8")
        buffer.seek(0)
        buffer.truncate(0)

        for row in get_llm_usage_store().iter_export_rows_sync(filters):
            writer.writerow(row)
            if buffer.tell() > 65536:
                yield buffer.getvalue().encode("utf-8")
                buffer.seek(0)
                buffer.truncate(0)
        if buffer.tell():
            yield buffer.getvalue().encode("utf-8")

    headers = {"Content-Disposition": 'attachment; filename="llm-usage-export.csv"'}
    return StreamingResponse(stream_rows(), media_type="text/csv", headers=headers)


@router.get("/budget")
async def get_budget(
    user: dict = Depends(get_current_user),
    workspace_id: str = Query(default="default"),
) -> dict[str, Any]:
    if not _usage_admin(user) and workspace_id != "default":
        raise HTTPException(status_code=403, detail="Cannot query another workspace budget")
    return await get_llm_usage_analytics().budget_status(workspace_id)


@router.put("/budget")
async def put_budget(
    body: BudgetBody,
    _admin: dict = Depends(require_admin),
    workspace_id: str = Query(default="default"),
) -> dict[str, Any]:
    try:
        budget = (
            Decimal(str(body.monthly_budget_usd))
            if body.monthly_budget_usd is not None
            else None
        )
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid monthly_budget_usd") from exc
    saved = await get_llm_usage_analytics().set_budget(
        workspace_id,
        monthly_budget_usd=budget,
        alert_threshold_percent=body.alert_threshold_percent,
    )
    status = await get_llm_usage_analytics().budget_status(workspace_id)
    return {"budget": saved, "status": status}


@router.get("/pricing/models")
async def pricing_models(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"models": list_pricing_catalog()}
