"""Coding preflight API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.coding.preflight_config import PreflightConfig, get_preflight_config, save_preflight_config
from keprix.coding.preflight_service import PreflightService
from keprix.coding.preflight_store import PreflightStore
from keprix.public_api.auth import require_developer_session

router = APIRouter(prefix="/api/coding/preflight", tags=["coding"])


class PreflightRunBody(BaseModel):
    session_id: str = Field(..., min_length=1)
    intent: str | None = None
    repo_path: str | None = None
    mutation_plan: dict[str, Any] | None = None
    recent_user_messages: list[str] = Field(default_factory=list)
    changed_files: list[str] = Field(default_factory=list)
    repo_index_present: bool = False
    tests_present: bool | None = None
    provider_budget_pct: float | None = None
    planned_lines: int | None = None


class ConfigBody(BaseModel):
    enabled: bool = True
    diff_budget_lines: int = Field(default=400, ge=1)
    duplicate_window_turns: int = Field(default=8, ge=1)
    provider_budget_warn_pct: int = Field(default=85, ge=1, le=100)
    allow_override: bool = True
    gates: dict[str, bool] = Field(default_factory=dict)


@router.post("/run")
async def run_preflight(body: PreflightRunBody, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    payload = body.model_dump(exclude={"session_id"})
    report = PreflightService().run(session_id=body.session_id, payload=payload)
    return {"report": report.to_dict()}


@router.get("/config")
async def get_preflight_settings(_session: str = Depends(require_developer_session)) -> dict[str, Any]:
    return {"config": get_preflight_config().to_dict()}


@router.put("/config")
async def update_preflight_settings(body: ConfigBody, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    config = PreflightConfig(**body.model_dump())
    return {"config": save_preflight_config(config).to_dict()}


@router.get("/{session_id}")
async def get_preflight(session_id: str, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    report = PreflightStore().get(session_id)
    if report is None:
        raise HTTPException(status_code=404, detail="preflight report not found")
    return {"report": report.to_dict()}


@router.post("/{session_id}/override")
async def override_preflight(session_id: str, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    report = PreflightService().override(session_id)
    if report is None:
        raise HTTPException(status_code=404, detail="preflight report not found")
    return {"report": report.to_dict()}
