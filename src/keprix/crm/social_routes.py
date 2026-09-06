"""Social channel routes (prompt 06). Decision-gated; refuses outbound until approved."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from keprix.auth.dependencies import get_current_user
from keprix.crm import social_channels as sc
from keprix.crm.roles import require_cap
from keprix.crm.routes import _workspace
from keprix.crm.store import get_crm_store

router = APIRouter(prefix="/api/crm/social", tags=["crm-social"])


class ConnectBody(BaseModel):
    channel: str
    provider_account_id: str = ""


class DiscoverBody(BaseModel):
    channel: str
    query: str = ""
    limit: int = 25


class SendRequestBody(BaseModel):
    channel: str
    provider_lead_id: str


class SendMessageBody(BaseModel):
    channel: str
    provider_lead_id: str
    body: str


class EventBody(BaseModel):
    channel: str
    provider_event_id: str
    event_type: str
    payload: dict[str, Any] = {}


def _ws(workspace_id, x_workspace_id, user):
    return _workspace(workspace_id, x_workspace_id, user)


@router.get("/providers")
async def providers(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    require_cap(user, "view")
    return {"ok": True, "providers": sc.PROVIDERS}


@router.post("/connect")
async def connect(
    body: ConnectBody,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    store = get_crm_store()
    ws = _ws(workspace_id, x_workspace_id, user)
    if body.channel not in sc.PROVIDERS:
        raise HTTPException(status_code=422, detail="unknown channel")
    return sc.connect_channel(store, ws, body.channel, provider_account_id=body.provider_account_id)


@router.get("/connections")
async def connections(
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    store = get_crm_store()
    ws = _ws(workspace_id, x_workspace_id, user)
    return {"ok": True, "items": sc.list_connections(store, ws)}


@router.post("/discover")
async def discover(
    body: DiscoverBody, user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    require_cap(user, "view")
    return sc.discover_leads(body.channel, {"query": body.query}, limit=body.limit)


@router.post("/send-request")
async def send_request(
    body: SendRequestBody, user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    require_cap(user, "edit")
    return sc.send_connection_request(body.channel, body.provider_lead_id)


@router.post("/send-message")
async def send_message(
    body: SendMessageBody, user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    require_cap(user, "edit")
    return sc.send_message(body.channel, body.provider_lead_id, body.body)


@router.post("/events")
async def record_event(
    body: EventBody,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    store = get_crm_store()
    ws = _ws(workspace_id, x_workspace_id, user)
    return sc.record_social_event(
        store, ws, body.channel, body.provider_event_id, body.event_type, body.payload
    )
