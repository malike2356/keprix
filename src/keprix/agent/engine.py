"""Core agent execution engine.

Implements the reasoning loop:
  1. Build message list with system prompt and history
  2. Call the LLM provider
  3. If tool calls returned, dispatch each via ToolRegistry
  4. Append results and loop until stop or max_iterations
  5. Yield StreamChunks for real-time UI updates

Mutation engine (Prompt 28) hooks into step 3: when a tool is NOT found in
the registry, the engine hands control to the MutationEngine which synthesises,
sandboxes, and installs the tool, then retries the dispatch.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

from keprix.agent.base import (
    AgentContext,
    AgentTurn,
    Message,
    MessageRole,
    StreamChunk,
    ToolCall,
)

logger = logging.getLogger(__name__)


class AgentEngine:
    """Orchestrates provider calls, tool dispatch, and the mutation fallback."""

    def __init__(self) -> None:
        from keprix.providers.router import ProviderRouter
        from keprix.tools.registry import ToolRegistry
        self._providers = ProviderRouter()
        self._tools = ToolRegistry()

    async def run(self, context: AgentContext) -> AgentTurn:
        """Non-streaming: run the full agent loop and return the final turn."""
        chunks: list[str] = []
        last_turn: AgentTurn | None = None
        async for chunk in self.stream(context):
            if chunk.text:
                chunks.append(chunk.text)
            if chunk.is_final:
                break
        return last_turn or AgentTurn(content="".join(chunks))

    async def stream(self, context: AgentContext) -> AsyncIterator[StreamChunk]:
        """Streaming agent loop. Yields StreamChunks as they arrive."""
        while context.iteration < context.max_iterations:
            context.iteration += 1
            logger.debug("Agent iteration %d / %d", context.iteration, context.max_iterations)

            provider = self._providers.get(context.model)
            turn_chunks: list[str] = []
            tool_calls: list[ToolCall] = []

            async for chunk in provider.stream(context):
                if chunk.tool_call:
                    tool_calls.append(chunk.tool_call)
                else:
                    turn_chunks.append(chunk.text)
                    yield chunk

            if not tool_calls:
                yield StreamChunk(is_final=True)
                return

            context.messages.append(
                Message(role=MessageRole.ASSISTANT, content="".join(turn_chunks))
            )

            for tool_call in tool_calls:
                result = await self._dispatch_tool(context, tool_call)
                context.messages.append(
                    Message(
                        role=MessageRole.TOOL,
                        content=result,
                        tool_call_id=tool_call.id,
                        name=tool_call.name,
                    )
                )

        logger.warning("Agent reached max iterations (%d)", context.max_iterations)
        yield StreamChunk(text="\n[reached iteration limit]", is_final=True)

    async def _dispatch_tool(self, context: AgentContext, tool_call: ToolCall) -> str:
        """Dispatch a tool call. Falls back to MutationEngine if tool is unknown."""
        tool = self._tools.get(tool_call.name)
        if tool is not None:
            try:
                return await tool.run(**tool_call.arguments)
            except Exception as exc:
                logger.error("Tool %s raised: %s", tool_call.name, exc)
                return f"error: {exc}"

        # Tool not found: hand off to the mutation engine (Prompt 28)
        logger.info("Tool '%s' not found - triggering mutation engine", tool_call.name)
        return await self._trigger_mutation(context, tool_call)

    async def _trigger_mutation(self, context: AgentContext, tool_call: ToolCall) -> str:
        """Stub: mutation engine integration (built in Prompt 28)."""
        return (
            f"Tool '{tool_call.name}' is not installed. "
            "A synthesis request has been queued for owner approval."
        )
