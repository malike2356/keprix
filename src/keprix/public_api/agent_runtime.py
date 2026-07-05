"""Run the Keprix agent for public OpenAI-compatible API requests."""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from keprix.gateway.platforms.api_server import (
    _content_has_visible_payload,
    _derive_chat_session_id,
    _normalize_chat_content,
)


@dataclass
class AgentChatResult:
    final_response: str
    session_id: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    finish_reason: str = "stop"
    completed: bool = True
    partial: bool = False
    failed: bool = False
    error: str | None = None


@dataclass
class ParsedChatMessages:
    system_prompt: str | None
    user_message: str
    history: list[dict[str, Any]]
    session_id: str


def parse_openai_messages(
    messages: list[dict[str, Any]],
    *,
    session_id: str | None = None,
) -> ParsedChatMessages:
    system_prompt: str | None = None
    conversation_messages: list[dict[str, Any]] = []

    for msg in messages:
        role = str(msg.get("role") or "")
        raw_content = msg.get("content", "")
        if role == "system":
            content = _normalize_chat_content(raw_content)
            system_prompt = content if system_prompt is None else f"{system_prompt}\n{content}"
        elif role in {"user", "assistant"}:
            content = _normalize_chat_content(raw_content)
            conversation_messages.append({"role": role, "content": content})

    if not conversation_messages or conversation_messages[-1].get("role") != "user":
        raise ValueError("No user message found in messages")

    user_message = str(conversation_messages[-1].get("content", ""))
    history = conversation_messages[:-1]

    if not _content_has_visible_payload(user_message):
        raise ValueError("No user message found in messages")

    if session_id:
        resolved_session_id = session_id
        db = _ensure_session_db()
        if db is not None:
            try:
                history = db.get_messages_as_conversation(session_id)
            except Exception:
                history = history or []
    else:
        first_user = ""
        for item in conversation_messages:
            if item.get("role") == "user":
                first_user = str(item.get("content", ""))
                break
        resolved_session_id = _derive_chat_session_id(system_prompt, first_user)

    return ParsedChatMessages(
        system_prompt=system_prompt,
        user_message=user_message,
        history=history,
        session_id=resolved_session_id,
    )


def _ensure_session_db():
    try:
        from keprix_state import SessionDB

        return SessionDB()
    except Exception:
        return None


def _resolve_toolsets(*, allow_tools: bool) -> list[str]:
    from gateway.run import _load_gateway_config
    from keprix_cli.tools_config import _get_platform_tools

    user_config = _load_gateway_config()
    toolsets = sorted(_get_platform_tools(user_config, "api_server"))
    if allow_tools:
        return toolsets
    return [name for name in toolsets if name == "safe"] or []


def _create_agent(
    *,
    session_id: str,
    gateway_session_key: str | None,
    ephemeral_system_prompt: str | None,
    allow_tools: bool,
    stream_delta_callback: Callable[[str | None], None] | None = None,
    tool_start_callback=None,
    tool_complete_callback=None,
):
    from gateway.run import GatewayRunner, _load_gateway_config, _resolve_gateway_model, _resolve_runtime_agent_kwargs
    from run_agent import AIAgent

    runtime_kwargs = _resolve_runtime_agent_kwargs()
    reasoning_config = GatewayRunner._load_reasoning_config()
    model = _resolve_gateway_model()
    user_config = _load_gateway_config()
    enabled_toolsets = _resolve_toolsets(allow_tools=allow_tools)
    max_iterations = int(os.getenv("KEPRIX_MAX_ITERATIONS", "90"))
    fallback_model = GatewayRunner._load_fallback_model()

    return AIAgent(
        model=model,
        **runtime_kwargs,
        max_iterations=max_iterations,
        quiet_mode=True,
        verbose_logging=False,
        ephemeral_system_prompt=ephemeral_system_prompt or None,
        enabled_toolsets=enabled_toolsets,
        session_id=session_id,
        platform="public_api",
        stream_delta_callback=stream_delta_callback,
        tool_start_callback=tool_start_callback,
        tool_complete_callback=tool_complete_callback,
        session_db=_ensure_session_db(),
        fallback_model=fallback_model,
        reasoning_config=reasoning_config,
        gateway_session_key=gateway_session_key or session_id,
    )


def _run_agent_sync(
    *,
    parsed: ParsedChatMessages,
    gateway_session_key: str | None,
    allow_tools: bool,
    stream_delta_callback: Callable[[str | None], None] | None = None,
    tool_start_callback=None,
    tool_complete_callback=None,
    agent_ref: list[Any] | None = None,
) -> tuple[dict[str, Any], dict[str, int]]:
    from gateway.session_context import clear_session_vars, set_session_vars

    tokens = set_session_vars(
        platform="public_api",
        chat_id=parsed.session_id,
        session_key=gateway_session_key or parsed.session_id,
        session_id=parsed.session_id,
    )
    try:
        agent = _create_agent(
            session_id=parsed.session_id,
            gateway_session_key=gateway_session_key,
            ephemeral_system_prompt=parsed.system_prompt,
            allow_tools=allow_tools,
            stream_delta_callback=stream_delta_callback,
            tool_start_callback=tool_start_callback,
            tool_complete_callback=tool_complete_callback,
        )
        if agent_ref is not None:
            agent_ref[0] = agent
        result = agent.run_conversation(
            user_message=parsed.user_message,
            conversation_history=parsed.history,
            task_id=parsed.session_id or str(uuid.uuid4()),
        )
        usage = {
            "input_tokens": int(getattr(agent, "session_prompt_tokens", 0) or 0),
            "output_tokens": int(getattr(agent, "session_completion_tokens", 0) or 0),
            "total_tokens": int(getattr(agent, "session_total_tokens", 0) or 0),
        }
        effective_session_id = getattr(agent, "session_id", parsed.session_id)
        if isinstance(effective_session_id, str) and effective_session_id:
            result["session_id"] = effective_session_id
        return result, usage
    finally:
        clear_session_vars(tokens)


def _finish_reason(result: dict[str, Any]) -> str:
    is_partial = bool(result.get("partial"))
    is_failed = bool(result.get("failed"))
    completed = bool(result.get("completed", True))
    err_msg = str(result.get("error") or "")
    if is_partial and "truncat" in err_msg.lower():
        return "length"
    if is_failed or (not completed and err_msg):
        return "error"
    return "stop"


def _to_chat_result(result: dict[str, Any], usage: dict[str, int]) -> AgentChatResult:
    final_response = str(result.get("final_response") or "")
    is_partial = bool(result.get("partial"))
    is_failed = bool(result.get("failed"))
    completed = bool(result.get("completed", True))
    prompt_tokens = int(usage.get("input_tokens", 0) or 0)
    completion_tokens = int(usage.get("output_tokens", 0) or 0)
    total_tokens = int(usage.get("total_tokens", 0) or prompt_tokens + completion_tokens)
    return AgentChatResult(
        final_response=final_response,
        session_id=str(result.get("session_id") or ""),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        finish_reason=_finish_reason(result),
        completed=completed,
        partial=is_partial,
        failed=is_failed,
        error=result.get("error"),
    )


def parse_responses_input(
    raw_input: str | list[dict[str, Any]],
    *,
    instructions: str | None = None,
    session_id: str | None = None,
) -> ParsedChatMessages:
    messages: list[dict[str, Any]] = []
    if instructions:
        messages.append({"role": "system", "content": instructions})
    if isinstance(raw_input, str):
        messages.append({"role": "user", "content": raw_input})
    else:
        for item in raw_input:
            if isinstance(item, str):
                messages.append({"role": "user", "content": item})
            elif isinstance(item, dict):
                messages.append(
                    {
                        "role": str(item.get("role") or "user"),
                        "content": _normalize_chat_content(item.get("content", "")),
                    }
                )
    return parse_openai_messages(messages, session_id=session_id)


async def run_agent_chat_completion(
    *,
    messages: list[dict[str, Any]],
    allow_tools: bool = True,
    session_id: str | None = None,
    gateway_session_key: str | None = None,
    stream_delta_callback: Callable[[str | None], None] | None = None,
    tool_start_callback=None,
    tool_complete_callback=None,
    agent_ref: list[Any] | None = None,
) -> AgentChatResult:
    parsed = parse_openai_messages(messages, session_id=session_id)
    loop = asyncio.get_running_loop()
    result, usage = await loop.run_in_executor(
        None,
        lambda: _run_agent_sync(
            parsed=parsed,
            gateway_session_key=gateway_session_key,
            allow_tools=allow_tools,
            stream_delta_callback=stream_delta_callback,
            tool_start_callback=tool_start_callback,
            tool_complete_callback=tool_complete_callback,
            agent_ref=agent_ref,
        ),
    )
    chat_result = _to_chat_result(result, usage)
    if not chat_result.session_id:
        chat_result.session_id = parsed.session_id
    return chat_result
