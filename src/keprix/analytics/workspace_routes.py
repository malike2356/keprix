"""Analytics workspace REST endpoints (Prompt 54)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from keprix.analytics.code_interpreter import AnalyticsSession, CodeInterpreter
from keprix.analytics.container_executor import ContainerExecutor
from keprix.analytics.reflective_execution import ReflectiveExecutor
from keprix.api.auth import require_api_auth

router = APIRouter(prefix="/api/analytics", tags=["analytics-workspace"])

_executor = ContainerExecutor(container_required=False)
_interpreter = CodeInterpreter(executor=_executor)
_reflective = ReflectiveExecutor(_interpreter)


class RunRequest(BaseModel):
    code: str
    auto_repair: bool = True


class ApproveRequest(BaseModel):
    approve_network: bool = False
    approve_shell: bool = False


def _get_session(session_id: str) -> AnalyticsSession:
    session = _interpreter.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/sessions")
async def create_session(_user: str = Depends(require_api_auth)) -> dict:
    session = _interpreter.create_session()
    return {"session_id": session.session_id}


@router.post("/sessions/{session_id}/run")
async def run_code(
    session_id: str,
    body: RunRequest,
    _user: str = Depends(require_api_auth),
) -> dict:
    session = _get_session(session_id)
    if body.auto_repair:
        ok, trail = _reflective.run_with_repair(session, body.code)
        return {"ok": ok, "trail": [dict(a) for a in trail.attempts]}
    verification, result = _interpreter.run_code(session, body.code)
    return {
        "ok": result.ok,
        "verification_passed": verification.allowed,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, _user: str = Depends(require_api_auth)) -> dict:
    return _get_session(session_id).to_dict()


@router.get("/sessions/{session_id}/artifacts")
async def get_artifacts(session_id: str, _user: str = Depends(require_api_auth)) -> dict:
    session = _get_session(session_id)
    return {"artifacts": list(session.artifacts), "charts": list(session.charts)}


@router.post("/sessions/{session_id}/approve")
async def approve_session(
    session_id: str,
    body: ApproveRequest,
    _user: str = Depends(require_api_auth),
) -> dict:
    session = _get_session(session_id)
    session.approved_network = body.approve_network
    session.approved_shell = body.approve_shell
    return {
        "session_id": session_id,
        "approved_network": session.approved_network,
        "approved_shell": session.approved_shell,
    }
