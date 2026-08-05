"""Edition information API."""

from __future__ import annotations

from fastapi import APIRouter

from keprix.licensing.dependencies import get_edition_info

router = APIRouter(prefix="/api/licensing", tags=["licensing"])


@router.get("/edition")
async def edition_info() -> dict:
    return get_edition_info()
