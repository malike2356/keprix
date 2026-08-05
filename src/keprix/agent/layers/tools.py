"""Tools layer: tool inventory and calling rules."""

from __future__ import annotations

from typing import Any

from agent.layered_prompt import PromptSessionContext
from agent.thinking_block import get_thinking_block_instruction

TOOLS_TEMPLATE = """\
You have access to {tool_count} tools. Use them to complete tasks, not to
demonstrate capability.

Tool-calling rules:
- Call tools silently. Do not announce what you are about to do.
- After calling a tool, report the result, not the process.
- If a tool fails, report the error and try an alternative if one exists.
- Never call a tool that would violate the safety rules above.
- If a tool requires user confirmation, present the action clearly and wait."""

DEFERRED_TOOLS_CLAUSE = """\
Deferred tools are not in your active tool list. You MUST call tool_search
before using them. Do not invent parameter names. Use exact names returned
by tool_search / tool_describe."""

CONNECTOR_FIRST_CLAUSE = """\
Check connected MCP / integrations before using the browser.
If a connector fits the category (calendar, email, drive, issues, chat, crm),
use it.
If the user names a connector that is not connected, call search_mcp_registry
then suggest_connectors.
Do not invent fake MCP UIs or simulated tool outputs.
Third-party MCP tools are tagged [third_party_mcp_app]; require an explicit
connect before first use when only suggested from the registry."""


def render_tools_layer(ctx: PromptSessionContext, agent: Any) -> str:
    del ctx
    tool_names = getattr(agent, "valid_tool_names", None) or []
    tool_count = len(tool_names)
    if tool_count == 0:
        return (
            "You have no tools in this session. Answer from context and "
            "knowledge only. Do not claim to have run commands or inspected "
            "files you cannot access."
        )
    parts = [TOOLS_TEMPLATE.format(tool_count=tool_count)]
    parts.append(CONNECTOR_FIRST_CLAUSE)

    deferred_note = ""
    try:
        from tools.tool_search import BRIDGE_TOOL_NAMES, get_deferred_tool_stats

        if any(name in BRIDGE_TOOL_NAMES for name in tool_names):
            parts.append(DEFERRED_TOOLS_CLAUSE)
            stats = get_deferred_tool_stats()
            deferred_note = stats.system_note or getattr(agent, "_deferred_tools_note", "") or ""
            if not deferred_note:
                deferred_count = getattr(agent, "_deferred_tool_count", 0) or stats.deferred_count
                if deferred_count:
                    deferred_note = f"{deferred_count} tools available via tool_search"
            if deferred_note:
                parts.append(deferred_note)
    except Exception:
        pass

    thinking = get_thinking_block_instruction(agent).strip()
    if thinking:
        parts.append(thinking)
    return "\n\n".join(parts)
