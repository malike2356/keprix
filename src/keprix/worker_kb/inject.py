"""Inject worker KB context into Carina/Aiva agent turns (K03)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def last_user_text(messages: list[dict[str, Any]] | None) -> str:
    for msg in reversed(messages or []):
        if not isinstance(msg, dict):
            continue
        if str(msg.get("role") or "").lower() != "user":
            continue
        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(str(block.get("text") or ""))
                elif isinstance(block, str):
                    parts.append(block)
            joined = "\n".join(p for p in parts if p.strip()).strip()
            if joined:
                return joined
    return ""


async def inject_worker_kb_into_system_prompt(
    *,
    system_prompt: str,
    workspace_id: str,
    worker_id: str | None,
    messages: list[dict[str, Any]] | None,
    limit: int = 5,
) -> str:
    """Append top-N worker KB chunks for the latest user message."""
    wid = (worker_id or "").strip()
    if not wid or not workspace_id:
        return system_prompt or ""
    query = last_user_text(messages)
    if not query:
        return system_prompt or ""
    try:
        from keprix.worker_kb.service import get_worker_kb_service

        block = await get_worker_kb_service().search_context(
            workspace_id,
            wid,
            query,
            limit=limit,
        )
    except Exception:
        logger.exception("worker KB inject failed for worker=%s", wid)
        return system_prompt or ""
    if not block:
        return system_prompt or ""
    base = (system_prompt or "").rstrip()
    return f"{base}\n\n{block}" if base else block
