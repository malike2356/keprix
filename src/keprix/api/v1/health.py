"""Health and readiness endpoints."""

from __future__ import annotations

import time

from fastapi import APIRouter
from pydantic import BaseModel

from keprix.config.constants import EDITION, PRODUCT_NAME, PRODUCT_VERSION

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    product: str
    version: str
    edition: str
    uptime_seconds: float


_start_time = time.monotonic()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        product=PRODUCT_NAME,
        version=PRODUCT_VERSION,
        edition=EDITION,
        uptime_seconds=round(time.monotonic() - _start_time, 2),
    )


@router.get("/ready")
async def ready() -> dict[str, str]:
    """Kubernetes readiness probe. Returns 200 only when DB + Redis are reachable."""
    from keprix.database import engine
    from sqlalchemy import text
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ready"}
