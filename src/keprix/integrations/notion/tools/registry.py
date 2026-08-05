"""Notion tool registry: MCP-compatible tool definitions with handlers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from ..client import NotionClient
from ..token_store import NotionTokenStore

ToolHandler = Callable[..., Awaitable[Any]]


@dataclass
class NotionTool:
    name: str
    description: str
    scopes: list[str]
    parameters: dict[str, Any]
    handler_name: str

    def to_mcp_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


NOTION_TOOLS: list[NotionTool] = [
    NotionTool(
        name="notion_search",
        description=(
            "Search pages and databases in Notion by text query. "
            "Returns matching page titles, IDs, and URLs."
        ),
        scopes=["read:notion"],
        parameters={
            "query": {"type": "string", "description": "Search query text"},
            "page_size": {"type": "integer", "default": 20, "maximum": 100},
            "start_cursor": {"type": "string", "description": "Pagination cursor", "optional": True},
        },
        handler_name="search",
    ),
    NotionTool(
        name="notion_get_page",
        description="Get the content and metadata of a Notion page by its ID.",
        scopes=["read:notion"],
        parameters={
            "page_id": {"type": "string", "description": "Notion page ID (32-char hex or UUID)"},
        },
        handler_name="get_page",
    ),
    NotionTool(
        name="notion_list_block_children",
        description="List all block children of a Notion block or page.",
        scopes=["read:notion"],
        parameters={
            "block_id": {"type": "string", "description": "Block ID to fetch children from"},
            "page_size": {"type": "integer", "default": 50, "maximum": 100},
            "start_cursor": {"type": "string", "description": "Pagination cursor", "optional": True},
        },
        handler_name="list_block_children",
    ),
    NotionTool(
        name="notion_query_database",
        description="Query a Notion database with optional filters and sorts.",
        scopes=["read:notion"],
        parameters={
            "database_id": {"type": "string", "description": "Notion database ID"},
            "filter": {"type": "object", "description": "Notion API filter object", "optional": True},
            "sorts": {"type": "array", "description": "Notion API sort array", "optional": True},
            "page_size": {"type": "integer", "default": 50, "maximum": 100},
            "start_cursor": {"type": "string", "description": "Pagination cursor", "optional": True},
        },
        handler_name="query_database",
    ),
    NotionTool(
        name="notion_get_database",
        description="Get metadata and schema of a Notion database by its ID.",
        scopes=["read:notion"],
        parameters={
            "database_id": {"type": "string", "description": "Notion database ID"},
        },
        handler_name="get_database",
    ),
    NotionTool(
        name="notion_append_blocks",
        description=(
            "Append block children to an existing Notion block or page. "
            "Maximum 100 blocks per request."
        ),
        scopes=["write:notion"],
        parameters={
            "block_id": {"type": "string", "description": "Target block or page ID to append to"},
            "children": {"type": "array", "description": "Array of block objects to append"},
            "after": {"type": "string", "description": "Block ID to append after", "optional": True},
        },
        handler_name="append_blocks",
    ),
]


class NotionToolDispatcher:
    """Route tool calls by name to the appropriate NotionClient method."""

    def __init__(self, token_store: NotionTokenStore | None = None) -> None:
        self._store = token_store or NotionTokenStore()

    def _client(self) -> NotionClient:
        return NotionClient(self._store.get())

    async def dispatch(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call the named tool with the given arguments."""
        tool = next((t for t in NOTION_TOOLS if t.name == tool_name), None)
        if not tool:
            raise ValueError(f"Unknown Notion tool: {tool_name!r}")

        if not self._store.is_enabled():
            raise RuntimeError(
                "Notion integration is disabled. "
                "Set KEPRIX_NOTION_ENABLED=true and NOTION_INTEGRATION_TOKEN."
            )

        async with self._client() as client:
            handler = getattr(client, tool.handler_name)
            return await handler(**arguments)
