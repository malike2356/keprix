"""Streaming WEB_UI handler for workspace chat (Prompt 142)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator

from keprix.interfaces.web_ui_stream_events import (
    GatewayStreamEvent,
    ndjson_chat_event_to_gateway,
)

logger = logging.getLogger(__name__)


def chat_gateway_stream_enabled() -> bool:
    import os

    raw = os.environ.get("KEPRIX_CHAT_GATEWAY_STREAM", "true")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def web_ui_agent_loop_enabled() -> bool:
    import os

    raw = os.environ.get("KEPRIX_WEB_UI_AGENT_LOOP")
    if raw is not None:
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    from keprix.keys.local_access import effective_access_level

    return effective_access_level() in {"developer", "admin", "owner"}


def _browser_tool_stream_mode(tool_name: str) -> str | None:
    if tool_name != "browser" and not tool_name.startswith("browser_"):
        return None
    try:
        from tools.browser_tool import _get_cloud_provider, _is_local_mode

        if _get_cloud_provider() is not None:
            return "live"
        return "dry_run" if _is_local_mode() else "live"
    except Exception:
        return "dry_run"


async def _stream_slash_reply(*, message: str, user_id: str, trace_id: str, agent_id: str) -> AsyncIterator[GatewayStreamEvent]:
    from keprix.interfaces.interface_registry import _web_ui_handler

    result = await _web_ui_handler(
        agent_id=agent_id,
        trace_id=trace_id,
        message=message,
        user_id=user_id,
        workspace_id="default",
        channel_user_id=user_id,
    )
    text = str(result.get("text") or result.get("message") or "").strip()
    if not text:
        yield GatewayStreamEvent("text_done", {})
        yield GatewayStreamEvent("done", {})
        return
    for word in text.split(" "):
        yield GatewayStreamEvent("text_delta", {"content": f"{word} "})
        await asyncio.sleep(0.01)
    yield GatewayStreamEvent("text_done", {})
    yield GatewayStreamEvent("done", {})


async def _stream_mutation_turn(
    *,
    user_text: str,
    user_id: str,
    session_id: str | None,
) -> AsyncIterator[GatewayStreamEvent]:
    from keprix.agent.keprix.mutation_hook import (
        chat_mutation_sidecar_enabled,
        mutation_stream_wait_enabled,
        run_agent_loop_mutation_turn,
    )

    if chat_mutation_sidecar_enabled():
        from keprix.agent.keprix.chat_mutation_bridge import maybe_run_mutation_for_chat

        emitted = False
        async for event in maybe_run_mutation_for_chat(
            user_text=user_text,
            user_id=user_id,
            channel="web_ui",
            session_id=session_id,
        ):
            mapped = ndjson_chat_event_to_gateway(event)
            if mapped is not None:
                emitted = True
                yield mapped
        if emitted:
            yield GatewayStreamEvent("done", {})
        return

    emitted = False
    async for event in run_agent_loop_mutation_turn(
        user_text=user_text,
        user_id=user_id,
        session_id=session_id,
        wait_for_approval=mutation_stream_wait_enabled(),
    ):
        if event.event == "done":
            yield event
            return
        emitted = True
        yield event
    if emitted:
        yield GatewayStreamEvent("done", {})


async def _stream_llm_reply(
    *,
    user_text: str,
    model: str | None,
    history: list[dict[str, Any]] | None,
    user_id: str | None,
    session_id: str | None,
) -> AsyncIterator[GatewayStreamEvent]:
    from keprix.api.chat_inference import stream_chat_completion

    try:
        async for delta in stream_chat_completion(
            user_text=user_text,
            model_id=model,
            history=history,
            user_id=user_id,
            session_id=session_id,
        ):
            yield GatewayStreamEvent("text_delta", {"content": delta})
        yield GatewayStreamEvent("text_done", {})
    except Exception as exc:
        yield GatewayStreamEvent("error", {"message": str(exc)})
        error_text = f"Chat inference failed: {exc}"
        for word in error_text.split(" "):
            yield GatewayStreamEvent("text_delta", {"content": f"{word} "})
        yield GatewayStreamEvent("text_done", {})
    yield GatewayStreamEvent("done", {})


async def _stream_agent_tool_loop(
    *,
    user_text: str,
    session_id: str | None,
    history: list[dict[str, Any]] | None,
) -> AsyncIterator[GatewayStreamEvent]:
    from keprix.api.chat_inference import _provider_configured, parse_model_id

    provider, _model = parse_model_id(None)
    if not _provider_configured(provider):
        return

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[GatewayStreamEvent | None | str] = asyncio.Queue()
    tool_names: dict[str, str] = {}

    def _stream_delta(delta: str | None) -> None:
        if not delta:
            return
        loop.call_soon_threadsafe(queue.put_nowait, GatewayStreamEvent("text_delta", {"content": delta}))

    def _tool_progress(event_type: str, tool_name: str, preview: str | None = None, args: Any = None) -> None:
        normalized = str(event_type or "").lower()
        name = tool_name or "tool"
        if normalized in {"tool.started", "started", "tool_started", "start"}:
            tool_names[name] = name
            payload = dict(args) if isinstance(args, dict) else {}
            event_payload: dict[str, Any] = {"name": name, "input": payload, "status": "running"}
            mode = _browser_tool_stream_mode(name)
            if mode:
                event_payload["mode"] = mode
            loop.call_soon_threadsafe(
                queue.put_nowait,
                GatewayStreamEvent("tool_call", event_payload),
            )
            return
        if normalized in {"tool.completed", "completed", "tool_completed", "done", "finish"}:
            loop.call_soon_threadsafe(
                queue.put_nowait,
                GatewayStreamEvent(
                    "tool_call_update",
                    {"name": name, "output": str(preview or ""), "status": "done"},
                ),
            )

    def _worker() -> None:
        try:
            from run_agent import AIAgent

            agent = AIAgent(
                platform="web_ui",
                session_id=session_id or "web-ui",
                quiet_mode=True,
            )
            agent.stream_delta_callback = _stream_delta
            agent.tool_progress_callback = _tool_progress
            agent.run_conversation(
                user_message=user_text,
                conversation_history=history or [],
                task_id=session_id,
            )
        except Exception as exc:
            loop.call_soon_threadsafe(queue.put_nowait, f"error:{exc}")
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    worker = loop.run_in_executor(None, _worker)
    emitted = False
    while True:
        item = await queue.get()
        if item is None:
            break
        if isinstance(item, str) and item.startswith("error:"):
            loop.call_soon_threadsafe(queue.put_nowait, None)
            await worker
            return
        emitted = True
        yield item
    await worker
    if emitted:
        yield GatewayStreamEvent("text_done", {})
        yield GatewayStreamEvent("done", {})


async def iter_web_ui_gateway_stream(
    *,
    agent_id: str,
    trace_id: str,
    message: str,
    user_id: str,
    session_id: str | None = None,
    model: str | None = None,
    history: list[dict[str, Any]] | None = None,
) -> AsyncIterator[GatewayStreamEvent]:
    """Yield typed gateway events for a workspace chat turn."""
    text = (message or "").strip()
    if not text:
        yield GatewayStreamEvent("text_done", {})
        yield GatewayStreamEvent("done", {})
        return

    if text.startswith("/"):
        async for event in _stream_slash_reply(message=text, user_id=user_id, trace_id=trace_id, agent_id=agent_id):
            yield event
        return

    async for event in _stream_mutation_turn(user_text=text, user_id=user_id, session_id=session_id):
        yield event
        if event.event == "done":
            return

    if web_ui_agent_loop_enabled():
        agent_events: list[GatewayStreamEvent] = []
        async for event in _stream_agent_tool_loop(
            user_text=text,
            session_id=session_id,
            history=history,
        ):
            agent_events.append(event)
        if agent_events:
            for event in agent_events:
                yield event
            return
        logger.debug("web UI agent loop produced no events; falling back to LLM stream")

    async for event in _stream_llm_reply(
        user_text=text,
        model=model,
        history=history,
        user_id=user_id,
        session_id=session_id,
    ):
        yield event


async def _web_ui_handler(*, agent_id: str, trace_id: str, message: str = "", stream: bool = False, **kwargs: Any):
    if stream:
        return iter_web_ui_gateway_stream(
            agent_id=agent_id,
            trace_id=trace_id,
            message=message or kwargs.get("text", ""),
            user_id=str(kwargs.get("user_id") or "web"),
            session_id=kwargs.get("session_id"),
            model=kwargs.get("model"),
            history=kwargs.get("history"),
        )

    from keprix.slash.executor import build_context, execute_context
    from keprix.slash.renderers import render_webchat

    text = message or kwargs.get("text", "/status")
    ctx = build_context(
        raw_text=text if text.startswith("/") else f"/{text}",
        user_id=kwargs.get("user_id", "web"),
        workspace_id=kwargs.get("workspace_id", "default"),
        channel="webchat",
        channel_user_id=kwargs.get("channel_user_id", "web"),
        role=kwargs.get("role"),
        request_id=trace_id,
    )
    result = await execute_context(ctx)
    return render_webchat(result) | {"trace_id": trace_id, "agent_id": agent_id}
