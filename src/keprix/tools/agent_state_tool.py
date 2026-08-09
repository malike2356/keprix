"""Agent project-state tool: durable context, chunking, and human checkpoints."""

from __future__ import annotations

import json
from typing import Any

from tools.registry import registry, tool_error

from keprix.agent_state.checkpoint_validator import (
    CheckpointBlockedError,
    CheckpointValidator,
)
from keprix.agent_state.context_state import ContextStateStore
from keprix.agent_state.task_decomposer import TaskDecomposer


def _store(base_dir: str | None = None) -> ContextStateStore:
    return ContextStateStore(root=base_dir) if base_dir else ContextStateStore()


def agent_state_tool(
    action: str,
    session_id: str,
    *,
    task_description: str | None = None,
    step_id: str | None = None,
    status: str | None = None,
    output: str | None = None,
    decision: str | None = None,
    constraint: str | None = None,
    error: str | None = None,
    chunk_id: str | None = None,
    summary: str | dict[str, Any] | None = None,
    human_signal: str | None = None,
    files_changed: list[str] | None = None,
    steps: list[str] | None = None,
    base_dir: str | None = None,
) -> str:
    """Dispatch durable agent-state actions. Returns JSON."""
    action = (action or "").strip().lower()
    session_id = (session_id or "").strip()
    if not session_id:
        return tool_error("session_id is required")
    if not action:
        return tool_error("action is required")

    store = _store(base_dir)
    validator = CheckpointValidator(store)
    decomposer = TaskDecomposer(store)

    try:
        if action in {"create", "create_state"}:
            state = store.create_state_file(
                session_id,
                task_description or "Untitled task",
                steps=steps,
                constraints=[constraint] if constraint else None,
                decisions=[decision] if decision else None,
            )
            return json.dumps({"ok": True, "state": state.to_dict()}, ensure_ascii=False)

        if action in {"read", "resume"}:
            payload = store.resume(session_id)
            payload["injection"] = store.format_for_injection(session_id)
            return json.dumps({"ok": True, **payload}, ensure_ascii=False)

        if action in {"update", "update_step"}:
            try:
                validator.assert_can_proceed(session_id)
            except CheckpointBlockedError as exc:
                return tool_error(str(exc))
            state = store.update_state_file(
                session_id,
                step_id=step_id,
                status=status,
                output=output,
                decision=decision,
                constraint=constraint,
                error=error,
                files_changed=files_changed,
            )
            return json.dumps({"ok": True, "state": state.to_dict()}, ensure_ascii=False)

        if action == "decompose":
            state = decomposer.decompose(session_id)
            return json.dumps(
                {
                    "ok": True,
                    "chunks": [c.to_dict() for c in state.chunks],
                    "state": state.to_dict(),
                },
                ensure_ascii=False,
            )

        if action == "start_chunk":
            if not chunk_id:
                return tool_error("chunk_id is required for start_chunk")
            state = validator.start_chunk(session_id, chunk_id)
            return json.dumps({"ok": True, "state": state.to_dict()}, ensure_ascii=False)

        if action == "pause_for_review":
            if not chunk_id:
                return tool_error("chunk_id is required for pause_for_review")
            payload = validator.pause_for_review(session_id, chunk_id, summary=summary)
            return json.dumps({"ok": True, **payload}, ensure_ascii=False)

        if action == "validate_chunk":
            if not chunk_id:
                return tool_error("chunk_id is required for validate_chunk")
            payload = validator.validate_chunk_output(session_id, chunk_id)
            return json.dumps({"ok": True, **payload}, ensure_ascii=False)

        if action == "approve":
            if not chunk_id:
                return tool_error("chunk_id is required for approve")
            state = validator.approve(
                session_id, chunk_id, human_signal=human_signal or "approved"
            )
            return json.dumps({"ok": True, "state": state.to_dict()}, ensure_ascii=False)

        if action == "reject":
            if not chunk_id:
                return tool_error("chunk_id is required for reject")
            state = validator.reject(
                session_id, chunk_id, human_signal=human_signal or "rejected"
            )
            return json.dumps({"ok": True, "state": state.to_dict()}, ensure_ascii=False)

        if action == "merge":
            if not chunk_id:
                return tool_error("chunk_id is required for merge")
            state = validator.merge_approved_chunk(session_id, chunk_id)
            return json.dumps({"ok": True, "state": state.to_dict()}, ensure_ascii=False)

        if action == "rollback":
            if not chunk_id:
                return tool_error("chunk_id is required for rollback")
            state = validator.rollback_chunk(session_id, chunk_id)
            return json.dumps({"ok": True, "state": state.to_dict()}, ensure_ascii=False)

        return tool_error(f"Unknown action '{action}'")
    except FileNotFoundError as exc:
        return tool_error(str(exc))
    except CheckpointBlockedError as exc:
        return tool_error(str(exc))
    except Exception as exc:  # noqa: BLE001 - surface to agent as tool error
        return tool_error(f"{type(exc).__name__}: {exc}")


def check_agent_state_requirements() -> bool:
    return True


AGENT_STATE_SCHEMA = {
    "name": "agent_state",
    "description": (
        "Durable project state for long multi-step agent work. "
        "ALWAYS call action=read at session start. "
        "Never run more than 7 steps in one chunk/session without a human checkpoint. "
        "After each completed step call action=update. "
        "After each chunk call pause_for_review and HALT until the human approves "
        "(action=approve with human_signal), then merge before the next chunk.\n\n"
        "Actions: create, read, update, decompose, start_chunk, pause_for_review, "
        "validate_chunk, approve, reject, merge, rollback."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "create|read|update|decompose|start_chunk|pause_for_review|"
                "validate_chunk|approve|reject|merge|rollback",
            },
            "session_id": {
                "type": "string",
                "description": "Stable id for this long-running task (reuse across sessions).",
            },
            "task_description": {"type": "string"},
            "step_id": {"type": "string"},
            "status": {
                "type": "string",
                "description": "pending|in_progress|completed|blocked|failed",
            },
            "output": {"type": "string"},
            "decision": {"type": "string"},
            "constraint": {"type": "string"},
            "error": {"type": "string"},
            "chunk_id": {"type": "string"},
            "summary": {"type": "string"},
            "human_signal": {
                "type": "string",
                "description": "Required confirmation text when approving a checkpoint.",
            },
            "files_changed": {
                "type": "array",
                "items": {"type": "string"},
            },
            "steps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional explicit step list when creating state.",
            },
        },
        "required": ["action", "session_id"],
    },
}

registry.register(
    name="agent_state",
    toolset="agent_state",
    schema=AGENT_STATE_SCHEMA,
    handler=lambda args, **kw: agent_state_tool(
        action=str(args.get("action") or ""),
        session_id=str(args.get("session_id") or ""),
        task_description=args.get("task_description"),
        step_id=args.get("step_id"),
        status=args.get("status"),
        output=args.get("output"),
        decision=args.get("decision"),
        constraint=args.get("constraint"),
        error=args.get("error"),
        chunk_id=args.get("chunk_id"),
        summary=args.get("summary"),
        human_signal=args.get("human_signal"),
        files_changed=args.get("files_changed"),
        steps=args.get("steps"),
        base_dir=kw.get("base_dir") or args.get("base_dir"),
    ),
    check_fn=check_agent_state_requirements,
    emoji="state",
)
