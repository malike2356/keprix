"""Unified compression pipeline: RTK + Caveman in one interface."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .caveman import CavemanDecompressor
from .rtk import CompressedRequest, RTKCompressor

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    strategy: str = "balanced"  # none | minimal | balanced | aggressive
    max_tokens: int | None = None
    enabled: bool = True


class CompressionPipeline:
    """RTK request compression + Caveman response decompression."""

    def __init__(
        self,
        rtk: RTKCompressor | None = None,
        caveman: CavemanDecompressor | None = None,
        config: PipelineConfig | None = None,
    ) -> None:
        self._rtk = rtk or RTKCompressor()
        self._caveman = caveman or CavemanDecompressor()
        self._config = config or PipelineConfig()

    async def compress_request(
        self,
        messages: list[dict[str, Any]],
        strategy: str | None = None,
        max_tokens: int | None = None,
        summarise_call_fn: Any | None = None,
    ) -> CompressedRequest:
        """Compress outgoing messages. Pass-through when disabled."""
        if not self._config.enabled:
            from .token_counter import count_tokens
            t = count_tokens(messages)
            return CompressedRequest(messages, t, t)

        return await self._rtk.compress(
            messages=messages,
            strategy=strategy or self._config.strategy,
            max_tokens=max_tokens or self._config.max_tokens,
            summarise_call_fn=summarise_call_fn,
        )

    async def decompress_response(
        self,
        content: str,
        original_messages: list[dict[str, Any]],
        tool_calls: list[dict[str, Any]] | None = None,
    ) -> tuple[str, list[dict[str, Any]] | None]:
        """Expand compressed response content."""
        if not self._config.enabled:
            return content, tool_calls

        return await self._caveman.decompress(content, original_messages, tool_calls)

    def disable(self) -> None:
        self._config.enabled = False

    def enable(self, strategy: str = "balanced") -> None:
        self._config.enabled = True
        self._config.strategy = strategy
