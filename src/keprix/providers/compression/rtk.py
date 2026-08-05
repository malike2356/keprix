"""RTK (Request Token Kompression): reduces token count before sending to LLM.

Adapted from OmniRoute's judgeModelClient.ts compression pipeline.
Average savings: 15-60% depending on conversation history length.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .context_dedup import ContextDeduplicator
from .token_counter import count_tokens
from .tool_output_summary import ToolOutputSummariser

logger = logging.getLogger(__name__)

STRATEGIES = ("aggressive", "balanced", "minimal", "none")


@dataclass
class CompressedRequest:
    messages: list[dict[str, Any]]
    original_tokens: int
    compressed_tokens: int

    @property
    def savings(self) -> float:
        if self.original_tokens == 0:
            return 0.0
        return 1.0 - (self.compressed_tokens / self.original_tokens)

    @property
    def savings_pct(self) -> float:
        return round(self.savings * 100, 1)

    @property
    def saved_tokens(self) -> int:
        return max(0, self.original_tokens - self.compressed_tokens)


class RTKCompressor:
    """Multi-strategy request compression pipeline."""

    def __init__(
        self,
        dedup: ContextDeduplicator | None = None,
        summariser: ToolOutputSummariser | None = None,
    ) -> None:
        self._dedup = dedup or ContextDeduplicator()
        self._summariser = summariser or ToolOutputSummariser()

    async def compress(
        self,
        messages: list[dict[str, Any]],
        strategy: str = "balanced",
        max_tokens: int | None = None,
        summarise_call_fn: Any | None = None,
    ) -> CompressedRequest:
        """Compress the outgoing message list.

        Parameters
        ----------
        messages:          OpenAI-format message list.
        strategy:          "aggressive" | "balanced" | "minimal" | "none"
        max_tokens:        Hard token budget; triggers trimming if set.
        summarise_call_fn: Optional async (prompt: str) -> str for tool summaries.
        """
        if strategy == "none":
            tokens = count_tokens(messages)
            return CompressedRequest(messages, tokens, tokens)

        original_tokens = count_tokens(messages)
        result = list(messages)

        # 1. Deduplication (all strategies except none)
        if len(result) > 6:
            result = self._dedup.deduplicate(result)

        # 2. Tool output summarisation (aggressive + balanced)
        if strategy in ("aggressive", "balanced"):
            result = await self._summariser.summarise_messages(result, summarise_call_fn)

        # 3. Merge consecutive system messages
        result = self._merge_system_messages(result)

        # 4. Context window trimming
        if max_tokens:
            result = self._trim_to_budget(result, max_tokens)

        # 5. Aggressive: also trim assistant turns older than recent N
        if strategy == "aggressive" and len(result) > 20:
            result = self._keep_recent(result, keep_pairs=8)

        compressed_tokens = count_tokens(result)
        if original_tokens > 0:
            logger.debug(
                "RTK [%s]: %d → %d tokens (%.0f%% saved)",
                strategy, original_tokens, compressed_tokens,
                (1 - compressed_tokens / original_tokens) * 100,
            )

        return CompressedRequest(result, original_tokens, compressed_tokens)

    def _merge_system_messages(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Merge consecutive system messages into one."""
        result: list[dict[str, Any]] = []
        pending_system: list[str] = []

        def flush():
            if pending_system:
                result.append({"role": "system", "content": "\n\n".join(pending_system)})
                pending_system.clear()

        for msg in messages:
            if msg.get("role") == "system":
                content = str(msg.get("content") or "")
                if content:
                    pending_system.append(content)
            else:
                flush()
                result.append(msg)

        flush()
        return result

    def _trim_to_budget(
        self, messages: list[dict[str, Any]], max_tokens: int
    ) -> list[dict[str, Any]]:
        """Remove oldest non-system messages until under token budget."""
        while count_tokens(messages) > max_tokens and len(messages) > 2:
            # Remove the oldest non-system message
            for i, msg in enumerate(messages):
                if msg.get("role") != "system":
                    messages = messages[:i] + messages[i + 1:]
                    break
            else:
                break
        return messages

    def _keep_recent(
        self, messages: list[dict[str, Any]], keep_pairs: int
    ) -> list[dict[str, Any]]:
        """Keep only the N most recent user/assistant pairs plus all system messages."""
        system_msgs = [m for m in messages if m.get("role") == "system"]
        non_system = [m for m in messages if m.get("role") != "system"]
        # Keep last keep_pairs * 2 messages (user + assistant pairs)
        trimmed = non_system[-(keep_pairs * 2):]
        return system_msgs + trimmed
