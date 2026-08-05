"""TUI slash exec, completion, and command dispatch HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.api.command_dispatch import dispatch_command, should_fallthrough_to_dispatch
from keprix.auth.dependencies import get_current_user
from keprix.slash.executor import build_context, execute_context
from keprix.slash.parser import parse_slash
from keprix.slash.registry import get_slash_registry
from keprix.tui.slash_registry import (
    local_completion_candidates,
    local_command_names,
    slash_command_metadata,
)
from keprix.workspace.repository import NotFoundError, workspace_repo

router = APIRouter(tags=["tui-slash"])

PAGER_LINE_THRESHOLD = 40


class SlashExecBody(BaseModel):
    command: str
    session_id: str = ""
    platform: str = "tui"


class SlashCompleteBody(BaseModel):
    prefix: str
    session_id: str = ""


class CommandDispatchBody(BaseModel):
    name: str
    arg: str = ""
    session_id: str = ""


def _user_id(user: dict[str, Any]) -> str:
    return str(user.get("id") or user.get("username") or "tui")


def _role_from_user(user: dict[str, Any]) -> str:
    role = str(user.get("role") or "admin")
    return role if role in {"viewer", "operator", "admin"} else "admin"


def _slash_text(raw: str) -> str:
    text = raw.strip()
    if not text:
        return text
    return text if text.startswith("/") else f"/{text}"


def _completion_candidates(prefix: str, role: str) -> list[str]:
    candidates = local_completion_candidates(prefix)
    needle = prefix.strip().lower()
    if not needle.startswith("/"):
        return candidates
    registry = get_slash_registry()
    for command in registry.list_for_role(role):
        for candidate in (f"/{command.name}", command.usage):
            if candidate.lower().startswith(needle) and candidate not in candidates:
                candidates.append(candidate)
        for alias in command.aliases:
            alias_text = f"/{alias}"
            if alias_text.lower().startswith(needle) and alias_text not in candidates:
                candidates.append(alias_text)
    try:
        from agent.skill_commands import get_skill_commands

        for key in sorted(get_skill_commands().keys()):
            if key.lower().startswith(needle) and key not in candidates:
                candidates.append(key)
    except Exception:
        pass
    return sorted(set(candidates))


@router.post("/api/slash/exec")
async def slash_exec(
    body: SlashExecBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    command = body.command.strip()
    if not command:
        raise HTTPException(status_code=400, detail={"error": "command_required"})
    if should_fallthrough_to_dispatch(command):
        return {"ok": False, "fallthrough": True, "output": ""}

    raw = _slash_text(command)
    first = parse_slash(raw, get_slash_registry().names()).command or ""
    # LOCAL_SLASH_COMMANDS includes backend-handled names (e.g. /status). Only
    # short-circuit when the override still marks the command as local.
    local_names = {name.lstrip("/").lower() for name in local_command_names()}
    if first.lower() in local_names:
        meta = slash_command_metadata(f"/{first}")
        if meta is None or meta.source != "backend":
            return {"ok": False, "local": True, "output": ""}

    ctx = build_context(
        raw_text=raw,
        user_id=_user_id(user),
        workspace_id="default",
        channel="tui",
        channel_user_id=_user_id(user),
        metadata={"session_id": body.session_id, "platform": body.platform},
        role=_role_from_user(user),
    )
    result = await execute_context(ctx)
    output = result.message.strip()
    if result.blocks:
        block_lines = [str(block.get("text") or "") for block in result.blocks if isinstance(block, dict)]
        block_text = "\n".join(line for line in block_lines if line).strip()
        if block_text:
            output = block_text if not output else f"{output}\n{block_text}"
    line_count = output.count("\n") + 1 if output else 0
    pager = line_count > PAGER_LINE_THRESHOLD
    if not result.ok and result.message and "Unknown command" in result.message:
        return {"ok": False, "fallthrough": True, "output": output}
    return {"ok": result.ok, "output": output, "pager": pager}


@router.post("/api/slash/complete")
async def slash_complete(
    body: SlashCompleteBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    role = _role_from_user(user)
    candidates = _completion_candidates(body.prefix, role)
    return {"candidates": candidates}


@router.post("/api/command/dispatch")
async def command_dispatch_route(
    body: CommandDispatchBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    messages: list[dict[str, Any]] = []
    if body.session_id:
        try:
            session = workspace_repo.get_session(user, body.session_id)
            messages = list(session.get("messages") or [])
        except NotFoundError:
            messages = []
    payload = await dispatch_command(
        name=body.name,
        arg=body.arg,
        session_id=body.session_id,
        messages=messages,
    )
    if not payload.get("ok", True):
        raise HTTPException(
            status_code=404 if payload.get("code") == 4040 else 400,
            detail={"error": payload.get("error"), "code": payload.get("code")},
        )
    return payload
