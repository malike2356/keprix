"""API v1 router. Each module registers its own sub-router here."""

from fastapi import APIRouter

from keprix.api.v1 import health

v1_router = APIRouter()

v1_router.include_router(health.router, tags=["system"])
