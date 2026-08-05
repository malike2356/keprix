"""Summarise long tool outputs before sending to the LLM.

Tool outputs > TOKEN_THRESHOLD tokens are replaced with concise summaries.
Uses a cheap/fast provider when available, otherwise falls back to truncation.
"""

from __future__ import annotations

import logging
from typing import Any

from .token_counter import count_tokens

logger = logging.getLogger(__name__)

TOKEN_THRESHOLD = 1000  # summarise tool outputs longer than this


class ToolOutputSummariser:
    """Replace oversized tool outputs with compact summaries."""

    def __init__(
        self,
        token_threshold: int = TOKEN_THRESHOLD,
        truncate_fallback: bool = True,
    ) -> None:
        self._threshold = token_threshold
        self._truncate = truncate_fallback

    async def summarise_messages(
        self,
        messages: list[dict[str, Any]],
        call_fn: Any | None = None,  # (prompt) -> str
    ) -> list[dict[str, Any]]:
        """Process message list, summarising oversized tool outputs."""
        result: list[dict[str, Any]] = []
        for msg in messages:
            if msg.get("role") in ("tool", "function"):
                content = str(msg.get("content") or "")
                tokens = count_tokens(content)
                if tokens > self._threshold:
                    msg = dict(msg)
                    msg["content"] = await self._compress(content, call_fn)
            result.append(msg)
        return result

    async def _compress(self, content: str, call_fn: Any | None) -> str:
        if call_fn is not None:
            try:
                prompt = (
                    f"Summarise this tool output in 2-3 sentences, "
                    f"keeping key values and results:\n\n{content[:4000]}"
                )
                summary = await call_fn(prompt)
                return f"[Summary] {summary}"
            except Exception as exc:
                logger.debug("Tool output summariser: call_fn failed: %s", exc)

        if self._truncate:
            # Truncation fallback: keep first + last 200 chars
            head = content[:200]
            tail = content[-200:]
            skipped = len(content) - 400
            return f"{head}\n... [{skipped} chars omitted] ...\n{tail}"

        return content
