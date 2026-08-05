"""Authenticated API for GitHub agent-sync bridge."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.sync.github_bridge import (
    GithubBridgeScope,
    get_status,
    pull_now,
    push_approved_durable_updates,
    rebuild_index,
    resolve_github_bridge_scope,
    search_shared_knowledge,
    start_github_bridge_schedule,
    update_settings,
    write_durable_note,
)

router = APIRouter(prefix="/api/agent-sync", tags=["agent-sync"])


class SettingsBody(BaseModel):
    scope_kind: str | None = Field(default=None, alias="scopeKind")
    scope_id: str | None = Field(default=None, alias="scopeId")
    enabled: bool | None = None
    owner: str | None = None
    repo: str | None = None
    branch: str | None = None
    pull_interval_minutes: int | None = Field(default=None, alias="pullIntervalMinutes")
    push_interval_minutes: int | None = Field(default=None, alias="pushIntervalMinutes")
    allowed_folders: list[str] | None = Field(default=None, alias="allowedFolders")
    human_edits_win: bool | None = Field(default=None, alias="humanEditsWin")
    product: str | None = None
    local_path: str | None = Field(default=None, alias="localPath")
    token: str | None = None

    model_config = {"populate_by_name": True}


class PushBody(BaseModel):
    message: str | None = None
    paths: list[str] | None = None
    scope_kind: str | None = Field(default=None, alias="scopeKind")
    scope_id: str | None = Field(default=None, alias="scopeId")

    model_config = {"populate_by_name": True}


class NoteBody(BaseModel):
    path: str
    content: str
    push: bool = True
    scope_kind: str | None = Field(default=None, alias="scopeKind")
    scope_id: str | None = Field(default=None, alias="scopeId")

    model_config = {"populate_by_name": True}


class SearchBody(BaseModel):
    query: str
    limit: int = 8
    product: str | None = None
    agent: str | None = None
    path_prefix: str | None = Field(default=None, alias="pathPrefix")
    scope_kind: str | None = Field(default=None, alias="scopeKind")
    scope_id: str | None = Field(default=None, alias="scopeId")

    model_config = {"populate_by_name": True}


def _scope_from_user(
    user: dict[str, Any],
    *,
    scope_kind: str | None = None,
    scope_id: str | None = None,
) -> GithubBridgeScope:
    kind = scope_kind if scope_kind in {"workspace", "user", "shared"} else "workspace"
    return GithubBridgeScope(
        scope_kind=kind,  # type: ignore[arg-type]
        scope_id=scope_id,
        workspace_id=str(user.get("workspace_id") or "default"),
        user_id=str(user.get("id") or user.get("username") or "default"),
    )


@router.get("/status")
async def agent_sync_status(
    scopeKind: str | None = None,
    scopeId: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    return get_status(_scope_from_user(user, scope_kind=scopeKind, scope_id=scopeId))


@router.put("/settings")
async def agent_sync_settings(body: SettingsBody, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    scope = _scope_from_user(user, scope_kind=body.scope_kind, scope_id=body.scope_id)
    status = update_settings(body.model_dump(by_alias=False, exclude_unset=True), scope)
    try:
        start_github_bridge_schedule()
    except Exception:
        pass
    return status


@router.post("/pull")
async def agent_sync_pull(
    scopeKind: str | None = None,
    scopeId: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    return pull_now(_scope_from_user(user, scope_kind=scopeKind, scope_id=scopeId))


@router.post("/push")
async def agent_sync_push(body: PushBody, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    scope = _scope_from_user(user, scope_kind=body.scope_kind, scope_id=body.scope_id)
    return push_approved_durable_updates({"message": body.message, "paths": body.paths}, scope)


@router.post("/index")
async def agent_sync_index(
    scopeKind: str | None = None,
    scopeId: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    scope = _scope_from_user(user, scope_kind=scopeKind, scope_id=scopeId)
    count = rebuild_index(scope=scope)
    return {"ok": True, "indexed": count}


@router.post("/search")
async def agent_sync_search(body: SearchBody, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    scope = _scope_from_user(user, scope_kind=body.scope_kind, scope_id=body.scope_id)
    hits = search_shared_knowledge(
        body.query,
        body.limit,
        {"product": body.product or "", "agent": body.agent or "", "path_prefix": body.path_prefix or ""},
        scope,
    )
    return {"hits": hits}


@router.post("/note")
async def agent_sync_note(body: NoteBody, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    scope = _scope_from_user(user, scope_kind=body.scope_kind, scope_id=body.scope_id)
    return write_durable_note(relative_path=body.path, content=body.content, push=body.push, scope=scope)


@router.get("/scope")
async def agent_sync_scope_debug(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return resolve_github_bridge_scope(_scope_from_user(user))
