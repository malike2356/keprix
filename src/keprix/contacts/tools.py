"""Agent-facing contact tools."""

from __future__ import annotations

from typing import Any

from keprix.contacts.search import (
    contact_get,
    contact_get_primary_email,
    contact_get_primary_phone,
    contact_search,
)

__all__ = [
    "contact_search",
    "contact_get",
    "contact_get_primary_email",
    "contact_get_primary_phone",
]


async def contact_search_tool(query: str, limit: int = 5) -> list[dict[str, Any]]:
    return await contact_search(query, limit=limit)
