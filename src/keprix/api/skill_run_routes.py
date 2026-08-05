"""Compatibility routes for running skills headlessly."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.agent_os.headless_run_service import HeadlessRunService
from keprix.agent_os.run_ledger_store import RunLedgerStore
from keprix.agent_os.workflow_audit_service import agent_os_enabled
from keprix.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/skills", tags=["skill-runs"])


class SkillRunBody(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict)
    background: bool = False


def _guard_enabled() -> None:
    if not agent_os_enabled():
        raise HTTPException(status_code=403, detail="Agent OS is disabled")


def _headless_to_skill_payload(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "skill": result["source_id"],
        "status": result["status"],
        "output": result.get("output") or {},
        "tokens_used": result.get("tokens", 0),
        "duration_ms": result.get("duration_ms", 0),
        "session_id": result["run_id"],
        "run_id": result["run_id"],
        "ledger_entry_id": result.get("ledger_entry_id"),
        "events": result.get("events") or [],
        "error": result.get("error"),
    }


@router.post("/{skill_slug}/run")
async def run_skill_headless(skill_slug: str, body: SkillRunBody | None = None, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    try:
        result = await HeadlessRunService().run_skill(skill_slug, (body.params if body else None))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _headless_to_skill_payload(result.to_dict())


@router.get("/{skill_slug}/runs")
async def skill_runs(skill_slug: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    entries = [
        entry.to_dict()
        for entry in RunLedgerStore().list(source_type="skill", source_id=skill_slug, limit=100)
    ]
    return {"skill": skill_slug, "runs": entries}
