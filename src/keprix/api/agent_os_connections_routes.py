"""Agent OS connections tier matrix API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.agent_os.connections_service import ConnectionsService
from keprix.agent_os.connections_templates import VALID_STATUSES
from keprix.agent_os.onboarding_events import record_onboarding_event_for_user
from keprix.agent_os.workflow_audit_service import agent_os_enabled
from keprix.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/agent-os/connections", tags=["agent-os"])


class WorkspaceBody(BaseModel):
    workspace_id: str = "personal-os"
    workspace_path: str | None = None


class InitBody(WorkspaceBody):
    seed_tools: list[str] = Field(default_factory=list)


class UpdateBody(WorkspaceBody):
    domain: str
    status: str
    tools: list[str] | None = None
    integration_ref: str | None = None
    service_account: bool | None = None
    notes: str | None = None


def _guard_enabled() -> None:
    if not agent_os_enabled():
        raise HTTPException(status_code=403, detail="Agent OS is disabled")


@router.get("")
async def get_connections(workspace_id: str = "personal-os", workspace_path: str | None = None, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _guard_enabled()
    domains = ConnectionsService().load(workspace_id=workspace_id, workspace_path=workspace_path)
    return {"domains": [domain.to_dict() for domain in domains]}


@router.post("/init-template")
async def init_connections(body: InitBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _guard_enabled()
    return ConnectionsService().init_template(workspace_id=body.workspace_id, workspace_path=body.workspace_path, seed_tools=body.seed_tools)


@router.put("")
async def update_connections(body: UpdateBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {sorted(VALID_STATUSES)}")
    try:
        result = ConnectionsService().update_domain(
            body.domain,
            status=body.status,
            tools=body.tools,
            integration_ref=body.integration_ref,
            service_account=body.service_account,
            notes=body.notes,
            workspace_id=body.workspace_id,
            workspace_path=body.workspace_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if body.status == "live":
        record_onboarding_event_for_user(user, "connections.domain_live")
    return result


@router.post("/suggest-priority")
async def suggest_connections(body: WorkspaceBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _guard_enabled()
    return {"suggestions": ConnectionsService().suggest_priority(workspace_id=body.workspace_id, workspace_path=body.workspace_path)}
