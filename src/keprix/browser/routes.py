"""Browser automation HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from keprix.api.auth import require_api_auth
from keprix.browser.action_engine import get_action_engine
from keprix.browser.drivers import BrowserDriverUnavailableError
from keprix.browser.qa_runner import BrowserQaRunner

router = APIRouter(prefix="/api/browser", tags=["browser"])


class SessionBody(BaseModel):
    objective: str = Field(default="Browse", min_length=1)
    url: str = "about:blank"


class RunBody(BaseModel):
    action: str | None = None
    objective: str | None = None
    selector: str = ""
    value: str = ""


class QaBody(BaseModel):
    scenario: str = Field(..., min_length=1)
    url: str = "about:blank"


@router.post("/session")
async def create_session(body: SessionBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    try:
        session = get_action_engine().create_session(objective=body.objective, url=body.url)
    except BrowserDriverUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"session_id": session.session_id, "objective": session.objective}


@router.get("/{session_id}/proposals")
async def list_proposals(session_id: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    try:
        return get_action_engine().propose_actions(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Browser session not found") from exc


@router.post("/{session_id}/run")
async def run_action(
    session_id: str,
    body: RunBody,
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    engine = get_action_engine()
    try:
        if body.objective:
            session = engine.get(session_id)
            if session is None:
                raise KeyError(session_id)
            session.objective = body.objective
            return engine.propose_actions(session_id)
        if not body.action:
            raise HTTPException(status_code=400, detail="Provide action or objective")
        return engine.run_action(
            session_id,
            action=body.action,
            selector=body.selector,
            value=body.value,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Browser session not found") from exc


@router.post("/{session_id}/approve")
async def approve_action(session_id: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    try:
        return get_action_engine().approve_pending(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Browser session not found") from exc


@router.get("/{session_id}/actions")
async def list_actions(session_id: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return {"actions": get_action_engine().list_actions(session_id)}


@router.get("/{session_id}/screenshot/{screenshot_id}")
async def get_screenshot(
    session_id: str,
    screenshot_id: str,
    _user: str = Depends(require_api_auth),
) -> Response:
    data = get_action_engine().get_screenshot(session_id, screenshot_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return Response(content=data, media_type="image/png")


@router.post("/qa/run")
async def run_qa(body: QaBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    try:
        report = BrowserQaRunner(get_action_engine()).run_scenario(body.scenario, url=body.url)
    except BrowserDriverUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return report.to_dict()
