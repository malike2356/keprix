"""Control center HTTP routes (Prompt 61)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.control_center.activity_feed import list_approvals, list_recent_artifacts, recent_activity
from keprix.control_center.agent_server_registry import get_server, list_servers, record_heartbeat, register_server
from keprix.control_center.automation_server import dispatch_automation, list_automations
from keprix.control_center.event_triggers import create_webhook_automation, trigger_from_webhook
from keprix.control_center.remote_agent_client import ping_health
from keprix.control_center.run_queue import fail_run, list_queue, public_run, start_run
from keprix.control_center.queue_worker import process_queued_runs
from keprix.control_center.scheduled_runs import create_scheduled_automation
from keprix.control_center.store import get_control_center_store
from keprix.control_center.workspace_sessions import create_session, list_sessions, update_session_status

router = APIRouter(prefix="/api/control-center", tags=["control-center"])


class RegisterServerBody(BaseModel):
    name: str
    url: str = "http://127.0.0.1:8000"
    workspace_root: str
    token: str | None = None
    capabilities: list[str] = Field(default_factory=lambda: ["coding", "research", "playbook"])
    sandbox_status: str = "enabled"


class CreateSessionBody(BaseModel):
    server_id: str
    task_type: str = "playbook"
    objective: str
    playbook_id: str | None = None
    repo_path: str | None = None
    workspace_id: str = "default"


class SessionStatusBody(BaseModel):
    status: str


class ScheduleAutomationBody(BaseModel):
    name: str
    playbook_id: str
    schedule_cron: str = "0 9 * * *"
    server_id: str | None = None
    enabled: bool = True


class WebhookAutomationBody(BaseModel):
    name: str
    playbook_id: str
    server_id: str | None = None


def _owner(user: dict) -> str:
    return str(user.get("id") or user.get("username") or "admin")


@router.get("/dashboard")
async def control_center_dashboard(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    queue = list_queue()
    failed = [item for item in queue if item.get("status") == "failed"]
    active_sessions = list_sessions(status="active")
    return {
        "servers": list_servers(),
        "active_sessions": active_sessions,
        "queued_runs": [item for item in queue if item.get("status") == "queued"],
        "failed_runs": failed,
        "automations": list_automations(),
        "approvals": list_approvals(status="pending"),
        "recent_artifacts": list_recent_artifacts(limit=10),
        "activity": recent_activity(limit=20),
    }


@router.get("/servers")
async def get_servers(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"servers": list_servers()}


@router.post("/servers")
async def post_server(body: RegisterServerBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        server = await register_server(
            name=body.name,
            url=body.url,
            owner=_owner(user),
            workspace_root=body.workspace_root,
            token=body.token,
            capabilities=body.capabilities,
            sandbox_status=body.sandbox_status,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"server": server}


@router.post("/servers/{server_id}/heartbeat")
async def server_heartbeat(server_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    server = get_server(server_id)
    if server is None:
        raise HTTPException(status_code=404, detail="Server not found")
    raw = get_control_center_store().get_server(server_id)
    health = await ping_health(raw or server, _owner(user))
    status = health.get("status", "unknown")
    updated = record_heartbeat(server_id, health_status=str(status))
    return {"server": updated, "health": health}


@router.get("/sessions")
async def get_sessions(status: str | None = None, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"sessions": list_sessions(status=status)}


@router.post("/sessions")
async def post_session(body: CreateSessionBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        session = create_session(
            server_id=body.server_id,
            task_type=body.task_type,  # type: ignore[arg-type]
            objective=body.objective,
            playbook_id=body.playbook_id,
            owner=_owner(user),
            repo_path=body.repo_path,
            workspace_id=body.workspace_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"session": session}


@router.patch("/sessions/{session_id}")
async def patch_session(
    session_id: str,
    body: SessionStatusBody,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    session = update_session_status(session_id, body.status)  # type: ignore[arg-type]
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session}


@router.post("/queue/process")
async def process_queue(limit: int = 5, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    results = await process_queued_runs(limit=limit)
    return {"processed": results}


@router.get("/queue")
async def get_queue(status: str | None = None, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"queue": list_queue(status=status)}


@router.get("/automations")
async def get_automations(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"automations": list_automations()}


@router.post("/automations/schedule")
async def post_scheduled_automation(
    body: ScheduleAutomationBody,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    automation = create_scheduled_automation(
        name=body.name,
        playbook_id=body.playbook_id,
        schedule_cron=body.schedule_cron,
        server_id=body.server_id,
        enabled=body.enabled,
    )
    return {"automation": automation}


@router.post("/automations/webhook")
async def post_webhook_automation(
    body: WebhookAutomationBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    result = await create_webhook_automation(
        name=body.name,
        playbook_id=body.playbook_id,
        owner=_owner(user),
        server_id=body.server_id,
    )
    return result


@router.post("/automations/{automation_id}/trigger")
async def trigger_automation(automation_id: str, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    run = dispatch_automation(automation_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Automation not found")
    started = start_run(run["id"]) or run
    return {"run": public_run(started)}


@router.post("/webhooks/{automation_id}")
async def webhook_trigger(
    automation_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    body = await request.body()
    signature = request.headers.get("X-Keprix-Signature") or request.headers.get("X-Hub-Signature-256")
    try:
        run = await trigger_from_webhook(
            automation_id,
            body=body,
            signature_header=signature,
            owner=_owner(user),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    started = start_run(run["id"]) or run
    return {"run": public_run(started)}


@router.get("/activity")
async def get_activity(limit: int = 50, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"activity": recent_activity(limit=limit)}


@router.get("/approvals")
async def get_approvals(status: str | None = None, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"approvals": list_approvals(status=status)}


@router.get("/artifacts")
async def get_artifacts(limit: int = 20, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"artifacts": list_recent_artifacts(limit=limit)}


@router.get("/runs/{run_id}")
async def get_run(run_id: str, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    item = get_control_center_store().get_queue_item(run_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"run": public_run(item)}


@router.post("/runs/{run_id}/fail")
async def mark_run_failed(run_id: str, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    run = fail_run(run_id, logs=["Marked failed by operator"])
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"run": run}
