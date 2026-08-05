"""Channel Shield HTTP API (+ email-shield alias)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from keprix.channel_shield.adapters.registry import adapters_health, get_adapter, list_adapters
from keprix.channel_shield.config import config_to_dict, load_channel_shield_config
from keprix.channel_shield.service import get_channel_shield_service
from keprix.channel_shield.store import get_channel_shield_store
from keprix.channel_shield.types import CHANNELS

router = APIRouter(prefix="/api/channel-shield", tags=["channel-shield"])
email_alias_router = APIRouter(prefix="/api/email-shield", tags=["email-shield"])


def _user_id(request: Request) -> str:
    return (request.headers.get("x-user-id") or "").strip() or "local"


def _is_admin(request: Request) -> bool:
    role = (request.headers.get("x-user-role") or "").strip().lower()
    return role in {"admin", "owner", "superadmin"} or (
        request.headers.get("x-admin") or ""
    ).strip().lower() in {"1", "true", "yes"}


class ProtectionCreate(BaseModel):
    channel: str
    label: str = ""
    protection_key: str
    config: dict[str, Any] = Field(default_factory=dict)


class ProtectionUpdate(BaseModel):
    label: str | None = None
    enabled: bool | None = None
    verified: bool | None = None
    protection_key: str | None = None
    config: dict[str, Any] | None = None


class IngestBody(BaseModel):
    channel: str
    protection_id: str | None = None
    protection_key: str | None = None
    payload: dict[str, Any]


def _ensure_channel(channel: str) -> str:
    if channel not in CHANNELS:
        raise HTTPException(400, f"unsupported channel: {channel}")
    return channel


@router.get("/health")
async def health() -> dict[str, Any]:
    cfg = load_channel_shield_config()
    return {
        "ok": True,
        "enabled": cfg.enabled,
        "adapters": await adapters_health(),
        "config": config_to_dict(cfg),
    }


@router.get("/adapters")
async def adapters() -> dict[str, Any]:
    return {"adapters": list_adapters(), "health": await adapters_health()}


@router.get("/settings")
async def get_settings() -> dict[str, Any]:
    return config_to_dict()


@router.post("/protections", status_code=201)
async def create_protection(body: ProtectionCreate, request: Request) -> dict[str, Any]:
    _ensure_channel(body.channel)
    store = get_channel_shield_store()
    record = await store.create_protection(
        _user_id(request),
        channel=body.channel,
        label=body.label,
        protection_key=body.protection_key,
        config=body.config,
    )
    return record.to_dict()


@router.get("/protections")
async def list_protections(
    request: Request, channel: str | None = None
) -> list[dict[str, Any]]:
    if channel:
        _ensure_channel(channel)
    store = get_channel_shield_store()
    return [p.to_dict() for p in await store.list_protections(_user_id(request), channel=channel)]


@router.get("/protections/{protection_id}")
async def get_protection(protection_id: str, request: Request) -> dict[str, Any]:
    store = get_channel_shield_store()
    record = await store.get_protection(protection_id, _user_id(request))
    if record is None:
        raise HTTPException(404, "Protection not found")
    return record.to_dict()


@router.patch("/protections/{protection_id}")
async def update_protection(
    protection_id: str, body: ProtectionUpdate, request: Request
) -> dict[str, Any]:
    store = get_channel_shield_store()
    record = await store.update_protection(
        protection_id, _user_id(request), body.model_dump(exclude_unset=True)
    )
    if record is None:
        raise HTTPException(404, "Protection not found")
    return record.to_dict()


@router.delete("/protections/{protection_id}", status_code=200)
async def delete_protection(protection_id: str, request: Request) -> dict[str, Any]:
    store = get_channel_shield_store()
    if not await store.delete_protection(protection_id, _user_id(request)):
        raise HTTPException(404, "Protection not found")
    return {"deleted": True}


@router.post("/protections/{protection_id}/verify")
async def verify_protection(protection_id: str, request: Request) -> dict[str, Any]:
    store = get_channel_shield_store()
    record = await store.get_protection(protection_id, _user_id(request))
    if record is None:
        raise HTTPException(404, "Protection not found")
    health = await get_adapter(record.channel).health()
    updated = await store.update_protection(
        protection_id, _user_id(request), {"verified": bool(health.get("ok"))}
    )
    return {"protection": updated.to_dict() if updated else None, "health": health}


@router.get("/messages")
async def list_messages(
    request: Request,
    channel: str | None = None,
    status: str | None = None,
    verdict: str | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> list[dict[str, Any]]:
    if channel:
        _ensure_channel(channel)
    store = get_channel_shield_store()
    items = await store.list_messages(
        _user_id(request), channel=channel, status=status, verdict=verdict, limit=limit
    )
    return [m.to_dict() for m in items]


@router.get("/messages/{message_id}")
async def get_message(message_id: str, request: Request) -> dict[str, Any]:
    store = get_channel_shield_store()
    message = await store.get_message(message_id, _user_id(request))
    if message is None:
        raise HTTPException(404, "Message not found")
    events = await store.list_events(message_id=message_id)
    attachments = await store.list_attachments(message_id)
    return {
        **message.to_dict(),
        "events": [e.to_dict() for e in events],
        "attachments": [a.to_dict() for a in attachments],
    }


@router.get("/messages/{message_id}/report")
async def get_report(message_id: str, request: Request) -> dict[str, Any]:
    store = get_channel_shield_store()
    message = await store.get_message(message_id, _user_id(request))
    if message is None:
        raise HTTPException(404, "Message not found")
    return {
        "message_id": message.id,
        "channel": message.channel,
        "verdict": message.verdict,
        "status": message.status,
        "envelope": message.envelope,
        "report": message.report,
        "safe_summary": message.safe_summary,
        "scout_ids": message.scout_ids,
    }


@router.post("/messages/{message_id}/release")
async def release_message(message_id: str, request: Request) -> dict[str, Any]:
    service = get_channel_shield_service()
    try:
        return await service.release_message(
            message_id, _user_id(request), is_admin=_is_admin(request)
        )
    except KeyError:
        raise HTTPException(404, "Message not found") from None
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/messages/{message_id}/destroy")
async def destroy_message(message_id: str, request: Request) -> dict[str, Any]:
    service = get_channel_shield_service()
    try:
        return await service.destroy_message(
            message_id, _user_id(request), is_admin=_is_admin(request)
        )
    except KeyError:
        raise HTTPException(404, "Message not found") from None
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc


class AgentGuardBody(BaseModel):
    action: str = "prompt"
    agent_id: str = "assistant"
    message_id: str | None = None
    content: str | None = None
    tool_name: str | None = None
    memory_kind: str | None = None
    approval_granted: bool = False


@router.post("/agent/guard")
async def agent_guard(body: AgentGuardBody) -> dict[str, Any]:
    from keprix.channel_shield.agent_ingress import guard_agent_ingress

    decision = await guard_agent_ingress(
        action=body.action,  # type: ignore[arg-type]
        agent_id=body.agent_id,
        message_id=body.message_id,
        content=body.content,
        tool_name=body.tool_name,
        memory_kind=body.memory_kind,
        approval_granted=body.approval_granted,
    )
    return decision.to_dict()


@router.get("/agent/os")
async def agent_os_panel() -> dict[str, Any]:
    from keprix.channel_shield.agent_policy import list_default_policies

    store = get_channel_shield_store()
    return {
        "protectedAgents": list_default_policies(),
        "blockedTriggers": await store.list_agent_blocks(limit=40),
        "approvalRequests": await store.list_approval_requests(limit=40),
        "memoryWritesPrevented": await store.list_memory_blocks(limit=40),
    }


@router.get("/messages/{message_id}/employee-action")
async def employee_action_drawer(message_id: str, request: Request) -> dict[str, Any]:
    store = get_channel_shield_store()
    message = await store.get_message(message_id, _user_id(request))
    if message is None:
        message = await store.get_message(message_id)
    if message is None:
        raise HTTPException(404, "Message not found")
    events = await store.list_events(message_id=message_id, limit=50)
    evidence_acl = "security_review_only"
    if message.status in {"released", "delivered"} and message.verdict == "clean":
        evidence_acl = "released_with_provenance"
    elif message.status == "destroyed":
        evidence_acl = "destroyed"
    return {
        "messageId": message.id,
        "verdict": message.verdict,
        "policyLabel": message.policy_label,
        "status": message.status,
        "safeSummary": message.safe_summary,
        "agentSafeContent": message.agent_safe_content,
        "evidenceAccess": evidence_acl,
        "rawEvidenceRef": message.raw_evidence_ref,
        "allowedActions": (message.agent_safe_content or {}).get("allowedActions") or [],
        "approvalState": "required"
        if message.status == "quarantined"
        else "not_required",
        "auditTrail": [e.to_dict() for e in events],
        "scoutIds": list(message.scout_ids),
    }


class ApprovalBody(BaseModel):
    message_id: str
    agent_id: str = "assistant"
    action: str = "release"


@router.post("/agent/approvals")
async def create_approval(body: ApprovalBody) -> dict[str, Any]:
    from keprix.channel_shield.agent_ingress import new_approval_request

    store = get_channel_shield_store()
    req = new_approval_request(
        message_id=body.message_id, agent_id=body.agent_id, action=body.action
    )
    return await store.add_approval_request(req)


@router.post("/ingest")
async def ingest(body: IngestBody, request: Request) -> dict[str, Any]:
    channel = _ensure_channel(body.channel)
    store = get_channel_shield_store()
    protection_id = body.protection_id
    if not protection_id and body.protection_key:
        found = await store.find_protection_by_key(channel, body.protection_key)
        if found is None:
            raise HTTPException(404, "Protection not found for key")
        protection_id = found.id
    if not protection_id:
        raise HTTPException(400, "protection_id or protection_key required")
    protection = await store.get_protection(protection_id, _user_id(request))
    if protection is None:
        # Allow system ingest with matching protection without user filter
        protection = await store.get_protection(protection_id)
    if protection is None or protection.channel != channel:
        raise HTTPException(404, "Protection not found")

    adapter = get_adapter(channel)
    raw_body = b""
    headers = {k.lower(): v for k, v in request.headers.items()}
    auth = adapter.authenticate_ingress(headers, raw_body)
    envelope, raw_bytes, attachment_bytes = adapter.ingest(
        body.payload, protection_id=protection_id, auth_signals=auth
    )
    service = get_channel_shield_service()
    return await service.process_envelope(
        protection.user_id,
        envelope,
        raw_bytes=raw_bytes,
        attachment_bytes=attachment_bytes,
    )


@router.post("/webhooks/{channel}")
async def channel_webhook(channel: str, request: Request) -> dict[str, Any]:
    channel = _ensure_channel(channel)
    body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}
    adapter = get_adapter(channel)
    auth = adapter.authenticate_ingress(headers, body)

    # Slack URL verification challenge
    if channel == "slack":
        try:
            import json

            data = json.loads(body.decode("utf-8") or "{}")
            if data.get("type") == "url_verification":
                return {"challenge": data.get("challenge")}
        except Exception:
            data = {}
    else:
        try:
            import json

            data = json.loads(body.decode("utf-8") or "{}") if body else {}
        except Exception:
            data = body

    store = get_channel_shield_store()
    # Resolve protection by key hints
    protection = None
    key_hints = []
    if isinstance(data, dict):
        key_hints = [
            data.get("team_id"),
            data.get("tenant_id"),
            (data.get("metadata") or {}).get("phone_number_id")
            if isinstance(data.get("metadata"), dict)
            else None,
            data.get("phone_number_id"),
            data.get("guild_id"),
            data.get("To"),
            headers.get("x-protection-key"),
        ]
    for hint in key_hints:
        if hint:
            protection = await store.find_protection_by_key(channel, str(hint))
            if protection:
                break
    if protection is None:
        # Fall back to first enabled protection for channel (dev / single-tenant)
        for p in store.protections.values():
            if p.channel == channel and p.enabled:
                protection = p
                break
    if protection is None:
        raise HTTPException(404, f"No protection configured for channel {channel}")

    envelope, raw_bytes, attachment_bytes = adapter.ingest(
        data if not isinstance(data, bytes) else data,
        protection_id=protection.id,
        auth_signals=auth,
    )
    # For SMS form bodies already handled in adapter via bytes
    if channel == "sms" and isinstance(data, dict) is False:
        envelope, raw_bytes, attachment_bytes = adapter.ingest(
            body, protection_id=protection.id, auth_signals=auth
        )

    service = get_channel_shield_service()
    result = await service.process_envelope(
        protection.user_id,
        envelope,
        raw_bytes=raw_bytes,
        attachment_bytes=attachment_bytes,
    )
    return {"ok": True, "action": result.get("action"), "message_id": result["message"]["id"]}


# --- email-shield alias (forces channel=email where relevant) ---


@email_alias_router.get("/health")
async def email_health() -> dict[str, Any]:
    data = await health()
    data["alias"] = "email-shield"
    return data


@email_alias_router.get("/messages")
async def email_messages(request: Request, status: str | None = None, limit: int = 100):
    return await list_messages(request, channel="email", status=status, limit=limit)


@email_alias_router.post("/ingest")
async def email_ingest(body: IngestBody, request: Request) -> dict[str, Any]:
    body.channel = "email"
    return await ingest(body, request)


@email_alias_router.post("/messages/{message_id}/release")
async def email_release(message_id: str, request: Request) -> dict[str, Any]:
    return await release_message(message_id, request)


@email_alias_router.post("/messages/{message_id}/destroy")
async def email_destroy(message_id: str, request: Request) -> dict[str, Any]:
    return await destroy_message(message_id, request)
