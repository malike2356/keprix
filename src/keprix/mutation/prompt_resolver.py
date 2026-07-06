"""Resolve evolved workspace prompts for the agent loop (Prompt 152)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def resolve_workspace_id(agent: Any) -> str:
    workspace = getattr(agent, "_workspace_id", None)
    if isinstance(workspace, str) and workspace.strip():
        return workspace.strip()
    return "default"


def resolve_prompt_key(agent: Any) -> str:
    for attr in ("_prompt_key", "_persona_id", "_active_persona"):
        value = getattr(agent, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return "default"


def resolve_active_prompt(agent: Any) -> str | None:
    """Return active evolved prompt content for this agent, if any."""
    try:
        from keprix.mutation.config import get_mutation_settings
        from keprix.mutation.prompt_store import get_prompt_store

        settings = get_mutation_settings()
        if not settings.enabled or not settings.prompt_evolution:
            return None
        return get_prompt_store().get_active_prompt(
            resolve_workspace_id(agent),
            resolve_prompt_key(agent),
        )
    except Exception as exc:
        logger.debug("resolve_active_prompt failed: %s", exc)
        return None


def resolve_active_or_default(agent: Any, default: str) -> str:
    try:
        from keprix.mutation.config import get_mutation_settings
        from keprix.mutation.prompt_store import get_prompt_store

        settings = get_mutation_settings()
        if not settings.enabled or not settings.prompt_evolution:
            return default
        return get_prompt_store().get_active_or_default(
            resolve_workspace_id(agent),
            resolve_prompt_key(agent),
            default,
        )
    except Exception as exc:
        logger.debug("resolve_active_or_default failed: %s", exc)
        return default
