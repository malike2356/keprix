"""Agent loop mutation hook on tool miss (Prompt 143)."""

from __future__ import annotations

import logging
import os
from typing import Any, AsyncIterator, Literal

from keprix.agent.keprix.config import get_mutation_config
from keprix.agent.keprix.governance import mutation_gates_open
from keprix.agent.keprix.mutation import get_mutation_engine
from keprix.agent.keprix.mutation_dispatch import run_tool_miss_cycle
from keprix.agent.keprix.retry import KeprixRetry
from keprix.agent.keprix.mutation_wait import (
    register_mutation_wait_now,
    unregister_mutation_wait,
    wait_for_mutation_resolution as wait_for_mutation_resolution_signal,
)
from keprix.agent.keprix.tool_dispatch import ToolDispatchResult
from keprix.agent.keprix.tool_inventory import list_runtime_tool_names
from keprix.interfaces.web_ui_stream_events import GatewayStreamEvent, ndjson_chat_event_to_gateway

logger = logging.getLogger(__name__)

MutationResolution = Literal["approved", "rejected", "timeout", "skipped"]


def chat_mutation_sidecar_enabled() -> bool:
    raw = os.environ.get("KEPRIX_CHAT_MUTATION_SIDECAR", "false")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def mutation_llm_trigger_enabled() -> bool:
    raw = os.environ.get("KEPRIX_MUTATION_LLM_TRIGGER", "false")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def mutation_approval_timeout_s() -> float:
    raw = os.environ.get("KEPRIX_MUTATION_APPROVAL_TIMEOUT", "3600")
    try:
        return float(raw)
    except ValueError:
        return 3600.0


def mutation_stream_wait_enabled() -> bool:
    raw = os.environ.get("KEPRIX_MUTATION_STREAM_WAIT_APPROVAL", "true")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _sandbox_stdout(sandbox_result: dict[str, Any]) -> str:
    return str(sandbox_result.get("stdout") or sandbox_result.get("output") or "")


def mutation_event_from_record(record: dict[str, Any]) -> dict[str, Any]:
    sandbox = record.get("sandbox_result") or {}
    return {
        "event": "mutation",
        "id": record.get("id"),
        "toolName": record.get("tool_name"),
        "approach": record.get("gap_description") or record.get("description") or "",
        "code": record.get("tool_code") or "",
        "skillYaml": record.get("skill_yaml") or "",
        "sandboxResult": _sandbox_stdout(sandbox),
        "sandboxExitCode": int(sandbox.get("exit_code") or 0),
        "sandboxStderr": str(sandbox.get("stderr") or ""),
        "status": "pending",
    }


async def evaluate_turn_tool_miss(
    *,
    task: str,
    available_tools: list[str] | None = None,
    requested_tool: str | None = None,
) -> ToolDispatchResult | None:
    """Return a not_found dispatch result when the turn needs a missing tool."""
    tools = available_tools if available_tools is not None else list_runtime_tool_names()
    tools_set = set(tools)
    text = task.strip()
    if not text:
        return None

    if requested_tool and requested_tool not in tools_set:
        return ToolDispatchResult(
            ok=False,
            error_code="not_found",
            tool_name=requested_tool,
            message=f"Unknown tool: {requested_tool}",
        )

    engine = get_mutation_engine()
    gap = await engine.detect_gap_async(text, tools)
    if not gap.has_gap:
        return None

    candidate = (gap.candidate_tool_name or "").strip()
    if candidate and candidate not in tools_set:
        return ToolDispatchResult(
            ok=False,
            error_code="not_found",
            tool_name=candidate,
            message=f"No registered tool can handle: {gap.gap_description or text}",
        )
    return None


async def wait_for_mutation_resolution(record_id: str, *, timeout_s: float | None = None) -> MutationResolution:
    return await wait_for_mutation_resolution_signal(
        record_id,
        timeout_s=timeout_s if timeout_s is not None else mutation_approval_timeout_s(),
    )  # type: ignore[return-value]


async def handle_tool_miss_stream(
    *,
    task: str,
    user_id: str,
    channel: str = "web_ui",
    session_id: str | None = None,
    requested_tool: str | None = None,
    available_tools: list[str] | None = None,
    wait_for_approval: bool = True,
) -> AsyncIterator[GatewayStreamEvent]:
    """Run mutation for a tool miss and optionally pause until approval resolves."""
    _ = user_id
    _ = channel

    allowed, block_reason = mutation_gates_open()
    if not allowed:
        yield GatewayStreamEvent(
            "text_delta",
            {"content": f"I cannot synthesise a tool right now ({block_reason}).\n"},
        )
        yield GatewayStreamEvent("text_done", {})
        return

    config = get_mutation_config()

    intro = (
        "I don't have a tool that can handle this yet. Let me create one.\n"
        if requested_tool
        else "No matching tool for this task. Synthesising one now...\n"
    )
    yield GatewayStreamEvent("text_delta", {"content": intro})
    yield GatewayStreamEvent("text_delta", {"content": "Running sandbox test...\n"})

    result = await run_tool_miss_cycle(
        task=task,
        requested_tool=requested_tool,
        session_id=session_id,
        available_tools=available_tools,
    )

    if not result.get("started"):
        reason = str(result.get("reason") or "mutation cycle did not start")
        yield GatewayStreamEvent("text_delta", {"content": f"Mutation cycle did not start: {reason}.\n"})
        yield GatewayStreamEvent("text_done", {})
        return

    if result.get("status") == "blocked":
        violations = result.get("violations") or []
        detail = "; ".join(str(item) for item in violations) or "static analysis rejected the code"
        yield GatewayStreamEvent("text_delta", {"content": f"Tool synthesis blocked: {detail}.\n"})
        yield GatewayStreamEvent("text_done", {})
        return

    if not result.get("sandbox_passed", False):
        record_data = result.get("record") or {}
        sandbox = record_data.get("sandbox_result") or {}
        stderr = str(sandbox.get("stderr") or sandbox.get("output") or "sandbox execution failed")
        exit_code = int(sandbox.get("exit_code") or 1)
        yield GatewayStreamEvent(
            "text_delta",
            {"content": f"Sandbox test failed (exit {exit_code}): {stderr}\n"},
        )
        yield GatewayStreamEvent("text_done", {})
        return

    record_data = result.get("record")
    if not isinstance(record_data, dict) or not record_data.get("id"):
        yield GatewayStreamEvent("text_delta", {"content": "Mutation completed without a pending record.\n"})
        yield GatewayStreamEvent("text_done", {})
        return

    record_id = str(record_data["id"])
    tool_name = str(record_data.get("tool_name") or requested_tool or "")
    register_wait = config.require_approval and wait_for_approval

    if register_wait:
        register_mutation_wait_now(record_id)

    mapped = ndjson_chat_event_to_gateway(mutation_event_from_record(record_data))
    if mapped is not None:
        yield mapped
    yield GatewayStreamEvent(
        "text_delta",
        {"content": "Sandbox passed. Approve the tool card to install and retry.\n"},
    )

    if not register_wait:
        yield GatewayStreamEvent("text_done", {})
        return

    try:
        resolution = await wait_for_mutation_resolution(record_id)
    finally:
        await unregister_mutation_wait(record_id)

    if resolution == "approved":
        retry = KeprixRetry()
        retry_text = await retry.retry(
            original_message=task,
            tool_name=tool_name,
            session_id=session_id,
        )
        yield GatewayStreamEvent(
            "text_delta",
            {"content": f"Tool approved and installed. Retrying your request now.\n{retry_text}\n"},
        )
    elif resolution == "rejected":
        yield GatewayStreamEvent(
            "text_delta",
            {"content": "Tool proposal rejected. I cannot complete this request without an approved tool.\n"},
        )
    else:
        yield GatewayStreamEvent(
            "text_delta",
            {"content": "Approval timed out before the tool could be installed.\n"},
        )
    yield GatewayStreamEvent("text_done", {})


async def run_agent_loop_mutation_turn(
    *,
    user_text: str,
    user_id: str,
    session_id: str | None = None,
    requested_tool: str | None = None,
    wait_for_approval: bool = True,
) -> AsyncIterator[GatewayStreamEvent]:
    """Evaluate tool miss for a chat turn and stream mutation events when needed."""
    miss = await evaluate_turn_tool_miss(
        task=user_text,
        requested_tool=requested_tool,
    )
    if miss is None or miss.error_code != "not_found":
        return

    async for event in handle_tool_miss_stream(
        task=user_text,
        user_id=user_id,
        session_id=session_id,
        requested_tool=miss.tool_name,
        wait_for_approval=wait_for_approval,
    ):
        yield event
    yield GatewayStreamEvent("done", {})
