"""NotionExporter: write agent findings to Notion pages."""

from __future__ import annotations

import logging
from typing import Any

from ..client import NotionClient
from ..token_store import NotionTokenStore

logger = logging.getLogger(__name__)


class NotionExporter:
    """Export agent findings, reports, and decisions to Notion pages.

    Usage::

        exporter = NotionExporter()
        url = await exporter.export_findings(
            parent_page_id="abc123",
            title="Weekly Research Brief",
            content="## Summary\\n\\nFindings from SAGE...",
        )
    """

    def __init__(self, token_store: NotionTokenStore | None = None) -> None:
        self._store = token_store or NotionTokenStore()

    def _client(self) -> NotionClient:
        return NotionClient(self._store.get())

    async def export_findings(
        self,
        parent_page_id: str,
        title: str,
        content: str,
    ) -> str:
        """Create a new Notion page with the given content. Returns the page URL."""
        blocks = self._markdown_to_blocks(content)
        async with self._client() as client:
            page = await client.create_page(
                parent_page_id=parent_page_id,
                title=title,
                children=blocks,
            )
        url = page.get("url", f"https://notion.so/{page.get('id', '').replace('-', '')}")
        logger.info("Exported to Notion: %s", url)
        return url

    async def append_to_page(self, page_id: str, content: str) -> None:
        """Append markdown content to an existing Notion page."""
        blocks = self._markdown_to_blocks(content)
        async with self._client() as client:
            for i in range(0, len(blocks), 100):
                await client.append_blocks(page_id, blocks[i:i + 100])

    # ------------------------------------------------------------------
    # Markdown -> Notion blocks
    # ------------------------------------------------------------------

    def _markdown_to_blocks(self, md: str) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        for line in md.split("\n"):
            if line.startswith("# "):
                blocks.append(self._heading_block(1, line[2:]))
            elif line.startswith("## "):
                blocks.append(self._heading_block(2, line[3:]))
            elif line.startswith("### "):
                blocks.append(self._heading_block(3, line[4:]))
            elif line.startswith("- [ ] ") or line.startswith("- [x] "):
                checked = line[3] == "x"
                blocks.append(self._todo_block(line[6:], checked))
            elif line.startswith("- "):
                blocks.append(self._bulleted_block(line[2:]))
            elif line.startswith("> "):
                blocks.append(self._quote_block(line[2:]))
            elif line.startswith("---"):
                blocks.append({"type": "divider", "divider": {}})
            elif line.strip():
                blocks.append(self._paragraph_block(line))
        return blocks

    @staticmethod
    def _rich_text(text: str) -> list[dict]:
        return [{"type": "text", "text": {"content": text}}]

    def _heading_block(self, level: int, text: str) -> dict[str, Any]:
        key = f"heading_{level}"
        return {
            "type": key,
            key: {"rich_text": self._rich_text(text)},
        }

    def _paragraph_block(self, text: str) -> dict[str, Any]:
        return {
            "type": "paragraph",
            "paragraph": {"rich_text": self._rich_text(text)},
        }

    def _bulleted_block(self, text: str) -> dict[str, Any]:
        return {
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": self._rich_text(text)},
        }

    def _todo_block(self, text: str, checked: bool = False) -> dict[str, Any]:
        return {
            "type": "to_do",
            "to_do": {"rich_text": self._rich_text(text), "checked": checked},
        }

    def _quote_block(self, text: str) -> dict[str, Any]:
        return {
            "type": "quote",
            "quote": {"rich_text": self._rich_text(text)},
        }
