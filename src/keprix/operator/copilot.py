"""Keprix operator copilot message handling."""

from __future__ import annotations

import re
import uuid
from typing import Any, AsyncIterator

from keprix.operator import copilot_tools as tools
from keprix.operator.context_bundle import OperatorContextBundle, build_operator_context

_SYSTEM_PROMPT = """You are the Keprix operator copilot. You help instance operators review staged
mutations, interrupted playbook runs, channel health, and failed automations.

Rules:
- Never expose secrets, tokens, or raw credentials.
- Prefer read-only inspection before suggesting mutating actions.
- Mutations (approve mutation, resume playbook) require explicit operator confirmation.
- Say "Keprix" when referring to the platform; do not mention n8n unless comparing migration paths.
"""


def _chunk_text(text: str, size: int = 48) -> list[str]:
    if not text:
        return [""]
    return [text[i : i + size] for i in range(0, len(text), size)]


def _mentions_approval(text: str) -> bool:
    lowered = text.lower()
    return any(
        phrase in lowered
        for phrase in (
            "what needs my approval",
            "what needs approval",
            "awaiting approval",
            "staged mutation",
            "pending mutation",
        )
    )


def _mentions_failed_playbook(text: str) -> bool:
    lowered = text.lower()
    return any(
        phrase in lowered
        for phrase in ("why did my last playbook fail", "last playbook fail", "failed playbook", "playbook fail")
    )


def _mentions_channels(text: str) -> bool:
    lowered = text.lower()
    return any(
        phrase in lowered
        for phrase in ("which channel", "unhealthy channel", "channel is unhealthy", "channel health")
    )


def _extract_mutation_id(text: str) -> str | None:
    match = re.search(r"\b([0-9a-f]{8,32})\b", text, re.IGNORECASE)
    return match.group(1) if match else None


def _extract_run_id(text: str) -> str | None:
    match = re.search(r"\b([0-9a-f-]{8,36})\b", text, re.IGNORECASE)
    return match.group(1) if match else None


def _mentions_page_location(text: str) -> bool:
    lowered = text.lower()
    return any(
        phrase in lowered
        for phrase in (
            "what page",
            "which page",
            "where am i",
            "what am i looking at",
            "current page",
            "this page",
            "what screen",
        )
    )


def _describe_current_page(page_path: str | None, page_label: str | None) -> str:
    path = (page_path or "").strip() or "/"
    label = (page_label or "").strip()
    if label and path:
        return f"You are on {label} ({path})."
    if label:
        return f"You are on {label}."
    if path == "/":
        return "You are on the Keprix marketing/home entry (/). Open /home for the workspace home."
    return f"You are on {path} in the Keprix workspace."


async def compose_operator_reply(
    text: str,
    context: OperatorContextBundle,
    *,
    workspace_id: str = "default",
    page_path: str | None = None,
    page_label: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Return assistant text and optional side-effect events (tool calls, approvals)."""
    events: list[dict[str, Any]] = []
    lowered = text.lower()

    if _mentions_page_location(lowered):
        return (_describe_current_page(page_path, page_label), events)

    if _mentions_approval(lowered):
        staged = tools.list_staged_mutations(workspace_id)
        count = context.staged_mutations
        if count == 0:
            return ("Nothing is waiting for your approval. Staged mutation count is 0.", events)
        names = ", ".join(item["name"] for item in staged[:5])
        suffix = f" Names: {names}." if names else ""
        events.append(
            {
                "event": "tool_call",
                "name": "list_staged_mutations",
                "input": {"workspace_id": workspace_id},
                "status": "done",
                "output": str(staged),
                "mode": "dry_run",
            }
        )
        return (
            f"{count} staged mutation(s) need your approval.{suffix} "
            "Open Admin → Mutations or ask me to approve a specific mutation id after confirmation.",
            events,
        )

    if _mentions_failed_playbook(lowered):
        failed = tools.recent_failed_runs(workspace_id)
        events.append(
            {
                "event": "tool_call",
                "name": "get_playbook_run_summary",
                "input": {"workspace_id": workspace_id},
                "status": "done",
                "output": str(failed),
                "mode": "dry_run",
            }
        )
        if not failed:
            return ("No failed playbook runs are recorded in this workspace session.", events)
        last = failed[0]
        return (
            f"Latest failed run `{last['run_id']}` on `{last['graph_id']}`: {last.get('error', 'unknown error')}. "
            "Open `/playbooks` for the step timeline or ask me to resume after you fix the underlying issue.",
            events,
        )

    if _mentions_channels(lowered):
        channels = await tools.get_channel_status()
        unhealthy = [row for row in channels if row.get("status") != "healthy"]
        events.append(
            {
                "event": "tool_call",
                "name": "get_channel_status",
                "input": {},
                "status": "done",
                "output": str(channels),
                "mode": "dry_run",
            }
        )
        if not unhealthy or (len(unhealthy) == 1 and unhealthy[0].get("id") == "all"):
            return ("All monitored Keprix channels look healthy.", events)
        parts = [f"{row['name']} ({row['status']})" for row in unhealthy]
        return (f"Unhealthy channels: {', '.join(parts)}. Check Settings → Messaging or `/admin/channels`.", events)

    if "approve mutation" in lowered or "approve tool" in lowered:
        record_id = _extract_mutation_id(text)
        if not record_id:
            staged = tools.list_staged_mutations(workspace_id)
            if len(staged) == 1:
                record_id = staged[0]["id"]
            else:
                return ("Tell me which staged mutation id to approve.", events)
        pending = tools.approve_mutation(record_id, confirmed=False)
        events.append(
            {
                "event": "approval",
                "action_id": str(uuid.uuid4()),
                "action": pending["action"],
                "record_id": record_id,
                "summary": pending["message"],
            }
        )
        return (f"Approval required to activate mutation `{record_id}`. Confirm in the copilot panel.", events)

    if "resume playbook" in lowered or "resume run" in lowered:
        run_id = _extract_run_id(text)
        if not run_id:
            interrupted = tools.list_interrupted_playbooks(workspace_id)
            if len(interrupted) == 1:
                run_id = interrupted[0]["run_id"]
            else:
                return ("Tell me which playbook run id to resume.", events)
        pending = await tools.resume_playbook_run(run_id, confirmed=False)
        events.append(
            {
                "event": "approval",
                "action_id": str(uuid.uuid4()),
                "action": pending["action"],
                "run_id": run_id,
                "summary": pending["message"],
            }
        )
        return (f"Approval required to resume playbook run `{run_id}`. Confirm in the copilot panel.", events)

    return (
        "I can summarize staged mutations, interrupted playbooks, channel health, and recent failures, "
        "and I can tell you which workspace page you are on. "
        "Try: \"What needs my approval?\", \"Why did my last playbook fail?\", "
        "\"Which channel is unhealthy?\", or \"What page am I on?\".",
        events,
    )


async def stream_operator_copilot_message(
    text: str,
    *,
    workspace_id: str = "default",
    confirm_action: dict[str, Any] | None = None,
    page_path: str | None = None,
    page_label: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Yield NDJSON-shaped events for the operator copilot drawer."""
    context = await build_operator_context(workspace_id)

    if confirm_action:
        action = str(confirm_action.get("action") or "")
        try:
            if action == "approve_mutation":
                record_id = str(confirm_action.get("record_id") or "")
                result = tools.approve_mutation(record_id, confirmed=True)
                reply = f"Approved mutation `{result.get('record_id')}` ({result.get('name')})."
            elif action == "resume_playbook_run":
                run_id = str(confirm_action.get("run_id") or "")
                result = await tools.resume_playbook_run(run_id, confirmed=True)
                reply = f"Resumed playbook run `{result.get('run_id')}` (status: {result.get('status')})."
            else:
                reply = f"Unknown confirm action: {action}"
        except tools.CopilotToolError as exc:
            reply = f"Action failed: {exc}"
        for chunk in _chunk_text(reply):
            yield {"event": "text_delta", "content": chunk}
        yield {"event": "text_done"}
        yield {
            "event": "message_done",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "content": reply}],
            },
        }
        return

    reply, side_events = await compose_operator_reply(
        text,
        context,
        workspace_id=workspace_id,
        page_path=page_path,
        page_label=page_label,
    )
    for side in side_events:
        yield side
    for chunk in _chunk_text(reply):
        yield {"event": "text_delta", "content": chunk}
    yield {"event": "text_done"}

    blocks: list[dict[str, Any]] = [{"type": "text", "content": reply}]
    for side in side_events:
        if side.get("event") == "tool_call":
            blocks.append(
                {
                    "type": "tool_call",
                    "name": side.get("name"),
                    "input": side.get("input") or {},
                    "output": side.get("output"),
                    "status": side.get("status") or "done",
                    "mode": side.get("mode"),
                }
            )
        if side.get("event") == "approval":
            blocks.append(
                {
                    "type": "text",
                    "content": f"[Approval required] {side.get('summary') or side.get('action')}",
                }
            )

    yield {
        "event": "message_done",
        "message": {
            "role": "assistant",
            "content": blocks,
        },
    }


def operator_system_prompt(context: OperatorContextBundle) -> str:
    return f"{_SYSTEM_PROMPT}\n\nCurrent instance context:\n{context.summary_markdown}"
