"""Render live runtime data in the details panel."""

from __future__ import annotations

from keprix.tui.runtime_store import RuntimeStore


def render_runtime_details(store: RuntimeStore) -> str:
    lines = ["[runtime]"]
    lines.extend(f"  {line}" for line in store.summary_lines())
    if store.tools:
        lines.append("[tool trace]")
        for tool in store.tools[-8:]:
            args = ", ".join(f"{key}={value!r}" for key, value in sorted(tool.safe_args.items()))
            suffix = f" {args}" if args else ""
            detail = tool.error or tool.result_preview
            preview = f" - {detail[:120]}" if detail else ""
            lines.append(f"  {tool.status:<9} {tool.name}{suffix}{preview}")
    if store.subagents:
        lines.append("[subagents live]")
        for subagent in list(store.subagents.values())[-8:]:
            preview = f" - {subagent.preview[:80]}" if subagent.preview else ""
            lines.append(f"  {subagent.status:<9} {subagent.label}{preview}")
    if store.api_events:
        event = store.api_events[-1]
        lines.append("[api inspector]")
        lines.append(f"  {event.status or '-'} {event.provider}:{event.model} {event.latency_ms} ms")
        if event.error:
            lines.append(f"  error: {event.error[:160]}")
    return "\n".join(lines)

