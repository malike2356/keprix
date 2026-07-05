"""Tool protocol and base class.

Every tool in Keprix - built-in, community, or synthesised - implements this
interface. The ToolRegistry discovers and serves them to the agent engine.

A tool is defined by:
  - name: the string the LLM calls (snake_case)
  - description: what it does (shown to the LLM in the system prompt)
  - parameters: JSON Schema for the arguments
  - run(): the async implementation

Synthesised tools (Prompt 28) are generated as Python files that subclass
BaseTool and are hot-loaded into the registry on approval.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Abstract base class for all Keprix tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique snake_case identifier the LLM uses to call this tool."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """One paragraph describing what the tool does and when to use it."""
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """JSON Schema object for the tool's arguments."""
        ...

    @abstractmethod
    async def run(self, **kwargs: Any) -> str:
        """Execute the tool and return a string result for the agent."""
        ...

    def to_llm_schema(self) -> dict[str, Any]:
        """Return the OpenAI-compatible tool definition dict."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
