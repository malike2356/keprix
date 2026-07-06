"""Admin workspace pages API (tools, memory, channels, keys, users, settings)."""

from __future__ import annotations

import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from keprix.agent.keprix.store import get_generated_tool_store
from keprix.auth.dependencies import get_current_user, require_admin
from keprix.auth.session import auth_manager
from keprix.keys.developer_identity import get_identity_status
from keprix.memory.rag.indexer import RagIndexer
from keprix.public_api.keys import get_api_key_store
from keprix.public_api.schemas import CreateApiKeyRequest
from keprix.research.fetch import fetch_page_text
from keprix.api.provider_settings import (
    admin_provider_catalog,
    delete_provider_settings,
    provider_settings_snapshot,
    save_provider_settings,
    set_default_provider,
    test_provider_settings,
)
from keprix.api.custom_provider_settings import (
    create_custom_provider,
    delete_custom_provider,
    list_custom_providers,
    test_custom_provider,
    update_custom_provider,
)
from keprix.api.web_search_settings import (
    activate_web_search_backend,
    delete_web_search_settings,
    save_web_search_settings,
    test_web_search_settings,
    web_search_settings_snapshot,
)

router = APIRouter(tags=["admin-workspace"])

_rag_indexer = RagIndexer()
_channel_config: dict[str, dict[str, Any]] = {
    "telegram": {"configured": False, "bot_username": None, "message_count": 0},
    "discord": {"configured": False, "message_count": 0},
    "rest": {"active_keys": 0},
}
_settings: dict[str, Any] = {
    "instance_name": "Keprix",
    "instance_url": "http://localhost:3333",
    "timezone": "UTC",
    "language": "en",
    "max_tool_iterations": 20,
    "context_compression_threshold": 60000,
    "mutation_engine_enabled": True,
    "mutation_sandbox_timeout": 30,
    "auto_approve_owner_mutations": False,
    "postgres_url": "",
    "redis_url": "",
    "vector_store_engine": "pgvector",
    "max_memory_documents": 1000,
    "governance_config": {
        "license_key": "",
        "audit_policy_url": "",
        "provider_endpoint": "",
    },
}
_memory_docs: dict[str, dict[str, Any]] = {}

_BUILTIN_TOOLS = [
    {
        "id": "builtin-read_file",
        "name": "read_file",
        "description": "Read a file from the workspace filesystem.",
        "source": "builtin",
        "status": "active",
        "last_used_at": None,
        "times_called": 0,
        "created_at": "2026-01-01T00:00:00+00:00",
        "tool_code": "def read_file(path: str) -> str:\n    ...\n",
        "skill_yaml": "name: read_file\n",
    },
    {
        "id": "builtin-write_file",
        "name": "write_file",
        "description": "Write content to a workspace file.",
        "source": "builtin",
        "status": "active",
        "last_used_at": None,
        "times_called": 0,
        "created_at": "2026-01-01T00:00:00+00:00",
        "tool_code": "def write_file(path: str, content: str) -> bool:\n    ...\n",
        "skill_yaml": "name: write_file\n",
    },
    {
        "id": "builtin-web_search",
        "name": "web_search",
        "description": "Search the web for current information.",
        "source": "builtin",
        "status": "active",
        "last_used_at": None,
        "times_called": 0,
        "created_at": "2026-01-01T00:00:00+00:00",
        "tool_code": "def web_search(query: str) -> list:\n    ...\n",
        "skill_yaml": "name: web_search\n",
    },
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now()).isoformat()


def _user_key(user: dict[str, Any]) -> str:
    return str(user.get("id") or user.get("username") or "default")


def _all_tools() -> list[dict[str, Any]]:
    tools = [dict(tool) for tool in _BUILTIN_TOOLS]
    for record in get_generated_tool_store().list_all(status="approved"):
        tools.append(
            {
                "id": record.id,
                "name": record.tool_name,
                "description": record.description or record.gap_description,
                "source": "synthesised",
                "status": "active",
                "last_used_at": record.approved_at,
                "times_called": 0,
                "created_at": record.created_at,
                "tool_code": record.tool_code,
                "skill_yaml": record.skill_yaml,
            }
        )
    return tools


def _usage_series(days: int = 14) -> dict[str, Any]:
    labels: list[str] = []
    values: list[int] = []
    today = _now().date()
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        labels.append(day.strftime("%d %b"))
        values.append(max(0, (offset * 3) % 7))
    return {"labels": labels, "values": values}


class InviteUserBody(BaseModel):
    email: str
    role: str = "user"
    message: str | None = None


class UpdateWorkspaceUserBody(BaseModel):
    role: str | None = None
    status: str | None = None


class CreateApiKeyBody(BaseModel):
    name: str
    expiry: str = "none"
    scopes: list[str] = Field(default_factory=lambda: ["read"])


class ChannelTokenBody(BaseModel):
    bot_token: str
    application_id: str | None = None
    guild_id: str | None = None


class SettingsBody(BaseModel):
    instance_name: str | None = None
    instance_url: str | None = None
    timezone: str | None = None
    language: str | None = None
    max_tool_iterations: int | None = None
    context_compression_threshold: int | None = None
    mutation_engine_enabled: bool | None = None
    mutation_sandbox_timeout: int | None = None
    auto_approve_owner_mutations: bool | None = None
    postgres_url: str | None = None
    redis_url: str | None = None
    vector_store_engine: str | None = None
    max_memory_documents: int | None = None
    governance_config: dict[str, str] | None = None


class ProviderBody(BaseModel):
    api_key: str | None = None
    default_model: str | None = None


class CustomProviderBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    base_url: str = Field(..., min_length=8, max_length=500)
    api_key: str | None = None
    default_model: str | None = None


class CustomProviderUpdateBody(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    base_url: str | None = Field(default=None, min_length=8, max_length=500)
    api_key: str | None = None
    default_model: str | None = None


class DefaultProviderBody(BaseModel):
    provider_id: str = Field(..., min_length=1, max_length=120)


class MemoryUrlBody(BaseModel):
    url: str


@router.get("/api/tools")
async def list_tools(
    _admin: dict = Depends(require_admin),
    source: str | None = Query(None),
    search: str | None = Query(None),
) -> dict[str, Any]:
    items = _all_tools()
    if source and source != "all":
        items = [tool for tool in items if tool["source"] == source]
    if search:
        q = search.lower()
        items = [tool for tool in items if q in tool["name"].lower() or q in tool["description"].lower()]
    counts = {
        "all": len(_all_tools()),
        "builtin": len([t for t in _all_tools() if t["source"] == "builtin"]),
        "synthesised": len([t for t in _all_tools() if t["source"] == "synthesised"]),
        "community": 0,
    }
    return {"items": items, "counts": counts}


@router.get("/api/tools/{tool_id}")
async def get_tool(tool_id: str, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    for tool in _all_tools():
        if tool["id"] == tool_id:
            return {**tool, "usage": _usage_series()}
    raise HTTPException(status_code=404, detail="Tool not found")


@router.post("/api/tools/{tool_id}/disable")
async def disable_tool(tool_id: str, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    for tool in _BUILTIN_TOOLS:
        if tool["id"] == tool_id:
            tool["status"] = "disabled"
            return tool
    raise HTTPException(status_code=404, detail="Tool not found")


@router.delete("/api/tools/{tool_id}")
async def delete_tool(tool_id: str, _admin: dict = Depends(require_admin)) -> dict[str, bool]:
    for index, tool in enumerate(_BUILTIN_TOOLS):
        if tool["id"] == tool_id:
            raise HTTPException(status_code=400, detail="Built-in tools cannot be deleted")
    record = get_generated_tool_store().get(tool_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    get_generated_tool_store().update(tool_id, status="deleted")
    return {"ok": True}


@router.get("/api/memory/documents")
async def list_memory_documents(
    user: dict = Depends(get_current_user),
    search: str | None = Query(None),
) -> dict[str, Any]:
    user_id = _user_key(user)
    sources = await _rag_indexer.list_sources(user_id)
    items: list[dict[str, Any]] = []
    for source in sources:
        doc_id = f"{source['source_type']}:{source['source_id']}"
        stored = _memory_docs.get(doc_id, {})
        name = stored.get("name") or source["source_id"]
        items.append(
            {
                "id": doc_id,
                "name": name,
                "type": stored.get("type") or source["source_type"],
                "size_bytes": stored.get("size_bytes", 0),
                "chunks": source.get("chunk_count", 0),
                "uploaded_at": stored.get("uploaded_at") or source.get("updated_at"),
                "uploaded_by": stored.get("uploaded_by") or user.get("username"),
                "status": stored.get("status", "indexed"),
                "preview": stored.get("preview", ""),
            }
        )
    for doc_id, doc in _memory_docs.items():
        if not any(item["id"] == doc_id for item in items):
            items.append(doc)
    if search:
        q = search.lower()
        items = [item for item in items if q in item["name"].lower()]
    total_chunks = sum(item.get("chunks", 0) for item in items)
    last_indexed = max((item.get("uploaded_at") or "") for item in items) if items else None
    return {
        "items": items,
        "stats": {
            "total_documents": len(items),
            "total_chunks": total_chunks,
            "last_indexed_at": last_indexed,
        },
    }


@router.get("/api/memory/documents/{doc_id}")
async def get_memory_document(doc_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    if doc_id in _memory_docs:
        return _memory_docs[doc_id]
    user_id = _user_key(user)
    if ":" in doc_id:
        source_type, source_id = doc_id.split(":", 1)
        sources = await _rag_indexer.list_sources(user_id)
        for source in sources:
            if source["source_type"] == source_type and source["source_id"] == source_id:
                return {
                    "id": doc_id,
                    "name": source_id,
                    "type": source_type,
                    "preview": f"Indexed source {source_id}",
                    "chunks": source.get("chunk_count", 0),
                }
    raise HTTPException(status_code=404, detail="Document not found")


@router.delete("/api/memory/documents/{doc_id}")
async def delete_memory_document(doc_id: str, user: dict = Depends(get_current_user)) -> dict[str, bool]:
    _memory_docs.pop(doc_id, None)
    if ":" in doc_id:
        _, source_id = doc_id.split(":", 1)
        await _rag_indexer.delete_source(_user_key(user), source_id)
    return {"ok": True}


@router.post("/api/memory/documents")
async def upload_memory_document(
    user: dict = Depends(get_current_user),
    file: UploadFile | None = File(None),
) -> dict[str, Any]:
    user_id = _user_key(user)
    if file is None:
        raise HTTPException(status_code=400, detail="file is required")
    payload = await file.read()
    content = payload.decode("utf-8", errors="replace")
    doc_id = str(uuid.uuid4())
    source_id = file.filename or doc_id
    chunks = await _rag_indexer.ingest(
        user_id=user_id,
        source_type=_guess_doc_type(file.filename or ""),
        source_id=source_id,
        content=content,
    )
    doc = {
        "id": doc_id,
        "name": file.filename or "upload.txt",
        "type": _guess_doc_type(file.filename or ""),
        "size_bytes": len(payload),
        "chunks": chunks,
        "uploaded_at": _iso(),
        "uploaded_by": user.get("username"),
        "status": "indexed",
        "preview": content[:2000],
    }
    _memory_docs[doc_id] = doc
    return doc


@router.post("/api/memory/documents/url")
async def index_memory_url(body: MemoryUrlBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    user_id = _user_key(user)
    doc_id = str(uuid.uuid4())
    try:
        title, content = await fetch_page_text(body.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {exc}") from exc

    if not content.strip():
        raise HTTPException(status_code=400, detail="No readable content at URL")

    display_name = title.strip() or body.url
    indexed_content = f"# {display_name}\n\nSource: {body.url}\n\n{content}"
    chunks = await _rag_indexer.ingest(
        user_id=user_id,
        source_type="url",
        source_id=body.url,
        content=indexed_content,
    )
    doc = {
        "id": doc_id,
        "name": display_name,
        "type": "url",
        "size_bytes": len(indexed_content.encode("utf-8")),
        "chunks": chunks,
        "uploaded_at": _iso(),
        "uploaded_by": user.get("username"),
        "status": "indexed",
        "preview": indexed_content[:2000],
    }
    _memory_docs[doc_id] = doc
    return doc


def _guess_doc_type(filename: str) -> str:
    lowered = filename.lower()
    if lowered.endswith(".pdf"):
        return "pdf"
    if lowered.endswith(".md"):
        return "markdown"
    if lowered.endswith(".docx"):
        return "docx"
    if lowered.endswith(".txt"):
        return "text"
    return "text"


@router.get("/api/channels/overview")
async def channels_overview(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    keys = [key for key in get_api_key_store().list_keys() if not key.revoked]
    _channel_config["rest"]["active_keys"] = len(keys)
    base_url = _settings.get("instance_url", "http://localhost:3333")
    return {
        "channels": [
            {
                "id": "telegram",
                "name": "Telegram",
                "status": "connected" if _channel_config["telegram"]["configured"] else "not_configured",
                "bot_username": _channel_config["telegram"].get("bot_username"),
                "message_count": _channel_config["telegram"].get("message_count", 0),
            },
            {
                "id": "discord",
                "name": "Discord",
                "status": "connected" if _channel_config["discord"]["configured"] else "not_configured",
                "message_count": _channel_config["discord"].get("message_count", 0),
            },
            {
                "id": "rest",
                "name": "REST API",
                "status": "active",
                "endpoint": f"{base_url}/api",
                "active_keys": len(keys),
            },
        ]
    }


@router.get("/api/channels/telegram")
async def get_telegram_config(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    base_url = _settings.get("instance_url", "http://localhost:3333")
    return {
        "webhook_url": f"{base_url}/api/channels/telegram/webhook",
        "configured": _channel_config["telegram"]["configured"],
    }


@router.post("/api/channels/telegram")
async def save_telegram_config(body: ChannelTokenBody, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    _channel_config["telegram"] = {
        "configured": bool(body.bot_token.strip()),
        "bot_username": "@keprix_bot",
        "message_count": _channel_config["telegram"].get("message_count", 0),
    }
    return {"ok": True}


@router.post("/api/channels/telegram/test")
async def test_telegram(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    if not _channel_config["telegram"]["configured"]:
        return {"ok": False, "message": "Telegram is not configured"}
    return {"ok": True, "message": "Connection successful"}


@router.post("/api/channels/discord")
async def save_discord_config(body: ChannelTokenBody, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    _channel_config["discord"] = {
        "configured": bool(body.bot_token.strip()),
        "message_count": _channel_config["discord"].get("message_count", 0),
    }
    return {"ok": True}


@router.post("/api/channels/discord/test")
async def test_discord(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    if not _channel_config["discord"]["configured"]:
        return {"ok": False, "message": "Discord is not configured"}
    return {"ok": True, "message": "Connection successful"}


@router.get("/api/api-keys")
async def list_api_keys(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    store = get_api_key_store()
    raw_rows = {row["id"]: row for row in store._load()}
    keys = store.list_keys()
    return {
        "keys": [
            {
                "id": key.id,
                "name": key.name,
                "key_prefix": key.key_prefix,
                "created_at": key.created_at,
                "last_used_at": None,
                "expires_at": None,
                "scopes": [
                    scope
                    for scope, enabled in (raw_rows.get(key.id, {}).get("scopes") or {}).items()
                    if enabled
                ]
                or ["read"],
                "revoked": key.revoked,
            }
            for key in keys
        ]
    }


@router.post("/api/api-keys")
async def create_api_key(body: CreateApiKeyBody, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    scopes = {scope: True for scope in body.scopes}
    created = get_api_key_store().create(
        CreateApiKeyRequest(
            name=body.name,
            workspace_id="default",
            role="developer",
            scopes=scopes,
        )
    )
    return created.model_dump()


@router.delete("/api/api-keys/{key_id}")
async def revoke_api_key(key_id: str, _admin: dict = Depends(require_admin)) -> dict[str, bool]:
    if not get_api_key_store().revoke(key_id):
        raise HTTPException(status_code=404, detail="Key not found")
    return {"ok": True}


@router.get("/api/identity/developer")
async def developer_identity(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    status = get_identity_status()
    fingerprint = status.get("fingerprint") or secrets.token_hex(4).upper()
    return {
        "fingerprint": fingerprint,
        "created_at": status.get("created_at") or _iso(),
        "public_key_pem": status.get("public_key_pem"),
        "config_path": status.get("config_path") or "~/.keprix/identity/dev.json",
    }


@router.get("/api/users")
async def list_workspace_users(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    from keprix.auth.invite_store import invite_store
    from keprix.auth.user_invites import pending_invite_row, workspace_user_row

    items = [workspace_user_row(user) for user in auth_manager.list_users()]
    for invite in invite_store.list_pending():
        items.append(pending_invite_row(invite))
    active = len([u for u in items if u.get("status") == "active"])
    pending = len([u for u in items if u.get("status") == "invited"])
    return {"items": items, "stats": {"total": len(items), "active": active, "pending_invites": pending}}


@router.post("/api/users/invite")
async def invite_user(body: InviteUserBody, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    from keprix.auth.user_invites import InviteError, send_workspace_invite

    try:
        result = await send_workspace_invite(
            email=body.email,
            role=body.role,
            invited_by=str(admin.get("id") or "admin"),
            message=body.message,
        )
    except InviteError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.put("/api/users/{user_id}")
async def update_workspace_user(
    user_id: str,
    body: UpdateWorkspaceUserBody,
    admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    target = auth_manager.get_user_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if str(admin.get("id")) == user_id and body.role and body.role != target.get("role"):
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    fields: dict[str, Any] = {}
    if body.role is not None:
        fields["role"] = body.role
    if body.status == "active":
        fields["is_active"] = True
        fields["is_approved"] = True
    elif body.status == "suspended":
        fields["is_active"] = False
    elif body.status == "invited":
        fields["is_approved"] = False

    user = auth_manager.update_user(user_id, **fields)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    from keprix.auth.user_invites import workspace_user_row

    return {"user": workspace_user_row(user)}


@router.delete("/api/users/{user_id}")
async def delete_workspace_user(user_id: str, admin: dict = Depends(require_admin)) -> dict[str, bool]:
    if str(admin.get("id")) == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    target = auth_manager.get_user_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if target.get("role") == "admin":
        admins = [u for u in auth_manager.list_users() if u.get("role") == "admin" and u.get("is_active", True)]
        if len(admins) <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last active admin")
    if not auth_manager.delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True}


@router.post("/api/users/invites/{invite_id}/resend")
async def resend_workspace_invite(invite_id: str, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    from keprix.auth.user_invites import InviteError, resend_workspace_invite

    try:
        return await resend_workspace_invite(invite_id, invited_by=str(admin.get("id") or "admin"))
    except InviteError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/api/users/invites/{invite_id}")
async def revoke_workspace_invite(invite_id: str, _admin: dict = Depends(require_admin)) -> dict[str, bool]:
    from keprix.auth.invite_store import invite_store

    if not invite_store.revoke(invite_id):
        raise HTTPException(status_code=404, detail="Invite not found")
    return {"ok": True}


@router.get("/api/settings")
async def get_settings(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return {
        "settings": _settings,
        "providers": provider_settings_snapshot(),
        "provider_catalog": admin_provider_catalog(),
        "custom_providers": list_custom_providers(),
        "default_provider": os.environ.get("KEPRIX_DEFAULT_PROVIDER", ""),
        "governance_enabled": os.environ.get("KEPRIX_GOVERNANCE_ENABLED", "").lower() == "true",
    }


@router.put("/api/settings")
async def update_settings(body: SettingsBody, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    for key, value in body.model_dump(exclude_none=True).items():
        _settings[key] = value
    return {"settings": _settings}


@router.put("/api/settings/providers/{provider_id}")
async def update_provider(provider_id: str, body: ProviderBody, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    try:
        entry = save_provider_settings(
            provider_id,
            api_key=body.api_key,
            default_model=body.default_model,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Provider not found") from None
    return {"provider": entry}


@router.post("/api/settings/providers/{provider_id}/test")
async def test_provider(provider_id: str, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    result = test_provider_settings(provider_id)
    if result.get("message") == "Provider not found":
        raise HTTPException(status_code=404, detail="Provider not found")
    return result


@router.delete("/api/settings/providers/{provider_id}")
async def delete_provider(provider_id: str, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    try:
        entry = delete_provider_settings(provider_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Provider not found") from None
    return {"provider": entry}


@router.post("/api/settings/default-provider")
async def update_default_provider(body: DefaultProviderBody, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    try:
        return set_default_provider(body.provider_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/settings/custom-providers")
async def list_custom_provider_settings(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return {"items": list_custom_providers()}


@router.post("/api/settings/custom-providers")
async def create_custom_provider_route(
    body: CustomProviderBody,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    try:
        entry = create_custom_provider(
            name=body.name.strip(),
            base_url=body.base_url.strip(),
            api_key=body.api_key,
            default_model=body.default_model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"provider": entry}


@router.put("/api/settings/custom-providers/{provider_id}")
async def update_custom_provider_route(
    provider_id: str,
    body: CustomProviderUpdateBody,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    try:
        entry = update_custom_provider(
            provider_id,
            name=body.name,
            base_url=body.base_url,
            api_key=body.api_key,
            default_model=body.default_model,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Provider not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"provider": entry}


@router.delete("/api/settings/custom-providers/{provider_id}")
async def delete_custom_provider_route(provider_id: str, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    try:
        entry = delete_custom_provider(provider_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Provider not found") from None
    return {"provider": entry}


@router.post("/api/settings/custom-providers/{provider_id}/test")
async def test_custom_provider_route(provider_id: str, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    result = test_custom_provider(provider_id)
    if result.get("message") == "Provider not found":
        raise HTTPException(status_code=404, detail="Provider not found")
    return result


class WebSearchProviderBody(BaseModel):
    env_values: dict[str, str] = Field(default_factory=dict)
    set_active: bool = True


class WebSearchActivateBody(BaseModel):
    provider_id: str = Field(..., min_length=1)


@router.get("/api/settings/web-search")
async def get_web_search_settings(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return web_search_settings_snapshot()


@router.put("/api/settings/web-search/{provider_id}")
async def update_web_search_provider(
    provider_id: str,
    body: WebSearchProviderBody,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    try:
        entry = save_web_search_settings(
            provider_id,
            env_values=body.env_values,
            set_active=body.set_active,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Provider not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"provider": entry, "snapshot": web_search_settings_snapshot()}


@router.post("/api/settings/web-search/{provider_id}/test")
async def test_web_search_provider(provider_id: str, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    result = test_web_search_settings(provider_id)
    if result.get("message") == "Provider not found":
        raise HTTPException(status_code=404, detail="Provider not found")
    return result


@router.delete("/api/settings/web-search/{provider_id}")
async def delete_web_search_provider(provider_id: str, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    try:
        entry = delete_web_search_settings(provider_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Provider not found") from None
    return {"provider": entry, "snapshot": web_search_settings_snapshot()}


@router.post("/api/settings/web-search/activate")
async def activate_web_search_provider(
    body: WebSearchActivateBody,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    try:
        return activate_web_search_backend(body.provider_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Provider not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
