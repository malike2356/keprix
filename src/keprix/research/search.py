"""Web search for deep research via the configured web search provider."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from keprix.research.errors import ResearchConfigError, ResearchPipelineError

SearchResult = dict[str, Any]


async def web_search(query: str, limit: int = 5) -> list[SearchResult]:
    from tools.web_tools import web_search_tool

    try:
        raw = await asyncio.to_thread(web_search_tool, query, limit)
    except Exception as exc:
        raise ResearchPipelineError(f"Web search failed: {exc}") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ResearchPipelineError("Web search returned invalid JSON.") from exc

    if not payload.get("success"):
        message = str(payload.get("error") or "Web search is not configured.")
        raise ResearchConfigError(message)

    rows = payload.get("data", {}).get("web", [])
    if not isinstance(rows, list):
        raise ResearchPipelineError("Web search returned an unexpected payload shape.")

    results: list[SearchResult] = []
    for item in rows[:limit]:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        results.append(
            {
                "title": str(item.get("title") or "").strip(),
                "url": url,
                "snippet": str(item.get("description") or item.get("snippet") or "").strip(),
            }
        )

    if not results:
        raise ResearchPipelineError(f"No web search results for query: {query!r}")

    return results
