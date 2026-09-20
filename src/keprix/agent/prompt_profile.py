"""Prompt profiles: ``full`` (default) and ``compact`` (small local models).

Keprix's fixed prompt prefix (tool schemas + skills index + guidance) is
sized for large cloud models.  On a small local model with a tight memory
budget that prefix eats most of the usable context and makes the first
turn slow.  The ``compact`` profile trims it:

* the model-visible tool list is cut to a core allow-list (terminal, file
  tools, web, todo, memory, skill loading, ...); MCP tools and the Tool
  Search bridge tools are always kept,
* the skills index is rendered names-only with a short header.

Selection precedence: ``KEPRIX_PROMPT_PROFILE`` env var, then
``agent.prompt_profile`` in config.yaml, then ``full``.  Anything
unrecognised falls back to ``full`` so a typo never changes behaviour.

Extra tools can be kept in compact mode with ``agent.compact_tools``
(a list of tool names).  Compact mode also caps an auto-detected local
(Ollama) context window at ``agent.compact_context_cap`` tokens (default
32768; 0 disables) so a model that advertises a huge window cannot exhaust
a small machine's memory.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, FrozenSet, Iterable, List, Optional

logger = logging.getLogger(__name__)

PROFILE_ENV_VAR = "KEPRIX_PROMPT_PROFILE"
PROFILE_FULL = "full"
PROFILE_COMPACT = "compact"
PROFILES = (PROFILE_FULL, PROFILE_COMPACT)

# Tools kept in compact mode: enough to read/edit files, run commands,
# browse text, plan, remember and load skills.  Heavy or admin-only tools
# (delegation, session search, skill authoring, *_config, kanban, browser
# automation, TTS, image generation, business/CRM tools, ...) are dropped.
COMPACT_CORE_TOOLS: FrozenSet[str] = frozenset(
    {
        "terminal",
        "process",
        "read_file",
        "write_file",
        "patch",
        "search_files",
        "web_search",
        "web_extract",
        "todo",
        "clarify",
        "memory",
        "skill_view",
        "skills_list",
        "present_files",
    }
)

# Tool Search bridge tools (tools/tool_search.py) — must survive the filter
# or deferred MCP/plugin tools become unreachable.
_BRIDGE_TOOL_NAMES: FrozenSet[str] = frozenset({"tool_search", "tool_describe", "tool_call"})
_MCP_TOOL_PREFIX = "mcp_"


def _agent_config() -> Dict[str, Any]:
    try:
        from keprix_cli.config import load_config_readonly

        agent_cfg = load_config_readonly().get("agent")
        return agent_cfg if isinstance(agent_cfg, dict) else {}
    except Exception:
        return {}


def get_prompt_profile() -> str:
    """Return the active prompt profile name (``full`` or ``compact``)."""
    raw: Any = os.getenv(PROFILE_ENV_VAR)
    if raw is None or not str(raw).strip():
        raw = _agent_config().get("prompt_profile")
    if raw is None or raw == "":
        return PROFILE_FULL
    name = str(raw).strip().lower()
    if name in PROFILES:
        return name
    logger.warning(
        "Unknown prompt profile %r (expected one of %s); using %r",
        raw, ", ".join(PROFILES), PROFILE_FULL,
    )
    return PROFILE_FULL


def is_compact_profile() -> bool:
    return get_prompt_profile() == PROFILE_COMPACT


def compact_tool_allowlist() -> FrozenSet[str]:
    """Core allow-list plus any names from ``agent.compact_tools``."""
    extra: Iterable[Any] = _agent_config().get("compact_tools") or ()
    if isinstance(extra, str):
        extra = [extra]
    try:
        extra_names = {str(name).strip() for name in extra if str(name).strip()}
    except TypeError:
        extra_names = set()
    return COMPACT_CORE_TOOLS | frozenset(extra_names)


# Ceiling for the auto-detected Ollama context window in compact mode.
# Ollama reports the model's *maximum* window (often 40K-256K+) and Keprix
# requests all of it, so the KV cache alone can exhaust a small machine's
# RAM/VRAM.  32K comfortably holds the compact prompt prefix plus a working
# conversation.  Override with ``agent.compact_context_cap`` (0 = no cap).
DEFAULT_COMPACT_CONTEXT_CAP = 32_768


def compact_context_cap() -> Optional[int]:
    """Ceiling for an auto-detected local context window, or None.

    None outside the compact profile, when the cap is disabled (0), or
    when the value is unusable.  Never below the effective minimum context
    floor, so the cap cannot itself trip the minimum-context check.
    """
    if not is_compact_profile():
        return None
    raw = _agent_config().get("compact_context_cap", DEFAULT_COMPACT_CONTEXT_CAP)
    if raw is None or isinstance(raw, bool):
        raw = DEFAULT_COMPACT_CONTEXT_CAP
    try:
        cap = int(raw)
    except (TypeError, ValueError):
        cap = DEFAULT_COMPACT_CONTEXT_CAP
    if cap <= 0:
        return None
    from agent.model_metadata import get_minimum_context_length

    return max(cap, get_minimum_context_length())


def cap_local_context(detected: int) -> int:
    """Apply :func:`compact_context_cap` to an auto-detected window size."""
    cap = compact_context_cap()
    if cap and detected > cap:
        return cap
    return detected


def filter_tools_for_profile(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Apply the active profile to a list of OpenAI-format tool definitions.

    A no-op for the ``full`` profile.  In ``compact`` mode keeps allow-listed
    core tools, MCP tools (``mcp_*``) and the Tool Search bridge tools.
    """
    if not is_compact_profile():
        return tools
    allowed = compact_tool_allowlist()

    def _keep(tool: Dict[str, Any]) -> bool:
        name = (tool.get("function") or {}).get("name", "")
        return (
            name in allowed
            or name in _BRIDGE_TOOL_NAMES
            or name.startswith(_MCP_TOOL_PREFIX)
        )

    return [tool for tool in tools if _keep(tool)]
