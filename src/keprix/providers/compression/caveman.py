"""Caveman decompressor: expands abbreviated LLM responses.

When RTK compresses the context, the model may produce abbreviated output
(shortened code blocks, omitted repeated content). Caveman rehydrates these
using the original uncompressed context.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CavemanDecompressor:
    """Rehydrate compressed LLM responses from original context."""

    async def decompress(
        self,
        response_content: str,
        original_messages: list[dict[str, Any]],
        tool_calls: list[dict[str, Any]] | None = None,
    ) -> tuple[str, list[dict[str, Any]] | None]:
        """Expand response content using the original (pre-compression) context.

        Returns
        -------
        (expanded_content, expanded_tool_calls)
        """
        content = response_content

        # Expand abbreviated tool call names if they look truncated
        expanded_tool_calls = tool_calls
        if tool_calls:
            expanded_tool_calls = self._expand_tool_calls(tool_calls, original_messages)

        # Rehydrate incomplete code blocks from context
        if "```" in content and len(content) < 300:
            content = self._try_rehydrate_code(content, original_messages)

        return content, expanded_tool_calls

    def _expand_tool_calls(
        self,
        tool_calls: list[dict[str, Any]],
        context: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Match abbreviated tool names to full names from context."""
        known_tools: dict[str, str] = {}
        for msg in context:
            tcs = msg.get("tool_calls") or []
            for tc in tcs:
                fn = (tc.get("function") or {}).get("name", "")
                if fn:
                    # Index by prefix for abbreviation matching
                    known_tools[fn] = fn
                    known_tools[fn[:6]] = fn

        result = []
        for tc in tool_calls:
            tc = dict(tc)
            fn = tc.get("function") or {}
            name = fn.get("name", "")
            if name and name in known_tools:
                tc = dict(tc)
                tc["function"] = dict(fn)
                tc["function"]["name"] = known_tools[name]
            result.append(tc)
        return result

    def _try_rehydrate_code(
        self, content: str, context: list[dict[str, Any]]
    ) -> str:
        """If response has a code fence but seems truncated, try to find the full version."""
        for msg in reversed(context):
            msg_content = str(msg.get("content") or "")
            if "```" in msg_content and len(msg_content) > len(content):
                logger.debug("Caveman: using context code block (response appeared truncated)")
                return msg_content
        return content
