"""Resolve Notion API tokens for RAG ingestion."""

from __future__ import annotations

import os


def resolve_notion_token(explicit: str | None = None) -> str:
    """Return a Notion integration token from the request body or environment."""
    if explicit and str(explicit).strip():
        return str(explicit).strip()

    for key in ("KEPRIX_NOTION_TOKEN", "NOTION_TOKEN", "NOTION_API_KEY"):
        value = os.environ.get(key, "").strip()
        if value:
            return value

    try:
        from keprix_cli.config import get_env_value

        for key in ("KEPRIX_NOTION_TOKEN", "NOTION_TOKEN", "NOTION_API_KEY", "notion_api_token"):
            value = get_env_value(key)
            if value and str(value).strip():
                return str(value).strip()
    except Exception:
        pass

    raise ValueError(
        "Notion token not configured. Set KEPRIX_NOTION_TOKEN or NOTION_TOKEN, "
        "or pass token in the ingest request."
    )
