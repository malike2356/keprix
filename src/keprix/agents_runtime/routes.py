"""Agents runtime HTTP routes."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from keprix.agents_runtime.agent_spec import list_agents
from keprix.agents_runtime.executor import handoff_run, run_agent_step, start_run
from keprix.agents_runtime.realtime import create_session, get_session
from keprix.agents_runtime.run_context import get_run
from keprix.agent_apps.run_store import list_runs as list_agent_app_runs
from keprix.agent_apps.trace_view import build_agent_app_trace_view
from keprix.api.auth import require_api_auth
from keprix.observability.trace_export import export_trace
from keprix.observability.trace_view import build_trace_view

router = APIRouter(prefix="/api/agents-runtime", tags=["agents-runtime"])


class StartRunBody(BaseModel):
    agent: str = Field(..., min_length=1)
    input: str = Field(..., min_length=1)
    state: dict[str, Any] | None = None


class HandoffBody(BaseModel):
    target: str
    reason: str
    handoff_type: Literal["agent", "human", "tool", "playbook"] = "agent"
    accept: bool = True


class StepBody(BaseModel):
    input: str
    draft_output: str | None = None


class RealtimeEventBody(BaseModel):
    type: Literal["speech_in", "speech_out", "interrupt", "tool_pause", "escalation", "transcript"]
    text: str = ""


@router.get("/agents")
async def agents_list(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return {"agents": [agent.to_dict() for agent in list_agents()]}


@router.get("/runs")
async def list_runtime_runs(
    source: str | None = Query(default=None),
    app: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    if source == "agent_app":
        if not app:
            raise HTTPException(status_code=400, detail="app query param is required for agent_app source")
        return {
            "source": "agent_app",
            "app": app,
            "runs": list_agent_app_runs(app, limit=limit, offset=offset),
        }
    raise HTTPException(status_code=400, detail="Provide source=agent_app to list persisted agent app runs")


@router.post("/runs")
async def create_run(body: StartRunBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return await start_run(body.agent, user_input=body.input, state=body.state)


@router.post("/runs/{run_id}/step")
async def step_run(run_id: str, body: StepBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    ctx = get_run(run_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return await run_agent_step(ctx, user_input=body.input, draft_output=body.draft_output)


@router.post("/runs/{run_id}/handoff")
async def run_handoff(run_id: str, body: HandoffBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    result = await handoff_run(
        run_id,
        target=body.target,
        reason=body.reason,
        handoff_type=body.handoff_type,
        accept=body.accept,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=str(result.get("message")))
    return result


@router.get("/runs/{run_id}/trace")
async def run_trace(run_id: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    ctx = get_run(run_id)
    if ctx is not None:
        return build_trace_view(ctx)
    agent_app_trace = build_agent_app_trace_view(run_id)
    if agent_app_trace is not None:
        return agent_app_trace
    raise HTTPException(status_code=404, detail="Run not found")


@router.get("/runs/{run_id}/trace/export")
async def run_trace_export(run_id: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    ctx = get_run(run_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return export_trace(ctx)


@router.post("/realtime/sessions")
async def realtime_create(agent: str = "echo_agent", _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    session = create_session(agent)
    return session.to_dict()


@router.post("/realtime/sessions/{session_id}/events")
async def realtime_event(
    session_id: str,
    body: RealtimeEventBody,
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    event = session.append(body.type, body.text)
    return {"event": event.to_dict(), "session": session.to_dict()}


@router.get("/realtime/sessions/{session_id}/transcript")
async def realtime_transcript(session_id: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"transcript": session.transcript()}
