"""Conversation workspace API routes."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from keprix.agent.keprix.mutation import get_mutation_engine
from keprix.agent.keprix.store import get_generated_tool_store
from keprix.auth.dependencies import get_current_user, require_admin
from keprix.keys.local_access import effective_access_level
from keprix.scout.kill_relay import agent_stop_requested, tools_disabled, workspace_locked
from keprix.scout.policy_receiver import get_policy_registry
from keprix.workspace.core.exceptions import NotFoundError
from keprix.workspace.repository import workspace_repo
from keprix.workspace.schemas import SessionRename

router = APIRouter(tags=["conversations"])

AVAILABLE_MODELS = [
    {"id": "anthropic:claude-sonnet-4-6", "provider": "anthropic", "name": "claude-sonnet-4-6"},
    {"id": "openai:gpt-4.1", "provider": "openai", "name": "gpt-4.1"},
    {"id": "google:gemini-2.5-pro", "provider": "google", "name": "gemini-2.5-pro"},
    {"id": "groq:llama-3.3-70b", "provider": "groq", "name": "llama-3.3-70b"},
    {"id": "ollama:llama3.2", "provider": "ollama", "name": "llama3.2"},
]


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


def _demo_stream_keywords(lowered: str) -> bool:
    return any(
        token in lowered
        for token in ("tool", "read", "code", "file", "synth", "mutation", "```")
    )


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
) -> AsyncIterator[dict[str, Any]]:
    """Emit NDJSON stream events for the workspace chat UI."""
    lowered = user_text.lower()
    if user_text.strip().startswith("/") or not _demo_stream_keywords(lowered):
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

    intro = (
        f"I received your message using model `{model or 'default'}`. "
        "Connect a full agent runtime for live inference."
    )
    words = intro.split(" ")
    for word in words:
        yield {"event": "text_delta", "content": f"{word} "}
        await asyncio.sleep(0.03)

    if "tool" in lowered or "read" in lowered:
        if not tools_disabled() and not get_policy_registry().is_tool_blocked("read_file"):
            yield {
                "event": "tool_call",
                "name": "read_file",
                "input": {"path": "/workspace/example.txt"},
                "status": "running",
            }
            await asyncio.sleep(0.2)
            yield {
                "event": "tool_call_update",
                "name": "read_file",
                "output": "Example file contents for preview.",
                "status": "done",
            }

    if "```" in user_text or "code" in lowered:
        yield {
            "event": "code",
            "language": "python",
            "content": "def hello(name: str) -> str:\n    return f'Hello, {name}'\n",
        }

    if "file" in lowered:
        yield {
            "event": "file",
            "path": "/workspace/report-summary.md",
            "action": "created",
        }

    if "synth" in lowered or "mutation" in lowered:
        record = get_generated_tool_store().create(
            task_that_triggered=user_text,
            tool_name="fetch_stock_price",
            tool_code=(
                "import requests\n\n"
                "def fetch_stock_price(symbol: str) -> float:\n"
                "    return 227.42\n"
            ),
            skill_yaml=(
                "name: fetch_stock_price\n"
                "description: Fetch a stock price by symbol.\n"
            ),
            description="Fetch stock price via public API",
            gap_description="No existing tool for stock quotes",
            static_analysis={"safe": True, "violations": []},
            sandbox_result={
                "passed": True,
                "output": "AAPL: 227.42",
                "stderr": "",
                "exit_code": 0,
            },
        )
        sandbox = record.sandbox_result or {}
        yield {
            "event": "mutation",
            "id": record.id,
            "toolName": record.tool_name,
            "approach": record.gap_description or record.description,
            "code": record.tool_code,
            "skillYaml": record.skill_yaml,
            "sandboxResult": sandbox.get("output", ""),
            "sandboxExitCode": sandbox.get("exit_code", 0),
            "sandboxStderr": sandbox.get("stderr", ""),
            "status": "pending",
        }

    yield {"event": "text_done"}


@router.get("/api/models/available")
async def models_available(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"models": AVAILABLE_MODELS}


@router.get("/api/conversations")
async def list_conversations(
    user: dict = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=50),
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
        raise HTTPException(status_code=423, detail="Workspace is read-only due to Scout governance")
    if agent_stop_requested():
        raise HTTPException(status_code=409, detail="Agent operations halted by Scout kill switch")
    try:
        workspace_repo.get_session(user, session_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None

    user_message = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "content": [{"type": "text", "content": body.content}],
        "createdAt": _iso_now(),
        "file_ids": body.file_ids,
    }
    workspace_repo.append_message(user, session_id, user_message)

    async def event_stream() -> AsyncIterator[bytes]:
        blocks: list[dict[str, Any]] = []
        text_buffer = ""

        async for event in _stream_assistant_reply(
            user_text=body.content,
            model=body.model,
            user_id=str(user.get("id") or user.get("username") or "web"),
        ):
            if event.get("event") == "text_delta":
                text_buffer += str(event.get("content") or "")
                yield (json.dumps(event) + "\n").encode("utf-8")
                continue

            if event.get("event") == "text_done" and text_buffer:
                blocks.append({"type": "text", "content": text_buffer.strip()})
                text_buffer = ""
                yield (json.dumps(event) + "\n").encode("utf-8")
                continue

            if event.get("event") == "tool_call":
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

            yield (json.dumps(event) + "\n").encode("utf-8")

        assistant_message = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": blocks,
            "createdAt": _iso_now(),
        }
        workspace_repo.append_message(user, session_id, assistant_message)
        yield (json.dumps({"event": "message_done", "message": assistant_message}) + "\n").encode("utf-8")

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@router.post("/api/mutations/{record_id}/approve")
async def approve_mutation(
    record_id: str,
    channel: str = Query(default="web_ui"),
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    from dataclasses import asdict

    record = await get_mutation_engine().approve(record_id, approver_id="admin", channel=channel)
    if record is None:
        raise HTTPException(status_code=404, detail="Pending tool not found")
    return asdict(record)


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
async def open_file(body: OpenFileBody, user: dict = Depends(get_current_user)) -> dict[str, str]:
    if not _is_owner(user):
        raise HTTPException(status_code=403, detail="Owner access required")
    return {"status": "queued", "path": body.path}
