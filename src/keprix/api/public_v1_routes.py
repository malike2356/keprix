"""Public REST API v1 for external integrations."""

from __future__ import annotations

import asyncio
import json
import queue
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from keprix.public_api.agent_runtime import run_agent_chat_completion
from keprix.public_api.auth import check_endpoint_allowed, check_tool_permission, require_api_key
from keprix.public_api.keys import ApiKeyContext
from keprix.observability.metrics import get_metrics_store
from keprix.security.prompt_guard_policy import analyze_prompt_turn

router = APIRouter(prefix="/v1", tags=["public"])


class ChatBody(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None
    model: str | None = None
    skills: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tokens_used: int


class TaskBody(BaseModel):
    title: str
    description: str = ""


class ToolCallBody(BaseModel):
    arguments: dict = Field(default_factory=dict)
    args: dict = Field(default_factory=dict)


def _tools_allowed(ctx: ApiKeyContext) -> bool:
    try:
        check_tool_permission(ctx)
        return True
    except HTTPException:
        return False


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatBody, ctx: ApiKeyContext = Depends(require_api_key)) -> ChatResponse:
    check_endpoint_allowed(ctx, "/v1/chat")
    session_id = body.session_id or str(uuid.uuid4())
    prompt_decision = analyze_prompt_turn(body.message)
    if prompt_decision.blocked:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "prompt_guard_blocked",
                "message": "Prompt guard blocked this turn before model execution.",
                "patterns": prompt_decision.patterns,
                "confidence": prompt_decision.confidence,
            },
        )
    message = prompt_decision.sanitized_text or body.message
    try:
        result = await run_agent_chat_completion(
            messages=[{"role": "user", "content": message}],
            allow_tools=_tools_allowed(ctx),
            session_id=session_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"error": str(exc), "code": "agent_runtime_error"}) from exc

    store = get_metrics_store()
    await store.record(
        metric_type="message",
        metric_name="public_chat",
        metric_value=1,
        user_id=ctx.workspace_id,
        tags={"session_id": result.session_id},
    )
    await store.record(
        metric_type="token",
        metric_name="public_chat",
        metric_value=result.total_tokens,
        user_id=ctx.workspace_id,
    )
    return ChatResponse(
        response=result.final_response,
        session_id=result.session_id,
        tokens_used=result.total_tokens,
    )


@router.post("/chat/stream")
async def chat_stream(body: ChatBody, ctx: ApiKeyContext = Depends(require_api_key)) -> StreamingResponse:
    check_endpoint_allowed(ctx, "/v1/chat/stream")
    session_id = body.session_id or str(uuid.uuid4())
    prompt_decision = analyze_prompt_turn(body.message)
    if prompt_decision.blocked:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "prompt_guard_blocked",
                "message": "Prompt guard blocked this turn before model execution.",
                "patterns": prompt_decision.patterns,
                "confidence": prompt_decision.confidence,
            },
        )
    message = prompt_decision.sanitized_text or body.message
    stream_queue: queue.Queue[str | None] = queue.Queue()
    result_holder: list = []

    def _on_delta(delta: str | None) -> None:
        if delta:
            stream_queue.put(delta)

    async def _run_agent() -> None:
        try:
            result = await run_agent_chat_completion(
                messages=[{"role": "user", "content": message}],
                allow_tools=_tools_allowed(ctx),
                session_id=session_id,
                stream_delta_callback=_on_delta,
            )
            result_holder.append(result)
        finally:
            stream_queue.put(None)

    agent_task = asyncio.create_task(_run_agent())

    async def event_stream():
        try:
            while True:
                if agent_task.done() and stream_queue.empty():
                    break
                try:
                    delta = await asyncio.get_running_loop().run_in_executor(
                        None,
                        lambda: stream_queue.get(timeout=0.2),
                    )
                except queue.Empty:
                    continue
                if delta is None:
                    break
                payload = {"session_id": session_id, "chunk": delta}
                yield f"data: {json.dumps(payload)}\n\n"

            await agent_task
            result = result_holder[0] if result_holder else None
            if result is not None:
                store = get_metrics_store()
                await store.record(
                    metric_type="message",
                    metric_name="public_chat_stream",
                    metric_value=1,
                    user_id=ctx.workspace_id,
                    tags={"session_id": result.session_id},
                )
                await store.record(
                    metric_type="token",
                    metric_name="public_chat_stream",
                    metric_value=result.total_tokens,
                    user_id=ctx.workspace_id,
                )
                done_payload = {
                    "done": True,
                    "session_id": result.session_id,
                    "tokens_used": result.total_tokens,
                }
            else:
                done_payload = {"done": True, "session_id": session_id, "tokens_used": 0}
            yield f"data: {json.dumps(done_payload)}\n\n"
        except Exception as exc:
            if not agent_task.done():
                agent_task.cancel()
            error_payload = {"error": str(exc), "session_id": session_id}
            yield f"data: {json.dumps(error_payload)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/tools/{tool_name}")
async def call_tool(
    tool_name: str,
    body: ToolCallBody | None = None,
    ctx: ApiKeyContext = Depends(require_api_key),
) -> dict:
    check_endpoint_allowed(ctx, "/v1/tools")
    check_tool_permission(ctx)
    payload_body = body or ToolCallBody()
    args = dict(payload_body.arguments or payload_body.args or {})
    store = get_metrics_store()
    await store.record(
        metric_type="tool_call",
        metric_name=tool_name,
        metric_value=1,
        user_id=ctx.workspace_id,
    )
    try:
        from keprix.tools.registry import registry

        try:
            import keprix.tools.mesh_workspace_tools  # noqa: F401
        except Exception:
            pass
        try:
            import keprix.tools.product_lead_tools  # noqa: F401
        except Exception:
            pass
        result = registry.dispatch(tool_name, args, user_id=str(ctx.workspace_id))
        try:
            payload = json.loads(result) if isinstance(result, str) else result
        except Exception:
            payload = {"raw": result}
        return {"tool": tool_name, "status": "completed", "result": payload}
    except Exception as exc:
        return {"tool": tool_name, "status": "error", "error": str(exc)}


@router.get("/memory/search")
async def memory_search(q: str, ctx: ApiKeyContext = Depends(require_api_key)) -> dict:
    check_endpoint_allowed(ctx, "/v1/memory/search")
    if not q.strip():
        raise HTTPException(status_code=400, detail="q is required")
    from keprix.memory.orchestrator import MemoryOrchestrator

    user_id = str(getattr(ctx, "workspace_id", None) or getattr(ctx, "user_id", None) or "default")
    payload = await MemoryOrchestrator().recall(user_id, q, limit=10, reinforce=False)
    return {
        "query": q,
        "results": payload.get("hits") or [],
        "context": payload.get("context") or "",
        "user": ctx.workspace_id,
    }


@router.post("/tasks")
async def create_task(body: TaskBody, ctx: ApiKeyContext = Depends(require_api_key)) -> dict:
    check_endpoint_allowed(ctx, "/v1/tasks")
    from keprix.public_api.task_store import get_public_task_store

    row = get_public_task_store().create(workspace_id=str(ctx.workspace_id), title=body.title)
    return row


@router.get("/tasks")
async def list_tasks(ctx: ApiKeyContext = Depends(require_api_key)) -> dict:
    check_endpoint_allowed(ctx, "/v1/tasks")
    from keprix.public_api.task_store import get_public_task_store

    rows = get_public_task_store().list_for_workspace(str(ctx.workspace_id))
    return {"tasks": rows, "user": ctx.workspace_id}
