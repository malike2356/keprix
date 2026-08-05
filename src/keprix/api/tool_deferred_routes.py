"""Admin routes for deferred tool search stats (Prompt 294)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from keprix.auth.dependencies import require_admin

router = APIRouter(prefix="/api/admin/tools", tags=["admin"])


@router.get("/deferred-stats")
async def deferred_tool_stats(_admin: dict = Depends(require_admin)) -> dict:
    """Return process-level deferred tool search metrics."""
    from tools.tool_search import get_deferred_tool_stats

    stats = get_deferred_tool_stats()
    return {"ok": True, "stats": stats.to_dict()}
