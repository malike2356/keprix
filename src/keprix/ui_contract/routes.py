"""HTTP routes exposing the shared UI contract."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from keprix.auth.dependencies import get_current_user
from keprix.ui_contract import build_ui_contract

router = APIRouter(prefix="/api/ui", tags=["ui-contract"])


@router.get("/contract")
async def get_ui_contract(user: dict = Depends(get_current_user)) -> dict:
    return build_ui_contract(user)
