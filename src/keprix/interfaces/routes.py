"""Agent platform interface routes."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from keprix.interfaces.ag_ui_adapter import serialize_ag_ui_stream
from keprix.interfaces.interface_registry import InterfaceKind, get_interface_registry
from keprix.public_api.auth import require_developer_session

router = APIRouter(prefix="/api/interfaces", tags=["interfaces"])


class BindBody(BaseModel):
    agent_id: str
    kinds: list[str] = Field(default_factory=lambda: ["web_ui", "api", "telegram"])


class DispatchBody(BaseModel):
    agent_id: str
    kind: str
    message: str = ""
    workspace_id: str = "default"
    user_id: str = "local"
    payload: dict[str, Any] = Field(default_factory=dict)


@router.post("/bind")
async def bind_agent_interfaces(body: BindBody, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    registry = get_interface_registry()
    kinds = []
    for value in body.kinds:
        try:
            kinds.append(InterfaceKind(value))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"unknown interface kind: {value}") from exc
    bindings = registry.bind_agent(body.agent_id, kinds)
    return {"agent_id": body.agent_id, "interfaces": [binding.kind.value for binding in bindings]}


@router.get("/agents/{agent_id}")
async def list_agent_interfaces(agent_id: str, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    registry = get_interface_registry()
    return {"agent_id": agent_id, "interfaces": registry.supported_kinds(agent_id)}


@router.post("/dispatch")
async def dispatch_interface(
    body: DispatchBody,
    _session: str = Depends(require_developer_session),
    x_trace_id: str | None = Header(default=None),
) -> dict[str, Any]:
    registry = get_interface_registry()
    try:
        kind = InterfaceKind(body.kind)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"unknown interface kind: {body.kind}") from exc
    trace_id = x_trace_id or str(uuid.uuid4())
    result = await registry.dispatch(
        body.agent_id,
        kind,
        trace_id=trace_id,
        message=body.message,
        text=body.message,
        user_id=body.user_id,
        workspace_id=body.workspace_id,
        **body.payload,
    )
    response: dict[str, Any] = {
        "ok": result.ok,
        "trace_id": result.trace_id,
        "channel": result.channel,
        "payload": result.payload,
        "error": result.error,
    }
    if kind == InterfaceKind.AG_UI and result.ok:
        response["stream"] = serialize_ag_ui_stream(result.payload.get("events", []))
    return response
