"""Bridge workspace chat streaming to the mutation engine."""

from __future__ import annotations

from typing import Any, AsyncIterator

from keprix.agent.keprix.config import get_mutation_config
from keprix.agent.keprix.mutation import get_mutation_engine
from keprix.agent.keprix.tool_inventory import list_runtime_tool_names
from keprix.agent.keprix.governance import mutation_gates_open


def _sandbox_stdout(sandbox_result: dict[str, Any]) -> str:
    return str(sandbox_result.get("stdout") or sandbox_result.get("output") or "")


def _mutation_event_from_record(record: dict[str, Any]) -> dict[str, Any]:
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


async def maybe_run_mutation_for_chat(
    *,
    user_text: str,
    user_id: str,
    channel: str = "web_ui",
    session_id: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Yield NDJSON-shaped events when a chat message should trigger mutation."""
    _ = user_id
    _ = channel

    text = user_text.strip()
    if not text:
        return

    allowed, block_reason = mutation_gates_open()
    if not allowed:
        return

    tools = list_runtime_tool_names()
    engine = get_mutation_engine()
    gap = await engine.detect_gap_async(text, tools)
    if not gap.has_gap:
        return

    yield {
        "event": "text_delta",
        "content": "No matching tool for this task. Synthesising one now...\n",
    }
    yield {"event": "text_delta", "content": "Running sandbox test...\n"}

    config = get_mutation_config()
    if not config.enabled:
        yield {
            "event": "text_delta",
            "content": "Mutation engine was disabled before synthesis could complete.\n",
        }
        yield {"event": "text_done"}
        return

    result = await engine.run_cycle(text, tools, session_id=session_id)

    if not result.get("started"):
        reason = str(result.get("reason") or "unknown")
        yield {
            "event": "text_delta",
            "content": f"Mutation cycle did not start: {reason}.\n",
        }
        yield {"event": "text_done"}
        return

    if result.get("status") == "blocked":
        violations = result.get("violations") or []
        detail = "; ".join(str(item) for item in violations) or "static analysis rejected the code"
        yield {
            "event": "text_delta",
            "content": f"Tool synthesis blocked by static analysis: {detail}.\n",
        }
        yield {"event": "text_done"}
        return

    if not result.get("sandbox_passed", False):
        record_data = result.get("record") or {}
        sandbox = record_data.get("sandbox_result") or {}
        stderr = str(sandbox.get("stderr") or sandbox.get("output") or "sandbox execution failed")
        exit_code = int(sandbox.get("exit_code") or 1)
        yield {
            "event": "text_delta",
            "content": f"Sandbox test failed (exit {exit_code}): {stderr}\n",
        }
        yield {"event": "text_done"}
        return

    record_data = result.get("record")
    if not isinstance(record_data, dict) or not record_data.get("id"):
        yield {
            "event": "text_delta",
            "content": "Mutation cycle completed without a pending approval record.\n",
        }
        yield {"event": "text_done"}
        return

    yield _mutation_event_from_record(record_data)
    yield {
        "event": "text_delta",
        "content": "Sandbox passed. Approve the tool card to install and retry.\n",
    }
    yield {"event": "text_done"}
