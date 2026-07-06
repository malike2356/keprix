"""Admin dashboard statistics routes."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query

from keprix.agent.keprix.store import get_generated_tool_store
from keprix.auth.dependencies import get_current_user, require_admin
from keprix.memory.episodic.store import create_episodic_store
from keprix.memory.rag.indexer import RagIndexer
from keprix.tools.registry import registry as tool_registry
from keprix.usage.analytics import get_llm_usage_analytics
from keprix.usage.filters import UsageQueryFilters
from keprix.workspace.repository import workspace_repo

router = APIRouter(prefix="/api/stats", tags=["stats"])
_episodic_store = create_episodic_store()
_rag_indexer = RagIndexer()


@router.get("/conversations/count")
async def conversation_count(user: dict = Depends(get_current_user)) -> dict[str, int]:
    sessions = workspace_repo.list_sessions(user, limit=10_000, offset=0)
    return {"count": len(sessions)}


@router.get("/conversations/daily")
async def conversation_daily(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    sessions = workspace_repo.list_sessions(user, limit=10_000, offset=0)
    today = datetime.now(timezone.utc).date()
    buckets: dict[str, int] = {}
    for offset in range(29, -1, -1):
        day = today - timedelta(days=offset)
        buckets[day.isoformat()] = 0
    for session in sessions:
        raw = session.get("created_at") or session.get("updated_at")
        if not raw:
            continue
        try:
            day = datetime.fromisoformat(str(raw).replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            continue
        if day in buckets:
            buckets[day] += 1
    return {
        "labels": list(buckets.keys()),
        "values": list(buckets.values()),
    }


@router.get("/tools/count")
async def tools_count(_admin: dict = Depends(require_admin)) -> dict[str, int]:
    builtin = len(tool_registry.get_all_tool_names())
    generated = len(get_generated_tool_store().list_all(status="approved"))
    return {"count": builtin + generated, "builtin": builtin, "generated": generated}


@router.get("/mutations/approved")
async def mutations_approved(_admin: dict = Depends(require_admin)) -> dict[str, int]:
    approved = len(get_generated_tool_store().list_all(status="approved"))
    pending = len(get_generated_tool_store().list_all(status="pending"))
    rejected = len(get_generated_tool_store().list_all(status="rejected"))
    return {"count": approved, "pending": pending, "rejected": rejected}


@router.get("/memory/count")
async def memory_count(user: dict = Depends(get_current_user)) -> dict[str, int]:
    user_id = str(user.get("id") or user.get("username") or "default")
    memories = await _episodic_store.list_all(user_id)
    rag_sources = await _rag_indexer.list_sources(user_id)
    return {"count": len(memories) + len(rag_sources), "memories": len(memories), "rag_sources": len(rag_sources)}


@router.get("/tools/breakdown")
async def tools_breakdown(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    store = get_generated_tool_store()
    synthesised = len(store.list_all(status="approved"))
    builtin = len(tool_registry.get_all_tool_names())
    community = len(store.list_all(status="installed"))
    return {
        "labels": ["Synthesised", "Built-in", "Community"],
        "values": [synthesised, builtin, community],
    }


@router.get("/llm/summary")
async def llm_summary(
    _admin: dict = Depends(require_admin),
    days: int = Query(default=30, ge=1, le=365),
    workspace_id: str = Query(default="default"),
) -> dict[str, Any]:
    filters = UsageQueryFilters.from_params(workspace_id=workspace_id, days=days)
    summary = await get_llm_usage_analytics().summary(filters)
    return {
        "llmSpend30d": summary.get("total_cost_usd", 0.0),
        "llmTokens30d": summary.get("total_tokens", 0),
        "llmRequestCount30d": summary.get("request_count", 0),
        "period_days": summary.get("period_days", days),
    }


@router.get("/mutations/compounding")
async def mutations_compounding(
    _admin: dict = Depends(require_admin),
    workspace_id: str = Query(default="default"),
) -> dict[str, Any]:
    from keprix.mutation.compounding import compute_compounding_metrics

    metrics = compute_compounding_metrics(workspace_id)
    return metrics.to_dict()


@router.get("/mutations/active-daily")
async def mutations_active_daily(
    _admin: dict = Depends(require_admin),
    workspace_id: str = Query(default="default"),
) -> dict[str, Any]:
    from keprix.mutation.compounding import active_mutations_daily_series

    return active_mutations_daily_series(workspace_id)
