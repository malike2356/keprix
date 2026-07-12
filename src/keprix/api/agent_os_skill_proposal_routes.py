"""Agent OS skill proposal and self-improvement routes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.agent_os.onboarding_events import record_onboarding_event_for_user
from keprix.agent_os.workflow_audit_service import agent_os_enabled
from keprix.auth.dependencies import get_current_user
from keprix.improvement.session_pattern_detector import detect_session_patterns
from keprix.improvement.skill_improvement_loop import SkillRunRecord, propose_skill_improvements, record_skill_run
from keprix.improvement.skill_packager import package_skill
from keprix.improvement.skill_proposer import SkillProposalStore
from keprix.improvement.skill_review_reporter import generate_weekly_review, latest_review
from keprix_constants import get_keprix_home

router = APIRouter(prefix="/api/agent-os", tags=["agent-os"])


class ScanBody(BaseModel):
    session_count: int = Field(default=50, ge=3, le=200)
    min_occurrences: int = Field(default=3, ge=2, le=20)


class SkillRunBody(BaseModel):
    run_id: str
    skill_slug: str
    follow_up_action: str
    session_id: str | None = None


class ImprovementSettingsBody(BaseModel):
    watch_sessions: bool = True
    propose_at_occurrences: int = Field(default=3, ge=2, le=20)
    min_confidence: float = Field(default=0.7, ge=0, le=1)
    auto_create_skills: bool = False
    auto_apply_improvements: bool = False
    weekly_report_schedule: str = "0 9 * * 1"
    ignored_pattern_keywords: list[str] = Field(default_factory=list)


def _guard_enabled() -> None:
    if not agent_os_enabled():
        raise HTTPException(status_code=403, detail="Agent OS is disabled")


def _settings_path() -> Path:
    path = get_keprix_home() / "agent-os" / "self-improvement-settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_settings() -> dict[str, Any]:
    path = _settings_path()
    if not path.is_file():
        return ImprovementSettingsBody().model_dump()
    data = json.loads(path.read_text(encoding="utf-8"))
    return ImprovementSettingsBody(**data).model_dump()


@router.get("/skill-proposals")
async def list_skill_proposals(status: str | None = None, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    proposals = SkillProposalStore().list(status=status)
    return {"proposals": [proposal.to_dict() for proposal in proposals]}


@router.post("/skill-proposals/import")
async def import_skill_proposals(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    proposals = SkillProposalStore().import_pending_queue()
    return {"imported": len(proposals), "proposals": [proposal.to_dict() for proposal in proposals]}


@router.post("/skill-proposals/scan-sessions")
async def scan_session_patterns(body: ScanBody = ScanBody(), user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    store = SkillProposalStore()
    repeated = detect_session_patterns(user, session_count=body.session_count, min_occurrences=body.min_occurrences)
    proposals = [store.create_from_repeated_task(task) for task in repeated]
    return {"patterns": [task.__dict__ for task in repeated], "proposals": [proposal.to_dict() for proposal in proposals]}


@router.post("/skill-proposals/{proposal_id}/approve")
async def approve_skill_proposal(proposal_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    try:
        proposal = package_skill(proposal_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="proposal not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_onboarding_event_for_user(user, "skill_proposal.approved")
    return {"proposal": proposal.to_dict()}


@router.post("/skill-proposals/{proposal_id}/reject")
async def reject_skill_proposal(proposal_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    proposal = SkillProposalStore().reject(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="proposal not found")
    return {"proposal": proposal.to_dict()}


@router.get("/skill-review/latest")
async def get_skill_review(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    return {"report": latest_review()}


@router.post("/skill-review/generate")
async def generate_skill_review(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    return {"report": generate_weekly_review()}


@router.get("/settings/self-improvement")
async def get_self_improvement_settings(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    return {"settings": _load_settings()}


@router.put("/settings/self-improvement")
async def update_self_improvement_settings(
    body: ImprovementSettingsBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    payload = body.model_dump()
    _settings_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {"settings": payload}


@router.post("/skill-runs")
async def record_skill_run_event(body: SkillRunBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    record_skill_run(SkillRunRecord(**body.model_dump()))
    proposals = propose_skill_improvements()
    return {"proposals": [proposal.to_dict() for proposal in proposals]}
