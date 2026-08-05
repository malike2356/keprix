"""Credential rotation admin API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from keprix.api.auth import require_admin
from keprix.proxy.config import load_proxy_config
from keprix.proxy.rotation import rotation_status

router = APIRouter(prefix="/api/admin/credentials/rotation", tags=["admin-credentials"])


@router.get("")
async def get_rotation_status(admin: dict = Depends(require_admin)) -> dict[str, Any]:
    _ = admin
    return rotation_status(load_proxy_config())
