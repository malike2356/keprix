"""NotionContextLoader: pull Notion pages and databases as agent context."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ..client import NotionClient
from ..token_store import NotionTokenStore

logger = logging.getLogger(__name__)


@dataclass
class DatabaseQuery:
    database_id: str
    filter: dict | None = None
    sorts: list | None = None
    page_size: int = 20


@dataclass
class ContextBlock:
    source: str     # e.g. "notion://page_id"
    title: str
    content: str    # markdown representation


class NotionContextLoader:
    """Load Notion pages and databases as LLM-ready markdown context blocks.

    Usage::

        loader = NotionContextLoader()
        blocks = await loader.load_context(
            page_ids=["abc123"],
            database_query=DatabaseQuery(database_id="def456"),
        )
        context_str = "\\n\\n".join(b.content for b in blocks)
    """

    def __init__(self, token_store: NotionTokenStore | None = None) -> None:
        self._store = token_store or NotionTokenStore()

    def _client(self) -> NotionClient:
        return NotionClient(self._store.get())

    async def load_context(
        self,
        page_ids: list[str] | None = None,
        database_query: DatabaseQuery | None = None,
    ) -> list[ContextBlock]:
        """Load pages and/or database results as context blocks."""
        blocks: list[ContextBlock] = []
        client = self._client()
        try:
            if page_ids:
                for pid in page_ids:
                    try:
                        page = await client.get_page(pid)
                        raw_blocks = await self._fetch_all_blocks(client, pid)
                        blocks.append(ContextBlock(
                            source=f"notion://{pid}",
                            title=self._extract_title(page),
                            content=self._blocks_to_markdown(raw_blocks),
                        ))
                    except Exception as exc:
                        logger.warning("Failed to load Notion page %s: %s", pid, exc)

            if database_query:
                try:
                    results = await client.query_database(
                        database_query.database_id,
                        filter=database_query.filter,
                        sorts=database_query.sorts,
                        page_size=database_query.page_size,
                    )
                    for page in results.get("results", []):
                        blocks.append(ContextBlock(
                            source=f"notion://{page['id']}",
                            title=self._extract_title(page),
                            content=self._page_to_summary(page),
                        ))
                except Exception as exc:
                    logger.warning("Failed to query Notion database: %s", exc)
        finally:
            await client.close()
        return blocks

    async def _fetch_all_blocks(
        self, client: NotionClient, block_id: str
    ) -> list[dict[str, Any]]:
        """Fetch all blocks with pagination."""
        blocks: list[dict[str, Any]] = []
        cursor = None
        while True:
            page = await client.list_block_children(block_id, start_cursor=cursor)
            blocks.extend(page.get("results", []))
            if not page.get("has_more"):
                break
            cursor = page.get("next_cursor")
        return blocks

    @staticmethod
    def _extract_title(page: dict[str, Any]) -> str:
        props = page.get("properties", {})
        for key in ("title", "Name", "Title"):
            if key in props:
                title_items = props[key].get("title", [])
                if title_items:
                    return "".join(t.get("plain_text", "") for t in title_items)
        return page.get("id", "Untitled")

    @staticmethod
    def _rich_text_to_plain(rich_text: list[dict]) -> str:
        return "".join(t.get("plain_text", "") for t in rich_text)

    def _blocks_to_markdown(self, blocks: list[dict[str, Any]]) -> str:
        md: list[str] = []
        for block in blocks:
            btype = block.get("type", "")
            content = block.get(btype, {})
            rt = content.get("rich_text", [])
            text = self._rich_text_to_plain(rt)

            if btype == "paragraph":
                if text.strip():
                    md.append(f"{text}\n")
            elif btype == "heading_1":
                md.append(f"# {text}\n")
            elif btype == "heading_2":
                md.append(f"## {text}\n")
            elif btype == "heading_3":
                md.append(f"### {text}\n")
            elif btype == "bulleted_list_item":
                md.append(f"- {text}\n")
            elif btype == "numbered_list_item":
                md.append(f"1. {text}\n")
            elif btype == "code":
                lang = content.get("language", "")
                md.append(f"```{lang}\n{text}\n```\n")
            elif btype == "to_do":
                checked = "x" if content.get("checked") else " "
                md.append(f"- [{checked}] {text}\n")
            elif btype == "divider":
                md.append("---\n")
            elif btype == "quote":
                md.append(f"> {text}\n")

        return "".join(md)

    @staticmethod
    def _page_to_summary(page: dict[str, Any]) -> str:
        """Produce a short summary of a database page for context."""
        props = page.get("properties", {})
        lines: list[str] = []
        for key, val in props.items():
            ptype = val.get("type", "")
            if ptype == "title":
                items = val.get("title", [])
                text = "".join(t.get("plain_text", "") for t in items)
                if text:
                    lines.append(f"**{key}**: {text}")
            elif ptype == "rich_text":
                items = val.get("rich_text", [])
                text = "".join(t.get("plain_text", "") for t in items)
                if text:
                    lines.append(f"**{key}**: {text}")
            elif ptype in ("select", "status"):
                sel = val.get(ptype, {}) or {}
                if sel.get("name"):
                    lines.append(f"**{key}**: {sel['name']}")
            elif ptype == "date":
                date_val = val.get("date") or {}
                if date_val.get("start"):
                    lines.append(f"**{key}**: {date_val['start']}")
        return "\n".join(lines)
