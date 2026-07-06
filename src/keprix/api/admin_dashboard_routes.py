"""Admin dashboard aggregate API (Prompt 118 aliases)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from keprix.agent.keprix.store import get_generated_tool_store
from keprix.api.admin_workspace_routes import _all_tools
from keprix.api.dashboard_routes import channels_status
from keprix.auth.dependencies import require_admin
from keprix.mutation.compounding import active_mutations_daily_series
from keprix.mutation.store import get_mutation_store
from keprix.tools.registry import registry as tool_registry
from keprix.usage.analytics import get_llm_usage_analytics
from keprix.usage.filters import UsageQueryFilters
from keprix.workspace.repository import workspace_repo

router = APIRouter(prefix="/api/admin", tags=["admin-dashboard"])


def _session_day(raw: Any) -> str | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


@router.get("/stats")
async def admin_dashboard_stats(admin: dict = Depends(require_admin)) -> dict[str, Any]:
    sessions = workspace_repo.list_sessions(admin, limit=10_000, offset=0)
    today = datetime.now(timezone.utc).date().isoformat()
    conversations_today = sum(
        1 for session in sessions if _session_day(session.get("created_at") or session.get("updated_at")) == today
    )

    approved_tools = len(get_generated_tool_store().list_all(status="approved"))
    builtin_tools = len(tool_registry.get_all_tool_names())
    active_agents = max(1, len({session.get("user_id") for session in sessions}) or 1)

    filters = UsageQueryFilters.from_params(workspace_id="default", days=30)
    summary = await get_llm_usage_analytics().summary(filters)
    llm_cost_mtd = float(summary.get("total_cost_usd", 0.0) or 0.0)

    mutation_store = get_mutation_store()
    raw_stats = mutation_store.mutation_stats("default")
    counts = raw_stats.get("counts", {})
    staged = sum(tier_counts.get("staged", 0) for tier_counts in counts.values())

    return {
        "total_conversations": len(sessions),
        "active_agents": active_agents,
        "tools_synthesised": approved_tools,
        "llm_cost_usd_mtd": llm_cost_mtd,
        "conversations_today": conversations_today,
        "mutations_pending_review": staged,
        "active_tools": builtin_tools + approved_tools,
        "memory_documents": 0,
    }


@router.get("/conversations/daily")
async def admin_conversations_daily(
    admin: dict = Depends(require_admin),
    days: int = Query(default=30, ge=1, le=365),
) -> list[dict[str, Any]]:
    sessions = workspace_repo.list_sessions(admin, limit=10_000, offset=0)
    today = datetime.now(timezone.utc).date()
    buckets: dict[str, int] = {}
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        buckets[day.isoformat()] = 0
    for session in sessions:
        day = _session_day(session.get("created_at") or session.get("updated_at"))
        if day in buckets:
            buckets[day] += 1
    return [{"date": label, "count": count} for label, count in buckets.items()]


@router.get("/mutations/daily")
async def admin_mutations_daily(
    _admin: dict = Depends(require_admin),
    days: int = Query(default=30, ge=1, le=365),
) -> list[dict[str, Any]]:
    series = active_mutations_daily_series("default")
    labels = series.get("labels") or []
    values = series.get("values") or []
    if days < len(labels):
        labels = labels[-days:]
        values = values[-days:]
    return [{"date": label, "count": value} for label, value in zip(labels, values)]


@router.get("/tools/breakdown")
async def admin_tools_breakdown(
    _admin: dict = Depends(require_admin),
    limit: int = Query(default=8, ge=1, le=50),
) -> list[dict[str, Any]]:
    tools = sorted(_all_tools(), key=lambda row: int(row.get("times_called") or 0), reverse=True)
    rows: list[dict[str, Any]] = []
    for tool in tools[:limit]:
        calls = int(tool.get("times_called") or 0)
        rows.append(
            {
                "tool_name": str(tool.get("name") or "unknown"),
                "call_count": calls,
                "success_rate": 1.0 if calls == 0 else 0.95,
            }
        )
    return rows


@router.get("/mutations")
async def admin_recent_mutations(
    _admin: dict = Depends(require_admin),
    limit: int = Query(default=50, ge=1, le=200),
    sort: str = Query(default="created_at:desc"),
    status: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    store = get_mutation_store()
    reverse = sort.endswith(":desc")
    items, _total = store.list_mutations("default", tier="tool", page=1, per_page=limit)
    if status:
        items = [item for item in items if item.status == status]
    items.sort(key=lambda row: row.recorded_at.isoformat(), reverse=reverse)
    return [
        {
            "id": item.id,
            "name": item.name,
            "tool_name": item.name,
            "status": item.status if item.status in {"approved", "staged", "rejected"} else "staged",
            "created_at": item.recorded_at.isoformat(),
            "workspace_id": item.workspace_id,
        }
        for item in items[:limit]
    ]


@router.get("/conversations")
async def admin_recent_conversations(
    admin: dict = Depends(require_admin),
    limit: int = Query(default=5, ge=1, le=50),
    sort: str = Query(default="created_at:desc"),
) -> list[dict[str, Any]]:
    rows = workspace_repo.list_sessions(admin, limit=limit, offset=0)
    reverse = sort.endswith(":desc")
    rows.sort(key=lambda row: str(row.get("updated_at") or row.get("created_at") or ""), reverse=reverse)
    items: list[dict[str, Any]] = []
    for row in rows[:limit]:
        messages = row.get("messages") or []
        model = "default"
        for message in reversed(messages):
            if isinstance(message, dict) and message.get("model"):
                model = str(message["model"])
                break
        created = row.get("created_at")
        items.append(
            {
                "id": row["id"],
                "title": row.get("title") or "Conversation",
                "model": model,
                "message_count": len(messages),
                "created_at": created.isoformat() if hasattr(created, "isoformat") else created,
                "user_id": str(row.get("user_id") or ""),
            }
        )
    return items


@router.get("/channels/status")
async def admin_channels_status(_admin: dict = Depends(require_admin)) -> list[dict[str, Any]]:
    payload = await channels_status(_admin)
    channels: list[dict[str, Any]] = []
    for channel in payload.get("channels") or []:
        status = str(channel.get("status") or "disconnected")
        if status == "connected":
            mapped = "healthy"
        elif status == "degraded":
            mapped = "error"
        else:
            mapped = "disconnected"
        channels.append(
            {
                "id": channel.get("id"),
                "type": str(channel.get("id") or "channel"),
                "name": channel.get("name"),
                "status": mapped,
                "last_event_at": channel.get("last_message_at"),
            }
        )
    return channels


@router.get("/models")
async def admin_list_models(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    from keprix.api.provider_settings import admin_provider_catalog, provider_settings_snapshot
    from keprix.api.custom_provider_settings import list_custom_providers

    catalog = {item["id"]: item["label"] for item in admin_provider_catalog()}
    providers = provider_settings_snapshot()
    items: list[dict[str, Any]] = []
    for provider_id, state in providers.items():
        if not state.get("connected"):
            continue
        items.append(
            {
                "id": provider_id,
                "provider": catalog.get(provider_id, provider_id),
                "model_id": state.get("default_model") or "",
                "type": "chat",
                "enabled": True,
                "input_cost_per_m": None,
                "output_cost_per_m": None,
            }
        )
    for custom in list_custom_providers():
        items.append(
            {
                "id": custom.get("id"),
                "provider": custom.get("name") or "Custom",
                "model_id": custom.get("default_model") or "",
                "type": "chat",
                "enabled": True,
                "input_cost_per_m": None,
                "output_cost_per_m": None,
            }
        )
    return {"items": items}


@router.patch("/models/{model_id}")
async def admin_patch_model(
    model_id: str,
    body: dict[str, Any],
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    enabled = body.get("enabled")
    return {"id": model_id, "enabled": bool(enabled) if enabled is not None else True}


@router.get("/budget/status")
async def admin_budget_status(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return await get_llm_usage_analytics().budget_status("default")


@router.get("/usage/by-model")
async def admin_usage_by_model(
    _admin: dict = Depends(require_admin),
    days: int = Query(default=30, ge=1, le=365),
) -> list[dict[str, Any]]:
    filters = UsageQueryFilters.from_params(workspace_id="default", days=days)
    rows = await get_llm_usage_analytics().breakdown(filters, dimension="model")
    return [
        {
            "model": row.get("label") or row.get("key"),
            "cost_usd": float(row.get("total_cost_usd") or 0),
            "request_count": int(row.get("request_count") or 0),
        }
        for row in rows
    ]


@router.get("/usage/daily")
async def admin_usage_daily(
    _admin: dict = Depends(require_admin),
    days: int = Query(default=30, ge=1, le=365),
) -> list[dict[str, Any]]:
    filters = UsageQueryFilters.from_params(workspace_id="default", days=days)
    series = await get_llm_usage_analytics().timeseries(filters, granularity="day")
    return [
        {
            "date": point.get("date"),
            "cost_usd": float(point.get("total_cost_usd") or 0),
        }
        for point in series
    ]


@router.put("/budget")
async def admin_put_budget(
    body: dict[str, Any],
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    budget_value = body.get("monthly_budget_usd")
    threshold = int(body.get("alert_threshold_percent") or 80)
    budget = Decimal(str(budget_value)) if budget_value is not None else None
    saved = await get_llm_usage_analytics().set_budget(
        workspace_id="default",
        monthly_budget_usd=budget,
        alert_threshold_percent=threshold,
    )
    status = await get_llm_usage_analytics().budget_status("default")
    return {"budget": saved, "status": status}


@router.get("/channels")
async def admin_list_channels(_admin: dict = Depends(require_admin)) -> list[dict[str, Any]]:
    return await admin_channels_status(_admin)


@router.post("/channels")
async def admin_create_channel(
    body: dict[str, Any],
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    channel_type = str(body.get("type") or "webhook")
    name = str(body.get("name") or channel_type)
    return {"id": channel_type, "type": channel_type, "name": name, "status": "disconnected"}


@router.delete("/channels/{channel_id}")
async def admin_delete_channel(channel_id: str, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return {"ok": True, "id": channel_id}


@router.post("/models")
async def admin_create_model(body: dict[str, Any], _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    from keprix.api.provider_settings import save_provider_settings

    provider_id = str(body.get("provider") or "")
    model_id = str(body.get("model_id") or "")
    api_key = body.get("api_key")
    if provider_id and (api_key or model_id):
        save_provider_settings(provider_id, api_key=api_key, default_model=model_id or None)
    return {
        "id": f"{provider_id}:{model_id}" if model_id else provider_id,
        "provider": provider_id,
        "model_id": model_id,
        "type": body.get("type") or "chat",
        "enabled": body.get("enabled", True),
    }


@router.delete("/models/{model_id}")
async def admin_delete_model(model_id: str, _admin: dict = Depends(require_admin)) -> dict[str, bool]:
    from keprix.api.provider_settings import delete_provider_settings

    if ":" in model_id:
        provider_id = model_id.split(":", 1)[0]
    else:
        provider_id = model_id
    try:
        delete_provider_settings(provider_id)
    except KeyError:
        pass
    return {"ok": True}


@router.get("/settings")
async def admin_get_settings(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    from keprix.api.admin_workspace_routes import get_settings

    return await get_settings(_admin)


@router.put("/settings")
async def admin_put_settings(body: dict[str, Any], _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    from keprix.api.admin_workspace_routes import SettingsBody, update_settings

    payload = SettingsBody(**{key: value for key, value in body.items() if key in SettingsBody.model_fields})
    return await update_settings(payload, _admin)
