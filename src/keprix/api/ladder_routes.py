"""Ponytail ladder API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from keprix.agent.ladder_mode import get_ladder_mode, set_ladder_mode
from keprix.auth.dependencies import get_current_user
from keprix.coding.ladder_audit import audit_repo
from keprix.coding.ladder_debt import add_debt, harvest_debt, list_debt, resolve_debt
from keprix.coding.ladder_metrics import ladder_metrics
from keprix.coding.ladder_review import review_diff

router = APIRouter(prefix="/api/coding/ladder", tags=["ponytail-ladder"])


class ModeBody(BaseModel):
    mode: str


class ReviewBody(BaseModel):
    diff: str = ""


class DebtBody(BaseModel):
    text: str


@router.get("/mode")
async def mode(user: dict = Depends(get_current_user)) -> dict[str, str]:
    _ = user
    return get_ladder_mode().to_dict()


@router.put("/mode")
async def put_mode(body: ModeBody, user: dict = Depends(get_current_user)) -> dict[str, str]:
    _ = user
    try:
        return set_ladder_mode(body.mode).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/review")
async def review(body: ReviewBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return review_diff(body.diff)


@router.get("/audit")
async def audit(root: str = ".", user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return audit_repo(root)


@router.get("/debt")
async def debt(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return {"items": [item.to_dict() for item in list_debt()]}


@router.post("/debt")
async def debt_add(body: DebtBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return add_debt(body.text).to_dict()


@router.post("/debt/{item_id}/resolve")
async def debt_resolve(item_id: int, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    item = resolve_debt(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="debt item not found")
    return item.to_dict()


@router.post("/debt/harvest")
async def debt_harvest(root: str = ".", user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return {"items": [item.to_dict() for item in harvest_debt(root)]}


@router.get("/metrics")
async def metrics(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return ladder_metrics()
