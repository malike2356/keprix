"""Authenticated property calculator endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user, require_admin
from .registry import CalculatorError, list_strategies
from .service import calculator_rules, calculator_settings, run_workspace_calculator, update_calculator_settings

router = APIRouter(prefix="/api/property/calculators", tags=["property-calculators"])


class CalculatorRunBody(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)


class CalculatorSettingsBody(BaseModel):
    overrides: dict[str, Any] = Field(default_factory=dict)


@router.get("")
async def list_calculators(_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return {"calculators": list_strategies()}


@router.get("/{strategy}/rules")
async def rules(strategy: str, workspace_id: str = "default", _user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    try:
        return calculator_rules(strategy, workspace_id)
    except CalculatorError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{strategy}/run")
async def run(strategy: str, body: CalculatorRunBody, workspace_id: str = "default", _user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    try:
        return run_workspace_calculator(workspace_id, strategy, body.inputs)
    except CalculatorError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc), "field_errors": exc.field_errors}) from exc


@router.get("/settings")
async def settings(workspace_id: str = "default", _user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return calculator_settings(workspace_id)


@router.patch("/settings")
async def update_settings(body: CalculatorSettingsBody, workspace_id: str = "default", _admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    try:
        return update_calculator_settings(workspace_id, body.overrides)
    except CalculatorError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
