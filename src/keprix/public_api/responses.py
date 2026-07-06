"""OpenAI-compatible responses API."""

from __future__ import annotations

import asyncio
import json
import queue
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from keprix.public_api.agent_runtime import parse_responses_input, run_agent_chat_completion
from keprix.public_api.auth import check_endpoint_allowed, check_model_allowed, require_api_key
from keprix.public_api.keys import ApiKeyContext
from keprix.public_api.logs import log_request
from keprix.public_api.openai_compat import _estimate_tokens, _tools_allowed
from keprix.public_api.rate_limits import enforce_rate_limit
from keprix.public_api.schemas import ResponseCreateRequest, ResponseObject, UsageInfo
from keprix.public_api.usage import record_api_usage
from keprix.public_api.webhooks import dispatch_webhook_event

router = APIRouter(tags=["openai-compat"])


def _input_messages(body: ResponseCreateRequest) -> list[dict]:
    if isinstance(body.input, str):
        return [{"role": "user", "content": body.input}]
    return [message.model_dump() for message in body.input]


async def _notify_response_completed(
    ctx: ApiKeyContext,
    body: ResponseCreateRequest,
    response: ResponseObject,
) -> None:
    await dispatch_webhook_event(
        ctx.workspace_id,
        "chat.completed",
        {
            "endpoint": "/v1/responses",
            "model": body.model,
            "response_id": response.id,
            "session_id": response.id,
            "output_text": response.output_text[:500],
            "usage": response.usage.model_dump(),
        },
    )


async def _create_response(
    body: ResponseCreateRequest,
    ctx: ApiKeyContext,
    request: Request,
) -> ResponseObject:
    session_id = request.headers.get("X-Keprix-Session-Id", "").strip() or None
    gateway_session_key = request.headers.get("X-Keprix-Session-Key", "").strip() or None
    raw_messages = _input_messages(body)
    try:
        parsed = parse_responses_input(
            raw_messages,
            instructions=body.instructions,
            session_id=session_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(exc), "code": "invalid_request_error"},
        ) from exc

    messages: list[dict] = []
    if parsed.system_prompt:
        messages.append({"role": "system", "content": parsed.system_prompt})
    messages.extend(parsed.history)
    messages.append({"role": "user", "content": parsed.user_message})

    try:
        agent_result = await run_agent_chat_completion(
            messages=messages,
            allow_tools=_tools_allowed(ctx),
            session_id=parsed.session_id,
            gateway_session_key=gateway_session_key,
        )
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

    prompt_tokens = agent_result.prompt_tokens or _estimate_tokens(json.dumps(messages))
    completion_tokens = agent_result.completion_tokens or _estimate_tokens(agent_result.final_response)
    response = ResponseObject(
        id=f"resp-{uuid.uuid4().hex[:24]}",
        created=int(time.time()),
        model=body.model,
        output_text=agent_result.final_response,
        usage=UsageInfo(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=agent_result.total_tokens or (prompt_tokens + completion_tokens),
        ),
    )
    await record_api_usage(
        ctx,
        endpoint="/v1/responses",
        model=body.model,
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
    )
    asyncio.create_task(_notify_response_completed(ctx, body, response))
    return response


async def _stream_response(
    body: ResponseCreateRequest,
    ctx: ApiKeyContext,
    request: Request,
) -> StreamingResponse:
    session_id = request.headers.get("X-Keprix-Session-Id", "").strip() or None
    gateway_session_key = request.headers.get("X-Keprix-Session-Key", "").strip() or None
    raw_messages = _input_messages(body)
    try:
        parsed = parse_responses_input(
            raw_messages,
            instructions=body.instructions,
            session_id=session_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(exc), "code": "invalid_request_error"},
        ) from exc

    messages: list[dict] = []
    if parsed.system_prompt:
        messages.append({"role": "system", "content": parsed.system_prompt})
    messages.extend(parsed.history)
    messages.append({"role": "user", "content": parsed.user_message})

    response_id = f"resp-{uuid.uuid4().hex[:24]}"
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
                session_id=parsed.session_id,
                gateway_session_key=gateway_session_key,
                stream_delta_callback=_on_delta,
                agent_ref=agent_ref,
            )
        finally:
            stream_queue.put(None)

    agent_task = asyncio.create_task(_run())

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
                chunk = {
                    "id": response_id,
                    "object": "response.chunk",
                    "created": created,
                    "model": body.model,
                    "output_text_delta": delta,
                }
                yield f"data: {json.dumps(chunk)}\n\n"
            await agent_task
            yield "data: [DONE]\n\n"
        except Exception:
            if not agent_task.done():
                agent = agent_ref[0] if agent_ref else None
                if agent is not None and hasattr(agent, "interrupt"):
                    agent.interrupt()
            raise

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/v1/responses", response_model=ResponseObject)
async def create_response(
    body: ResponseCreateRequest,
    request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
):
    started = time.perf_counter()
    check_endpoint_allowed(ctx, "/v1/responses")
    check_model_allowed(ctx, body.model)
    enforce_rate_limit(request, ctx)

    try:
        if body.stream:
            response = await _stream_response(body, ctx, request)
            await log_request(
                api_key_id=ctx.key_id,
                workspace_id=ctx.workspace_id,
                method="POST",
                path="/v1/responses",
                status_code=200,
                duration_ms=(time.perf_counter() - started) * 1000,
                request_body=body.model_dump(),
            )
            return response

        result = await _create_response(body, ctx, request)
        await log_request(
            api_key_id=ctx.key_id,
            workspace_id=ctx.workspace_id,
            method="POST",
            path="/v1/responses",
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
            path="/v1/responses",
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
            path="/v1/responses",
            status_code=500,
            duration_ms=(time.perf_counter() - started) * 1000,
            request_body=body.model_dump(),
            error_message=str(exc)[:200],
        )
        raise
