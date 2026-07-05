"""LLM provider protocol.

Every provider adapter (Anthropic, OpenAI, Ollama, etc.) implements this
interface. The ProviderRouter selects the right one per request.

Providers do NOT own the conversation loop - that is the engine's job.
A provider receives a context snapshot and yields StreamChunks.
"""

from __future__ import annotations

from typing import AsyncIterator, Protocol, runtime_checkable

from keprix.agent.base import AgentContext, StreamChunk


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for any LLM provider adapter."""

    @property
    def name(self) -> str:
        """Provider identifier (e.g. 'anthropic', 'openai', 'ollama')."""
        ...

    @property
    def default_model(self) -> str:
        """Default model ID for this provider."""
        ...

    async def list_models(self) -> list[str]:
        """Return available model IDs for this provider."""
        ...

    async def stream(self, context: AgentContext) -> AsyncIterator[StreamChunk]:
        """Stream a single LLM turn and yield StreamChunks."""
        ...
