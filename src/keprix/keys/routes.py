"""Developer identity HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter

from keprix.keys.developer_identity import get_identity_status
from keprix.keys.local_access import effective_access_level

router = APIRouter(prefix="/api/v1/identity", tags=["identity"])


@router.get("/status")
async def identity_status() -> dict:
    status = get_identity_status()
    status["access_level"] = effective_access_level()
    return status
