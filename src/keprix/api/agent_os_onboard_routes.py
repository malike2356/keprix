"""Agent OS onboard interview API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.agent_os.onboard_interview_service import OnboardInterviewService
from keprix.agent_os.onboarding_events import record_onboarding_event_for_user
from keprix.agent_os.workflow_audit_service import agent_os_enabled
from keprix.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/agent-os/onboard", tags=["agent-os"])


class StartBody(BaseModel):
    workspace_id: str = "personal-os"
    resume: bool = True


class AnswerBody(BaseModel):
    question: int = Field(..., ge=1, le=7)
    text: str = Field(..., min_length=1)


class CompleteBody(BaseModel):
    workspace_path: str | None = None


def _guard_enabled() -> None:
    if not agent_os_enabled():
        raise HTTPException(status_code=403, detail="Agent OS is disabled")


@router.get("/questions")
async def onboard_questions(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _guard_enabled()
    return {"questions": OnboardInterviewService().questions()}


@router.post("/start")
async def start_onboard(body: StartBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _guard_enabled()
    session = OnboardInterviewService().start(body.workspace_id, resume=body.resume)
    return {"session": session.to_dict(), "questions": OnboardInterviewService().questions()}


@router.get("/{session_id}")
async def get_onboard(session_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _guard_enabled()
    session = OnboardInterviewService().get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="onboard session not found")
    return {"session": session.to_dict(), "questions": OnboardInterviewService().questions()}


@router.post("/{session_id}/answer")
async def answer_onboard(session_id: str, body: AnswerBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _guard_enabled()
    try:
        session = OnboardInterviewService().answer(session_id, body.question, body.text)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="onboard session not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"session": session.to_dict()}


@router.post("/{session_id}/complete")
async def complete_onboard(session_id: str, body: CompleteBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    try:
        session = OnboardInterviewService().complete(session_id, workspace_path=body.workspace_path)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="onboard session not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    record_onboarding_event_for_user(user, "onboard.completed")
    return {"session": session.to_dict()}
