"""Unified tool-miss dispatch into MutationEngine.run_cycle (Prompt 193)."""

from __future__ import annotations

from typing import Any

from keprix.agent.keprix.config import get_mutation_config
from keprix.agent.keprix.governance import mutation_gates_open
from keprix.agent.keprix.mutation import get_mutation_engine
from keprix.agent.keprix.tool_inventory import list_runtime_tool_names


async def run_tool_miss_cycle(
    *,
    task: str,
    requested_tool: str | None = None,
    session_id: str | None = None,
    available_tools: list[str] | None = None,
) -> dict[str, Any]:
    """Single entry point for tool-miss mutation synthesis."""
    allowed, block_reason = mutation_gates_open()
    if not allowed:
        return {"started": False, "reason": block_reason or "mutation_gates_closed"}

    config = get_mutation_config()
    if not config.enabled:
        return {"started": False, "reason": "mutation_disabled"}

    tools = available_tools if available_tools is not None else list_runtime_tool_names()
    engine = get_mutation_engine()
    return await engine.run_cycle(
        task,
        tools,
        session_id=session_id,
        trigger="tool_miss",
        requested_tool=requested_tool,
    )


def sync_message_from_cycle_result(result: dict[str, Any], *, tool_name: str) -> str | None:
    """Map run_cycle output to conversation-loop injection text."""
    if not result.get("started"):
        reason = str(result.get("reason") or "")
        if reason in {"", "no_gap", "mutation_disabled"}:
            return None
        return (
            f"Tool '{tool_name}' was not found and mutation could not start: {reason}. "
            "Use an available tool or rephrase the task."
        )

    if result.get("status") == "blocked":
        violations = result.get("violations") or []
        detail = "; ".join(str(item) for item in violations) or "static analysis rejected the code"
        return (
            f"Tool '{tool_name}' was not found and could not be synthesized: {detail}. "
            "Use an available tool or rephrase the task."
        )

    if not result.get("sandbox_passed", False):
        record_data = result.get("record") or {}
        sandbox = record_data.get("sandbox_result") or {}
        stderr = str(sandbox.get("stderr") or sandbox.get("output") or "sandbox execution failed")
        return (
            f"Tool '{tool_name}' was not found and sandbox test failed: {stderr}. "
            "Use an available tool or rephrase the task."
        )

    synthesized_name = str(result.get("tool_name") or tool_name)
    config = get_mutation_config()
    if not config.require_approval:
        return (
            f"Tool '{synthesized_name}' was not found. A replacement was synthesized "
            "and is now available. Retry the task."
        )
    return (
        f"Tool '{synthesized_name}' was synthesized but requires operator approval "
        "before it can be used."
    )


async def finalize_sync_tool_miss(
    result: dict[str, Any],
    *,
    tool_name: str,
    confidence: float = 1.0,
) -> str | None:
    """Complete sync tool-miss handling, including optional auto-approval."""
    from keprix.mutation.config import get_mutation_settings

    message = sync_message_from_cycle_result(result, tool_name=tool_name)
    if not result.get("started"):
        return message

    record_id = result.get("record_id")
    synthesized_name = str(result.get("tool_name") or tool_name)
    if not result.get("sandbox_passed") or not record_id:
        return message

    settings = get_mutation_settings()
    config = get_mutation_config()
    should_auto = not config.require_approval or confidence >= settings.auto_approve_threshold
    if not should_auto:
        return message

    approval = await get_mutation_engine().approve(
        str(record_id),
        approver_id="mutation_auto",
        channel="web_ui",
    )
    if approval is None:
        return message
    return (
        f"Tool '{synthesized_name}' was not found. A replacement was synthesized "
        "and is now available. Retry the task."
    )
