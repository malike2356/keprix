"""Ops/search routes for private error logs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from keprix.auth.dependencies import get_current_user
from keprix.errors import detect_five_hundred_spike, get_error_context, search_errors

router = APIRouter(prefix="/api/errors", tags=["errors"])


@router.get("/search")
async def errors_search(
    user: dict = Depends(get_current_user),
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    user_id: str | None = Query(default=None, alias="userId"),
    route: str | None = Query(default=None),
    status_code: int | None = Query(default=None, alias="statusCode"),
    error_reference: str | None = Query(default=None, alias="errorReference"),
    limit: int = Query(default=100),
) -> dict[str, Any]:
    _ = user
    rows = search_errors(
        {
            "from": from_,
            "to": to,
            "userId": user_id,
            "route": route,
            "statusCode": status_code,
            "errorReference": error_reference,
            "limit": limit,
        }
    )
    return {
        "ok": True,
        "count": len(rows),
        "spike": detect_five_hundred_spike(),
        "errors": rows,
    }


@router.get("/{error_reference}")
async def errors_context(
    error_reference: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    row = get_error_context(error_reference)
    if not row:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True, "error": row}
