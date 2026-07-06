"""OpenAI-compatible chat completions endpoint."""

from __future__ import annotations

import asyncio
import json
import queue
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from keprix.public_api.agent_runtime import run_agent_chat_completion
from keprix.public_api.auth import check_endpoint_allowed, check_model_allowed, check_tool_permission, require_api_key
from keprix.public_api.keys import ApiKeyContext
from keprix.public_api.logs import log_request
from keprix.public_api.rate_limits import enforce_rate_limit
from keprix.public_api.schemas import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    UsageInfo,
)
from keprix.public_api.usage import record_api_usage
from keprix.public_api.webhooks import dispatch_webhook_event

router = APIRouter(tags=["openai-compat"])


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def _tools_allowed(ctx: ApiKeyContext) -> bool:
    try:
        check_tool_permission(ctx)
        return True
    except HTTPException:
        return False


async def _notify_chat_completed(
    ctx: ApiKeyContext,
    body: ChatCompletionRequest,
    response: ChatCompletionResponse,
    session_id: str | None,
) -> None:
    await dispatch_webhook_event(
        ctx.workspace_id,
        "chat.completed",
        {
            "endpoint": "/v1/chat/completions",
            "model": body.model,
            "session_id": session_id,
            "completion_id": response.id,
            "content": response.choices[0].message.content[:500] if response.choices else "",
            "usage": response.usage.model_dump(),
        },
    )


def _response_from_agent(
    *,
    completion_id: str,
    model: str,
    agent_result,
) -> ChatCompletionResponse:
    prompt_tokens = agent_result.prompt_tokens or 1
    completion_tokens = agent_result.completion_tokens or _estimate_tokens(agent_result.final_response)
    total_tokens = agent_result.total_tokens or (prompt_tokens + completion_tokens)
    return ChatCompletionResponse(
        id=completion_id,
        created=int(time.time()),
        model=model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(role="assistant", content=agent_result.final_response),
                finish_reason=agent_result.finish_reason if agent_result.finish_reason in {"stop", "length", "tool_calls"} else "stop",
            )
        ],
        usage=UsageInfo(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        ),
    )


async def _complete(
    body: ChatCompletionRequest,
    ctx: ApiKeyContext,
    request: Request,
) -> ChatCompletionResponse:
    session_id = request.headers.get("X-Keprix-Session-Id", "").strip() or None
    gateway_session_key = request.headers.get("X-Keprix-Session-Key", "").strip() or None
    messages = [message.model_dump() for message in body.messages]
    try:
        agent_result = await run_agent_chat_completion(
            messages=messages,
            allow_tools=_tools_allowed(ctx),
            session_id=session_id,
            gateway_session_key=gateway_session_key,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(exc), "code": "invalid_request_error"},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": f"Agent runtime error: {exc}", "code": "agent_runtime_error"},
        ) from exc

    if not agent_result.final_response and (agent_result.failed or agent_result.partial):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": agent_result.error or "Agent run did not produce a response.",
                "code": "agent_incomplete",
            },
        )

    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    response = _response_from_agent(
        completion_id=completion_id,
        model=body.model,
        agent_result=agent_result,
    )
    await record_api_usage(
        ctx,
        endpoint="/v1/chat/completions",
        model=body.model,
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
    )
    asyncio.create_task(
        _notify_chat_completed(ctx, body, response, agent_result.session_id),
    )
    return response


async def _stream_completion(
    body: ChatCompletionRequest,
    ctx: ApiKeyContext,
    request: Request,
) -> StreamingResponse:
    session_id = request.headers.get("X-Keprix-Session-Id", "").strip() or None
    gateway_session_key = request.headers.get("X-Keprix-Session-Key", "").strip() or None
    messages = [message.model_dump() for message in body.messages]
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())
    stream_queue: queue.Queue[str | None] = queue.Queue()
    agent_ref: list = []

    def _on_delta(delta: str | None) -> None:
        if delta is not None:
            stream_queue.put(delta)

    async def _run() -> None:
        try:
            await run_agent_chat_completion(
                messages=messages,
                allow_tools=_tools_allowed(ctx),
                session_id=session_id,
                gateway_session_key=gateway_session_key,
                stream_delta_callback=_on_delta,
                agent_ref=agent_ref,
            )
        finally:
            stream_queue.put(None)

    agent_task = asyncio.create_task(_run())

    async def event_stream():
        try:
            role_sent = False
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
                if not role_sent:
                    role_chunk = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": body.model,
                        "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
                    }
                    yield f"data: {json.dumps(role_chunk)}\n\n"
                    role_sent = True
                chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": body.model,
                    "choices": [{"index": 0, "delta": {"content": delta}, "finish_reason": None}],
                }
                yield f"data: {json.dumps(chunk)}\n\n"

            await agent_task
            final_chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": body.model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception:
            if not agent_task.done():
                agent = agent_ref[0] if agent_ref else None
                if agent is not None and hasattr(agent, "interrupt"):
                    agent.interrupt()
            raise

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    body: ChatCompletionRequest,
    request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
):
    started = time.perf_counter()
    check_endpoint_allowed(ctx, "/v1/chat/completions")
    check_model_allowed(ctx, body.model)
    enforce_rate_limit(request, ctx)

    try:
        if body.stream:
            response = await _stream_completion(body, ctx, request)
            await log_request(
                api_key_id=ctx.key_id,
                workspace_id=ctx.workspace_id,
                method="POST",
                path="/v1/chat/completions",
                status_code=200,
                duration_ms=(time.perf_counter() - started) * 1000,
                request_body=body.model_dump(),
            )
            return response

        result = await _complete(body, ctx, request)
        await log_request(
            api_key_id=ctx.key_id,
            workspace_id=ctx.workspace_id,
            method="POST",
            path="/v1/chat/completions",
            status_code=200,
            duration_ms=(time.perf_counter() - started) * 1000,
            request_body=body.model_dump(),
        )
        return result
    except HTTPException as exc:
        await log_request(
            api_key_id=ctx.key_id,
            workspace_id=ctx.workspace_id,
            method="POST",
            path="/v1/chat/completions",
            status_code=exc.status_code,
            duration_ms=(time.perf_counter() - started) * 1000,
            request_body=body.model_dump(),
            error_message=str(exc.detail)[:200],
        )
        raise
    except Exception as exc:
        await log_request(
            api_key_id=ctx.key_id,
            workspace_id=ctx.workspace_id,
            method="POST",
            path="/v1/chat/completions",
            status_code=500,
            duration_ms=(time.perf_counter() - started) * 1000,
            request_body=body.model_dump(),
            error_message=str(exc)[:200],
        )
        raise
