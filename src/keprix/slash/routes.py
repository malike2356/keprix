"""Slash command HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from keprix.public_api.auth import require_developer_session
from keprix.slash.audit import get_slash_audit_store
from keprix.slash.executor import approve_token, build_context, cancel_token, execute_context
from keprix.slash.parser import parse_slash
from keprix.slash.permissions import normalize_role
from keprix.slash.registry import get_slash_registry
from keprix.slash.schemas import SlashResult

router = APIRouter(prefix="/api/slash", tags=["slash"])


class ParseBody(BaseModel):
    text: str


class ExecuteBody(BaseModel):
    text: str
    channel: str = "webchat"
    user_id: str = "local"
    workspace_id: str = "default"
    channel_user_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    skip_confirmation: bool = False


class TokenBody(BaseModel):
    token: str
    channel: str = "webchat"
    user_id: str = "local"
    workspace_id: str = "default"
    channel_user_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def _role_from_headers(x_slash_role: str | None = Header(default=None)) -> str:
    return normalize_role(x_slash_role or "admin")


@router.get("/commands")
async def list_commands(
    _session: str = Depends(require_developer_session),
    x_slash_role: str | None = Header(default=None),
) -> dict[str, Any]:
    role = normalize_role(x_slash_role or "admin")
    commands = get_slash_registry().list_for_role(role)
    return {
        "commands": [
            {
                "name": command.name,
                "aliases": command.aliases,
                "description": command.description,
                "usage": command.usage,
                "category": command.category,
                "min_role": command.min_role,
                "requires_confirmation": command.requires_confirmation,
            }
            for command in commands
        ]
    }


@router.post("/parse")
async def parse_command(
    body: ParseBody,
    _session: str = Depends(require_developer_session),
) -> dict[str, Any]:
    parsed = parse_slash(body.text, get_slash_registry().names())
    return parsed.__dict__


@router.post("/execute")
async def execute_command(
    body: ExecuteBody,
    request: Request,
    _session: str = Depends(require_developer_session),
    x_slash_role: str | None = Header(default=None),
) -> dict[str, Any]:
    ctx = build_context(
        raw_text=body.text,
        user_id=body.user_id,
        workspace_id=body.workspace_id,
        channel=body.channel,
        channel_user_id=body.channel_user_id or body.user_id,
        metadata=body.metadata,
        role=_role_from_headers(x_slash_role),
        request_id=request.headers.get("x-request-id"),
        skip_confirmation=body.skip_confirmation,
    )
    result = await execute_context(ctx)
    return _result_payload(result)


@router.post("/approve")
async def approve_command(
    body: TokenBody,
    request: Request,
    _session: str = Depends(require_developer_session),
    x_slash_role: str | None = Header(default=None),
) -> dict[str, Any]:
    ctx = build_context(
        raw_text=f"/approve {body.token}",
        user_id=body.user_id,
        workspace_id=body.workspace_id,
        channel=body.channel,
        channel_user_id=body.channel_user_id or body.user_id,
        metadata=body.metadata,
        role=_role_from_headers(x_slash_role),
        request_id=request.headers.get("x-request-id"),
        confirmation_token=body.token,
    )
    result = await approve_token(ctx, body.token)
    return _result_payload(result)


@router.post("/cancel")
async def cancel_command(
    body: TokenBody,
    request: Request,
    _session: str = Depends(require_developer_session),
    x_slash_role: str | None = Header(default=None),
) -> dict[str, Any]:
    ctx = build_context(
        raw_text=f"/cancel {body.token}",
        user_id=body.user_id,
        workspace_id=body.workspace_id,
        channel=body.channel,
        channel_user_id=body.channel_user_id or body.user_id,
        metadata=body.metadata,
        role=_role_from_headers(x_slash_role),
        request_id=request.headers.get("x-request-id"),
        confirmation_token=body.token,
    )
    result = await cancel_token(ctx, body.token)
    return _result_payload(result)


@router.get("/audit")
async def list_audit(
    workspace_id: str | None = None,
    limit: int = 100,
    _session: str = Depends(require_developer_session),
) -> dict[str, Any]:
    rows = get_slash_audit_store().list_rows(workspace_id=workspace_id, limit=limit)
    return {"audit": rows}


def _result_payload(result: SlashResult) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "message": result.message,
        "blocks": result.blocks,
        "requires_confirmation": result.requires_confirmation,
        "confirmation_token": result.confirmation_token,
        "ephemeral": result.ephemeral,
        "audit_id": result.audit_id,
        "data": result.data,
    }
