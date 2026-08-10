"""HTTP routes for prototype-to-production conveyor."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.conveyor import (
    default_keprix_root,
    generate_fixes_for_report,
    pipeline_status,
    run_full_audit,
    run_pipeline,
)

router = APIRouter(prefix="/api/conveyor", tags=["conveyor"])


class PipelineBody(BaseModel):
    target_env: str = Field(default="staging")
    human_approval: bool = False
    project_path: str | None = None


@router.get("/audit")
async def conveyor_audit(
    project_path: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    root = project_path or str(default_keprix_root())
    report = run_full_audit(root)
    return {"ok": True, "report": report, "fixes": generate_fixes_for_report(report)}


@router.get("/status")
async def conveyor_status(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return {"ok": True, "status": pipeline_status()}


@router.post("/pipeline")
async def conveyor_pipeline(
    body: PipelineBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    root = body.project_path or str(default_keprix_root())
    result = run_pipeline(root, body.target_env, human_approval=body.human_approval)
    return {"ok": result["report"]["passed"], **result}
