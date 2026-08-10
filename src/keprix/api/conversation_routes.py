"""Conversation workspace API routes."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from keprix.agent.keprix.mutation import get_mutation_engine
from keprix.auth.dependencies import get_current_user, require_admin
from keprix.keys.local_access import effective_access_level
from keprix.governance.kill_relay import agent_stop_requested, workspace_locked
from keprix.workspace.core.exceptions import NotFoundError
from keprix.workspace.repository import workspace_repo
from keprix.workspace.schemas import SessionRename

from keprix.agent.keprix.chat_mutation_bridge import maybe_run_mutation_for_chat
from keprix.api.chat_inference import list_available_models, stream_chat_completion
from keprix.api.turn_registry import turn_registry
from keprix.brain.activation_emitter import ActivationEventType, activation_emitter
from keprix.security.rule_of_two import record_leg
from keprix.security.prompt_guard_policy import analyze_prompt_turn

router = APIRouter(tags=["conversations"])
logger = logging.getLogger(__name__)


class CreateConversationBody(BaseModel):
    title: str = "New conversation"


class SendMessageBody(BaseModel):
    content: str = Field(..., min_length=1)
    file_ids: list[str] = Field(default_factory=list)
    model: str | None = None


class RejectMutationBody(BaseModel):
    reason: str | None = None
    channel: str = "web_ui"


class OpenFileBody(BaseModel):
    path: str


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize_session(row: dict[str, Any]) -> dict[str, Any]:
    created = row.get("created_at")
    updated = row.get("updated_at")
    return {
        "id": row["id"],
        "title": row.get("title") or "Conversation",
        "messages": row.get("messages") or [],
        "created_at": created.isoformat() if hasattr(created, "isoformat") else created,
        "updated_at": updated.isoformat() if hasattr(updated, "isoformat") else updated,
    }


def _serialize_session_item(row: dict[str, Any]) -> dict[str, Any]:
    payload = _serialize_session(row)
    messages = payload.get("messages") or []
    preview = ""
    if messages:
        last = messages[-1]
        preview = _message_preview(last) if isinstance(last, dict) else ""
    payload["preview"] = preview
    return payload


def _message_preview(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = str(block.get("content") or "").strip()
                if text:
                    return text
    return ""


def _is_owner(user: dict[str, Any]) -> bool:
    role = str(user.get("role") or "").lower()
    if role in {"admin", "owner", "developer"}:
        return True
    return effective_access_level() in {"developer", "admin", "owner"}


async def _agent_reply_text(*, user_text: str, user_id: str) -> str:
    from keprix.interfaces.interface_registry import InterfaceKind, get_interface_registry

    registry = get_interface_registry()
    payload = await registry.dispatch(
        "default",
        InterfaceKind.WEB_UI,
        message=user_text,
        user_id=user_id,
        workspace_id="default",
        channel_user_id=user_id,
    )
    return str(payload.get("message") or "").strip()


async def _stream_assistant_reply(
    *,
    user_text: str,
    model: str | None,
    user_id: str,
    history: list[dict[str, Any]] | None = None,
    session_id: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Emit NDJSON stream events for the workspace chat UI."""
    from keprix.interfaces.interface_registry import InterfaceKind, get_interface_registry
    from keprix.interfaces.web_ui_stream import chat_gateway_stream_enabled
    from keprix.interfaces.web_ui_stream_events import map_gateway_event_to_ndjson

    if chat_gateway_stream_enabled():
        logger.debug("routing chat turn through WEB_UI gateway stream (mutation bridge inside handler)")
        registry = get_interface_registry()
        async for gw_event in registry.dispatch_stream(
            "default",
            InterfaceKind.WEB_UI,
            message=user_text,
            user_id=user_id,
            workspace_id="default",
            channel_user_id=user_id,
            session_id=session_id,
            model=model,
            history=history,
        ):
            if gw_event.event == "done":
                continue
            mapped = map_gateway_event_to_ndjson(gw_event)
            yield mapped
            if mapped.get("event") == "text_done":
                return
        return

    if user_text.strip().startswith("/"):
        try:
            reply = await _agent_reply_text(user_text=user_text, user_id=user_id)
        except Exception:
            reply = ""
        if reply:
            for word in reply.split(" "):
                yield {"event": "text_delta", "content": f"{word} "}
                await asyncio.sleep(0.01)
            yield {"event": "text_done"}
            return

    mutation_ran = False
    from keprix.agent.keprix.mutation_hook import chat_mutation_sidecar_enabled

    if chat_mutation_sidecar_enabled():
        async for event in maybe_run_mutation_for_chat(
            user_text=user_text,
            user_id=user_id,
            channel="web_ui",
            session_id=session_id,
        ):
            mutation_ran = True
            yield event
        if mutation_ran:
            return

    try:
        async for delta in stream_chat_completion(
            user_text=user_text,
            model_id=model,
            history=history,
            user_id=user_id,
            session_id=session_id,
        ):
            yield {"event": "text_delta", "content": delta}
        yield {"event": "text_done"}
        return
    except Exception as exc:
        from keprix.quotas.actor_enforcer import ActorQuotaExceeded
        from keprix.transparency.consent_gate import ConsentRequiredError

        if isinstance(exc, ConsentRequiredError):
            yield {
                "event": "error",
                "content": (
                    f"AI consent required for '{exc.feature}'. "
                    "Open Privacy and grant affirmative consent for this AI feature."
                ),
                "code": 403,
                "ai_consent_required": True,
                "feature": exc.feature,
            }
            yield {"event": "text_done"}
            return
        if isinstance(exc, ActorQuotaExceeded):
            detail = exc.to_http_detail()
            msg = (
                f"Quota exceeded ({detail.get('reason')}). "
                f"Remaining resets on the next {detail.get('period', 'period')} window. "
                "Actor quotas are separate from managed AI billing credits."
            )
            yield {"event": "error", "content": msg, "code": 429, "quota": detail}
            yield {"event": "text_done"}
            return
        error_text = f"Chat inference failed: {exc}"
        for word in error_text.split(" "):
            yield {"event": "text_delta", "content": f"{word} "}
            await asyncio.sleep(0.01)
        yield {"event": "text_done"}
        return


@router.get("/api/models/available")
async def models_available(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"models": list_available_models()}


@router.get("/api/conversations")
async def list_conversations(
    user: dict = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    sort: str = Query("updated_at:desc"),
) -> dict[str, Any]:
    rows = workspace_repo.list_sessions(user, limit=limit, offset=0)
    if sort.endswith(":desc"):
        rows.sort(key=lambda row: row.get("updated_at") or row.get("created_at") or "", reverse=True)
    else:
        rows.sort(key=lambda row: row.get("updated_at") or row.get("created_at") or "")
    return {"items": [_serialize_session_item(row) for row in rows[:limit]]}


@router.post("/api/conversations")
async def create_conversation(
    body: CreateConversationBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    session = workspace_repo.create_session(user, body.title)
    return {"id": session["id"], **_serialize_session(session)}


@router.get("/api/conversations/{session_id}")
async def get_conversation(session_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        return _serialize_session(workspace_repo.get_session(user, session_id))
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None


@router.put("/api/conversations/{session_id}")
async def rename_conversation(
    session_id: str,
    body: SessionRename,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        return _serialize_session(workspace_repo.rename_session(user, session_id, body.title))
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None


@router.delete("/api/conversations/{session_id}", status_code=200)
async def delete_conversation(session_id: str, user: dict = Depends(get_current_user)) -> None:
    try:
        workspace_repo.delete_session(user, session_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None


@router.post("/api/conversations/{session_id}/messages")
async def send_message(
    session_id: str,
    body: SendMessageBody,
    user: dict = Depends(get_current_user),
) -> StreamingResponse:
    if workspace_locked():
        raise HTTPException(status_code=423, detail="Workspace is read-only due to governance policy")
    if agent_stop_requested():
        raise HTTPException(status_code=409, detail="Agent operations halted by governance kill switch")
    try:
        session = workspace_repo.get_session(user, session_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None

    history = session.get("messages") or []

    user_message = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "content": [{"type": "text", "content": body.content}],
        "createdAt": _iso_now(),
        "file_ids": body.file_ids,
    }
    workspace_repo.append_message(user, session_id, user_message)

    async def event_stream() -> AsyncIterator[bytes]:
        turn = turn_registry.register(session_id)
        blocks: list[dict[str, Any]] = []
        text_buffer = ""
        prompt_decision = analyze_prompt_turn(body.content)

        try:
            if prompt_decision.blocked:
                yield (
                    json.dumps(
                        {
                            "event": "error",
                            "code": "prompt_guard_blocked",
                            "content": "Prompt guard blocked this turn before model execution.",
                            "patterns": prompt_decision.patterns,
                            "confidence": prompt_decision.confidence,
                        }
                    )
                    + "\n"
                ).encode("utf-8")
                return

            if prompt_decision.quarantined and prompt_decision.sanitized_text:
                record_leg(session_id, untrusted_content=True, last_reason="prompt_guard_quarantine")
                blocks.append(
                    {
                        "type": "system",
                        "content": (
                            f"Prompt guard quarantined this turn. Patterns: {', '.join(prompt_decision.patterns) or 'none'}."
                        ),
                    }
                )
                yield (
                    json.dumps(
                        {
                            "event": "content_quarantined",
                            "patterns": prompt_decision.patterns,
                            "confidence": prompt_decision.confidence,
                        }
                    )
                    + "\n"
                ).encode("utf-8")
                user_text = prompt_decision.sanitized_text
            else:
                record_leg(session_id, untrusted_content=False, last_reason="prompt_guard_clear")
                user_text = body.content

            try:
                await activation_emitter.emit(
                    ActivationEventType.SESSION_LINKED,
                    workspace_id=str(user.get("workspace_id") or "default"),
                    session_id=session_id,
                    node_kind="session",
                    node_id=session_id,
                    relation="active_session",
                )
            except Exception:
                pass
            async for event in _stream_assistant_reply(
                user_text=user_text,
                model=body.model,
                user_id=str(user.get("id") or user.get("username") or "web"),
                history=history,
                session_id=session_id,
            ):
                if turn.cancel_event.is_set():
                    break
                if event.get("event") == "text_delta":
                    text_buffer += str(event.get("content") or "")
                    turn_registry.set_partial_chars(session_id, len(text_buffer))
                    yield (json.dumps(event) + "\n").encode("utf-8")
                    continue

                if event.get("event") == "text_done" and text_buffer:
                    blocks.append({"type": "text", "content": text_buffer.strip()})
                    text_buffer = ""
                    yield (json.dumps(event) + "\n").encode("utf-8")
                    continue

                if event.get("event") == "tool_call":
                    try:
                        await activation_emitter.emit(
                            ActivationEventType.TOOL_CALLED,
                            workspace_id=str(user.get("workspace_id") or "default"),
                            session_id=session_id,
                            node_kind="tool",
                            node_id=str(event.get("name") or "tool"),
                            relation="called_in_session",
                        )
                    except Exception:
                        pass
                    blocks.append(
                        {
                            "type": "tool_call",
                            "name": event["name"],
                            "input": event.get("input") or {},
                            "status": event.get("status") or "running",
                        }
                    )
                    yield (json.dumps(event) + "\n").encode("utf-8")
                    continue

                if event.get("event") in {"skill_selected", "skill_fired", "skill_action"}:
                    skill_name = event.get("name") or event.get("skill") or event.get("slug") or event.get("skillName")
                    try:
                        await activation_emitter.emit(
                            ActivationEventType.SKILL_FIRED if event.get("event") != "skill_selected" else ActivationEventType.SKILL_SELECTED,
                            workspace_id=str(user.get("workspace_id") or "default"),
                            session_id=session_id,
                            node_kind="skill",
                            node_id=str(skill_name or "skill"),
                            relation=str(event.get("event")),
                        )
                    except Exception:
                        pass
                    yield (json.dumps(event) + "\n").encode("utf-8")
                    continue

                if event.get("event") == "tool_call_update":
                    for block in reversed(blocks):
                        if block.get("type") == "tool_call" and block.get("name") == event.get("name"):
                            block["output"] = event.get("output")
                            block["status"] = event.get("status") or "done"
                            break
                    yield (json.dumps(event) + "\n").encode("utf-8")
                    continue

                if event.get("event") == "code":
                    blocks.append(
                        {
                            "type": "code",
                            "language": event.get("language") or "text",
                            "content": event.get("content") or "",
                        }
                    )
                    yield (json.dumps(event) + "\n").encode("utf-8")
                    continue

                if event.get("event") == "file":
                    blocks.append(
                        {
                            "type": "file",
                            "path": event.get("path") or "",
                            "action": event.get("action") or "created",
                        }
                    )
                    yield (json.dumps(event) + "\n").encode("utf-8")
                    continue

                if event.get("event") == "mutation":
                    blocks.append(
                        {
                            "type": "mutation",
                            "id": event.get("id"),
                            "toolName": event.get("toolName"),
                            "approach": event.get("approach"),
                            "code": event.get("code"),
                            "skillYaml": event.get("skillYaml"),
                            "sandboxResult": event.get("sandboxResult"),
                            "sandboxExitCode": event.get("sandboxExitCode", 0),
                            "sandboxStderr": event.get("sandboxStderr", ""),
                            "status": event.get("status") or "pending",
                        }
                    )
                    yield (json.dumps(event) + "\n").encode("utf-8")
                    continue

                if event.get("event") in {"clarify", "approval", "approval_resolved"}:
                    yield (json.dumps(event) + "\n").encode("utf-8")
                    continue

                yield (json.dumps(event) + "\n").encode("utf-8")
        finally:
            turn_registry.unregister(session_id)

        if text_buffer and not any(block.get("type") == "text" for block in blocks):
            blocks.append({"type": "text", "content": text_buffer.strip()})

        try:
            from keprix.security.ai_hardening import detect_canary_leak, record_anomaly

            for block in blocks:
                if block.get("type") != "text":
                    continue
                content = str(block.get("content") or "")
                if detect_canary_leak(content):
                    record_anomaly("canary_leak_blocked")
                    block["content"] = (
                        "[Response withheld: integrity token leak detected. "
                        "Please retry without requesting hidden system tokens.]"
                    )
        except Exception:
            pass

        assistant_message = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": blocks,
            "createdAt": _iso_now(),
        }
        workspace_repo.append_message(user, session_id, assistant_message)
        try:
            from keprix.vault.capture import capture_conversation

            refreshed = workspace_repo.get_session(user, session_id)
            await capture_conversation(
                session_id=session_id,
                messages=list(refreshed.get("messages") or []),
                title=str(refreshed.get("title") or "") or None,
                source="web",
            )
        except Exception:
            logger.debug("vault auto-capture failed for session %s", session_id, exc_info=True)
        yield (json.dumps({"event": "message_done", "message": assistant_message}) + "\n").encode("utf-8")

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@router.post("/api/mutations/{record_id}/approve")
async def approve_mutation(
    record_id: str,
    channel: str = Query(default="web_ui"),
    session_id: str | None = Query(default=None),
    user: dict = Depends(require_admin),
) -> dict[str, Any]:
    from dataclasses import asdict

    from keprix.agent.keprix.mutation_wait import has_active_mutation_wait, signal_mutation_resolved

    stream_waiting = has_active_mutation_wait(record_id)
    result = await get_mutation_engine().approve(record_id, approver_id="admin", channel=channel)
    if result is None:
        raise HTTPException(status_code=404, detail="Pending tool not found")

    if stream_waiting:
        await signal_mutation_resolved(record_id, "approved")

    record = result.record
    retry_message = result.retry_message
    assistant_message: dict[str, Any] | None = None

    if session_id and retry_message and not stream_waiting:
        assistant_message = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": [{"type": "text", "content": retry_message}],
            "createdAt": _iso_now(),
        }
        try:
            workspace_repo.append_message(user, session_id, assistant_message)
        except NotFoundError:
            assistant_message = None

    payload: dict[str, Any] = {
        **asdict(record),
        "record": asdict(record),
        "retry_message": None if stream_waiting else retry_message,
        "stream_waiting": stream_waiting,
    }
    if assistant_message is not None:
        payload["message"] = assistant_message
    return payload


@router.post("/api/mutations/{record_id}/reject")
async def reject_mutation(
    record_id: str,
    body: RejectMutationBody,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    from dataclasses import asdict

    record = await get_mutation_engine().reject(
        record_id,
        approver_id="admin",
        reason=body.reason,
        channel=body.channel,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Pending tool not found")

    from keprix.agent.keprix.mutation_wait import signal_mutation_resolved

    await signal_mutation_resolved(record_id, "rejected")
    return asdict(record)


@router.post("/api/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    payload = await file.read()
    file_id = str(uuid.uuid4())
    return {
        "id": file_id,
        "filename": file.filename or "upload.bin",
        "size": len(payload),
        "content_type": file.content_type or "application/octet-stream",
    }


@router.post("/api/files/open")
async def open_file(body: OpenFileBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    if not _is_owner(user):
        raise HTTPException(status_code=403, detail="Owner access required")
    from pathlib import Path

    path = Path(body.path).expanduser()
    if not path.is_absolute():
        try:
            from keprix.auth.config import data_dir

            path = Path(data_dir()) / path
        except Exception:
            path = Path.home() / ".keprix" / path
    try:
        path = path.resolve()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid path: {exc}") from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if not path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")
    # Bound read for operator preview (not a full file server).
    max_bytes = 256_000
    data = path.read_bytes()[:max_bytes]
    text: str | None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    return {
        "status": "opened",
        "path": str(path),
        "size": path.stat().st_size,
        "preview_bytes": len(data),
        "truncated": len(data) < path.stat().st_size,
        "text": text,
        "content_base64": None if text is not None else __import__("base64").b64encode(data).decode("ascii"),
    }
