"""Keprix operator copilot message handling."""

from __future__ import annotations

import re
import uuid
from typing import Any, AsyncIterator

from keprix.operator import copilot_tools as tools
from keprix.operator.context_bundle import OperatorContextBundle, build_operator_context
from keprix.operator.platform_knowledge import find_modules_for_path

_SYSTEM_PROMPT = """You are the Keprix operator copilot for this self-hosted instance.

You know the full Keprix platform surface: navigation, modules catalog, settings,
mutations, playbooks, channels, readiness, billing, governance, developer tools,
memory/RAG, Agent OS, Channel Shield, and related operator workflows.

Rules:
- Never expose secrets, tokens, API keys, or raw credentials.
- Prefer read-only inspection before suggesting mutating actions.
- Mutations (approve mutation, resume playbook) require explicit operator confirmation.
- Answer with concrete Keprix routes when pointing operators somewhere.
- Say "Keprix" when referring to the platform; do not mention n8n unless comparing migration paths.
- When self-knowledge RAG hits are provided, ground answers in them and the live operator snapshot.
- Treat runtime registries as authoritative for current version, routes, module status, and readiness.
- Treat indexed docs and source code as supporting evidence that may be stale.
- If evidence is missing or conflicts, say what could not be verified. Never guess.
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


def _mentions_modules(text: str) -> bool:
    lowered = text.lower()
    return any(
        phrase in lowered
        for phrase in ("module catalog", "which modules", "list modules", "settings/modules", "what modules")
    )


def _mentions_readiness(text: str) -> bool:
    lowered = text.lower()
    return any(
        phrase in lowered
        for phrase in ("readiness", "ship gate", "is this instance ready", "failing checks")
    )


def _mentions_navigation(text: str) -> bool:
    lowered = text.lower()
    return any(
        phrase in lowered
        for phrase in (
            "where is",
            "where do i find",
            "how do i open",
            "nav for",
            "navigation",
            "sidebar",
            "which menu",
        )
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
            "explain this page",
        )
    )


def _describe_current_page(
    page_path: str | None,
    page_label: str | None,
    context: OperatorContextBundle,
) -> str:
    path = (page_path or "").strip() or "/"
    nav = context.current_page or tools.resolve_route(path)
    label = (page_label or "").strip() or (nav or {}).get("label") or ""
    group = (nav or {}).get("group_label") or ""
    parts: list[str] = []
    if label and path:
        parts.append(f"You are on **{label}** (`{path}`).")
    elif label:
        parts.append(f"You are on **{label}**.")
    elif path == "/":
        parts.append("You are on the Keprix marketing/home entry (`/`). Open `/home` for the workspace home.")
    else:
        parts.append(f"You are on `{path}` in the Keprix workspace.")
    if group:
        parts.append(f"Nav group: {group}.")
    related = find_modules_for_path(path)
    if related:
        names = ", ".join(f"{item['name']} (`{item['gui_href']}`)" for item in related[:4])
        parts.append(f"Related modules: {names}.")
    parts.append("Ask about any Keprix module, route, readiness check, mutation, or playbook from here.")
    return " ".join(parts)


def _tool_event(name: str, output: Any, *, input_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "event": "tool_call",
        "name": name,
        "input": input_payload or {},
        "status": "done",
        "output": str(output)[:4_000],
        "mode": "dry_run",
    }


def _answer_from_knowledge(query: str, markdown: str, *, preface: str = "") -> str:
    if not markdown.strip():
        return (
            f"{preface}"
            "I could not retrieve indexed self-knowledge for that yet. "
            "Try `/settings/modules`, `/developer/module-inventory`, or ask about approvals, "
            "playbooks, channels, readiness, or the current page."
        ).strip()
    # Keep operator-facing answer compact: preface + truncated knowledge block.
    body = markdown.strip()
    if len(body) > 2_400:
        body = body[:2_400].rstrip() + "\n[truncated]"
    if preface:
        return f"{preface}\n\n{body}"
    return (
        f"Here is the relevant indexed Keprix knowledge for \"{query.strip()}\":\n\n{body}\n\n"
        "Evidence: indexed product documentation and code. Current runtime facts take precedence.\n\n"
        "Ask a follow-up about a route, module, or operator action if you want next steps."
    )


def _answer_from_live_facts(live: dict[str, Any]) -> str | None:
    if live.get("version_requested"):
        return (
            f"This Keprix instance is running version `{live.get('installed_version') or 'unknown'}`. "
            "Evidence: live runtime version registry."
        )
    matches = live.get("module_matches") or []
    if not live.get("module_requested") or not matches:
        return None
    lines = ["I found these matches in the live Keprix module catalog:"]
    for item in matches[:6]:
        route = f" Route: `{item['route']}`." if item.get("route") else " No dedicated GUI route is registered."
        lines.append(f"- **{item['name']}**: status `{item['status']}`.{route} {item['description']}")
    lines.append("Evidence: live module registry. Status describes the current installed build.")
    return "\n".join(lines)


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
        return (_describe_current_page(page_path, page_label, context), events)

    if _mentions_approval(lowered):
        staged = tools.list_staged_mutations(workspace_id)
        count = context.staged_mutations
        if count == 0:
            return ("Nothing is waiting for your approval. Staged mutation count is 0.", events)
        names = ", ".join(item["name"] for item in staged[:5])
        suffix = f" Names: {names}." if names else ""
        events.append(_tool_event("list_staged_mutations", staged, input_payload={"workspace_id": workspace_id}))
        return (
            f"{count} staged mutation(s) need your approval.{suffix} "
            "Open Admin → Mutations or ask me to approve a specific mutation id after confirmation.",
            events,
        )

    if _mentions_failed_playbook(lowered):
        failed = tools.recent_failed_runs(workspace_id)
        events.append(_tool_event("get_playbook_run_summary", failed, input_payload={"workspace_id": workspace_id}))
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
        events.append(_tool_event("get_channel_status", channels))
        if not unhealthy or (len(unhealthy) == 1 and unhealthy[0].get("id") == "all"):
            return ("All monitored Keprix channels look healthy.", events)
        parts = [f"{row['name']} ({row['status']})" for row in unhealthy]
        return (f"Unhealthy channels: {', '.join(parts)}. Check Settings → Messaging or `/admin/channels`.", events)

    if _mentions_modules(lowered):
        summary = tools.get_modules_catalog_summary()
        events.append(_tool_event("get_modules_catalog_summary", summary))
        counts = summary.get("counts") or {}
        highlights = summary.get("highlights") or []
        names = ", ".join(f"{item['name']} (`{item['gui_href']}`)" for item in highlights[:6])
        return (
            f"Modules catalog: {counts.get('available', 0)} available GUI, "
            f"{counts.get('partial', 0)} partial, {counts.get('cli_api', 0)} CLI/API-only "
            f"(version {summary.get('installed_version') or context.installed_version}). "
            f"Open `/settings/modules`. Highlights: {names or 'see catalog'}."
            ,
            events,
        )

    if _mentions_readiness(lowered):
        summary = tools.get_instance_readiness_summary()
        events.append(_tool_event("get_instance_readiness_summary", summary))
        failing = summary.get("failing") or []
        if not failing:
            return (
                f"Readiness overall is `{summary.get('overall', 'unknown')}`. No failing checks in the current report. "
                "Open `/admin/readiness` for the full matrix.",
                events,
            )
        bits = [f"{item['title']} ({item['status']})" for item in failing[:5]]
        return (
            f"Readiness overall is `{summary.get('overall', 'unknown')}`. Attention: {', '.join(bits)}. "
            "Open `/admin/readiness` for fix paths.",
            events,
        )

    if _mentions_navigation(lowered):
        nav = tools.get_navigation_map()
        events.append(_tool_event("get_navigation_map", {"count": len(nav)}))
        knowledge = await tools.search_keprix_knowledge(text, limit=5)
        events.append(_tool_event("search_keprix_knowledge", knowledge.get("sources") or [], input_payload={"query": text}))
        preface = (
            f"Keprix exposes {len(nav)} curated navigation routes. "
            "Use the sidebar groups (Workspace, Data, Research, Apps, Automations, Security, Commerce, Admin). "
        )
        return (_answer_from_knowledge(text, knowledge.get("markdown") or context.platform_map_markdown, preface=preface), events)

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

    # Default: platform knowledge search + live snapshot (full-platform answers).
    knowledge = await tools.search_keprix_knowledge(text, limit=6)
    events.append(
        _tool_event(
            "search_keprix_knowledge",
            {"sources": knowledge.get("sources") or [], "hit_count": knowledge.get("hit_count", 0)},
            input_payload={"query": text},
        )
    )
    live_answer = _answer_from_live_facts(knowledge.get("live") or {})
    if live_answer:
        return (live_answer, events)
    preface = (
        f"Live ops: staged={context.staged_mutations}, interrupted playbooks={context.interrupted_playbooks}, "
        f"channel issues={len(context.channel_issues)}, readiness={context.readiness_overall}, "
        f"version={context.installed_version}.\n"
    )
    markdown = knowledge.get("markdown") or ""
    if not markdown and context.platform_map_markdown:
        markdown = context.platform_map_markdown
    if markdown:
        return (_answer_from_knowledge(text, markdown, preface=preface), events)
    return (
        preface
        + "I can help with the full Keprix platform: modules, navigation, readiness, mutations, "
        "playbooks, channels, settings, billing, and governance. "
        'Try: "What page am I on?", "What modules are available?", "Is readiness green?", '
        '"What needs my approval?", or ask how a feature works.',
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
    context = await build_operator_context(
        workspace_id,
        detail="full",
        page_path=page_path,
        page_label=page_label,
    )

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
    parts = [_SYSTEM_PROMPT, "", "Current instance context:", context.summary_markdown]
    if context.platform_map_markdown:
        parts.extend(["", context.platform_map_markdown])
    return "\n".join(parts)
