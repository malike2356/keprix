"""Startup helpers for mutation tool synthesis (Prompt 150)."""

from __future__ import annotations

import logging
from pathlib import Path

from keprix.mutation.config import get_mutation_settings
from keprix.mutation.store import get_mutation_store

logger = logging.getLogger(__name__)


def load_mutation_tools_on_startup(workspace_id: str = "default") -> int:
    settings = get_mutation_settings()
    if not settings.enabled or not settings.tool_synthesis:
        return 0
    generated_dir = Path(settings.generated_tools_dir).expanduser()
    generated_dir.mkdir(parents=True, exist_ok=True)
    count = get_mutation_store().load_tools_on_startup(workspace_id, generated_dir)
    if count:
        logger.info("Loaded %d generated tools from mutation store", count)
    return count


async def load_mutation_tools_on_startup_async(workspace_id: str = "default") -> int:
    settings = get_mutation_settings()
    if not settings.enabled or not settings.tool_synthesis:
        return 0
    generated_dir = Path(settings.generated_tools_dir).expanduser()
    generated_dir.mkdir(parents=True, exist_ok=True)
    store = get_mutation_store()
    await store.ensure_mutation_tables()
    count = await store.load_tools_on_startup_async(workspace_id, generated_dir)
    if count:
        logger.info("Loaded %d generated tools from mutation store", count)
    return count
