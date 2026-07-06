"""Opportunity Engine HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from keprix.auth.dependencies import get_current_user
from keprix.opportunity.approvals import resolve_approval
from keprix.opportunity.models import OpportunityPhase, OpportunityRequest, PHASE_ORDER
from keprix.opportunity.orchestrator import run_opportunity_phase, run_opportunity_pipeline
from keprix.opportunity.registry import get_opportunity_registry
from keprix.opportunity.workspace import OPPORTUNITY_ID_RE, read_artifact, read_opportunity_asset, read_opportunity_json
from keprix.security.validation import ValidationError, default_validator

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


def _user_id(user: dict) -> str:
    return str(user.get("id") or user.get("username") or "local")


def _validate_opportunity_id(opportunity_id: str) -> None:
    if not OPPORTUNITY_ID_RE.fullmatch(opportunity_id):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid opportunity ID: {opportunity_id!r}",
        )


class OpportunityCreateBody(BaseModel):
    title: str = Field(..., min_length=1)
    workspace_id: str = "default"
    niche: str | None = None
    market: str | None = None
    goal: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return default_validator.validate_string(value, "title")


class RunOptionsBody(BaseModel):
    stop_at: OpportunityPhase | None = None
    pause_on_approval: bool = False


class ApproveBody(BaseModel):
    approval_id: str
    approved: bool = True


@router.post("", status_code=201)
async def create_opportunity(
    body: OpportunityCreateBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    registry = get_opportunity_registry()
    request = OpportunityRequest(
        workspace_id=body.workspace_id,
        title=body.title,
        niche=body.niche,
        market=body.market,
        goal=body.goal,
        source="api",
    )
    workspace = registry.create(user_id=_user_id(user), request=request)
    return workspace.model_dump(mode="json")


@router.get("")
async def list_opportunities(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    registry = get_opportunity_registry()
    records = registry.list_for_user(_user_id(user))
    return {"opportunities": [record.to_dict() for record in records]}


@router.get("/{opportunity_id}")
async def get_opportunity(
    opportunity_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _validate_opportunity_id(opportunity_id)
    registry = get_opportunity_registry()
    record = registry.get(opportunity_id)
    if record is None or record.user_id != _user_id(user):
        raise HTTPException(status_code=404, detail="Opportunity not found")
    meta = read_opportunity_json(opportunity_id)
    return {"record": record.to_dict(), "meta": meta}


@router.post("/{opportunity_id}/run")
async def run_pipeline(
    opportunity_id: str,
    body: RunOptionsBody | None = None,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _validate_opportunity_id(opportunity_id)
    registry = get_opportunity_registry()
    record = registry.get(opportunity_id)
    if record is None or record.user_id != _user_id(user):
        raise HTTPException(status_code=404, detail="Opportunity not found")
    options = body.model_dump(exclude_none=True) if body else {}
    return await run_opportunity_pipeline(opportunity_id, options)


@router.post("/{opportunity_id}/phase/{phase}")
async def run_phase(
    opportunity_id: str,
    phase: OpportunityPhase,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _validate_opportunity_id(opportunity_id)
    if phase not in PHASE_ORDER:
        raise HTTPException(status_code=422, detail=f"Unknown phase: {phase}")
    registry = get_opportunity_registry()
    record = registry.get(opportunity_id)
    if record is None or record.user_id != _user_id(user):
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return await run_opportunity_phase(opportunity_id, phase)


@router.get("/{opportunity_id}/artifacts/{filename}")
async def get_artifact(
    opportunity_id: str,
    filename: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _validate_opportunity_id(opportunity_id)
    registry = get_opportunity_registry()
    record = registry.get(opportunity_id)
    if record is None or record.user_id != _user_id(user):
        raise HTTPException(status_code=404, detail="Opportunity not found")
    try:
        content = read_artifact(opportunity_id, filename)
    except (FileNotFoundError, ValidationError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"filename": filename, "content": content}


@router.get("/{opportunity_id}/assets/{filename}")
async def get_asset_file(
    opportunity_id: str,
    filename: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _validate_opportunity_id(opportunity_id)
    registry = get_opportunity_registry()
    record = registry.get(opportunity_id)
    if record is None or record.user_id != _user_id(user):
        raise HTTPException(status_code=404, detail="Opportunity not found")
    try:
        content = read_opportunity_asset(opportunity_id, filename)
    except (FileNotFoundError, ValidationError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"filename": filename, "content": content}


@router.post("/{opportunity_id}/approve")
async def approve_action(
    opportunity_id: str,
    body: ApproveBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _validate_opportunity_id(opportunity_id)
    registry = get_opportunity_registry()
    record = registry.get(opportunity_id)
    if record is None or record.user_id != _user_id(user):
        raise HTTPException(status_code=404, detail="Opportunity not found")
    resolved = resolve_approval(
        workspace_id=record.workspace_id,
        opportunity_id=opportunity_id,
        approval_id=body.approval_id,
        approved=body.approved,
        approved_by=_user_id(user),
    )
    if resolved is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return resolved.model_dump(mode="json")


@router.post("/{opportunity_id}/pause")
async def pause_opportunity(
    opportunity_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _validate_opportunity_id(opportunity_id)
    registry = get_opportunity_registry()
    record = registry.get(opportunity_id)
    if record is None or record.user_id != _user_id(user):
        raise HTTPException(status_code=404, detail="Opportunity not found")
    updated = registry.update_status(opportunity_id, "paused")
    return updated.to_dict()


@router.post("/{opportunity_id}/archive")
async def archive_opportunity(
    opportunity_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _validate_opportunity_id(opportunity_id)
    registry = get_opportunity_registry()
    record = registry.get(opportunity_id)
    if record is None or record.user_id != _user_id(user):
        raise HTTPException(status_code=404, detail="Opportunity not found")
    updated = registry.update_status(opportunity_id, "archived")
    return updated.to_dict()
