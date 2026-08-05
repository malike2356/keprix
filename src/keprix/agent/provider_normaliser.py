"""Provider normalisation for tool definitions and tool calls."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from agent.tool_description import generate_natural_description
from agent.tool_schema import ToolSchema, schemas_from_openai_tools
from agent.transports.types import ToolCall, build_tool_call

logger = logging.getLogger(__name__)

_OPENAI_FAMILY = frozenset(
    {"openai", "deepseek", "groq", "together", "openrouter", "xai", "mistral"}
)


@dataclass
class ToolResult:
    tool_call_id: str | None
    name: str
    content: str
    is_error: bool = False


class ProviderNormaliser:
    """Converts tool schemas and calls between provider formats."""

    def __init__(self, provider: str, tools: list[ToolSchema]):
        self.provider = (provider or "").lower().strip()
        self.tools = tools
        self._schema_by_name = {tool.name: tool for tool in tools if tool.name}

    @classmethod
    def from_openai_tools(cls, provider: str, openai_tools: list[dict[str, Any]]) -> ProviderNormaliser:
        return cls(provider, schemas_from_openai_tools(openai_tools))

    def get_tool_definitions(self) -> list[Any]:
        if self.provider == "anthropic":
            return [tool.to_anthropic() for tool in self.tools]
        if self.provider in _OPENAI_FAMILY:
            return [tool.to_openai() for tool in self.tools]
        if self.provider in ("google", "gemini"):
            declarations = [tool.to_google()["functionDeclarations"][0] for tool in self.tools]
            return [{"functionDeclarations": declarations}] if declarations else []
        if self.provider == "bedrock":
            return [tool.to_bedrock() for tool in self.tools]
        return [generate_natural_description(tool) for tool in self.tools]

    def schema_for(self, name: str) -> ToolSchema | None:
        return self._schema_by_name.get(name)

    def parse_tool_call(self, raw_call: dict[str, Any]) -> ToolCall:
        if self.provider == "anthropic":
            return self._parse_anthropic_tool_call(raw_call)
        if self.provider in _OPENAI_FAMILY:
            return self._parse_openai_tool_call(raw_call)
        if self.provider in ("google", "gemini"):
            return self._parse_google_tool_call(raw_call)
        return self._parse_generic_tool_call(raw_call)

    def format_tool_result(self, result: ToolResult) -> dict[str, Any]:
        if self.provider == "anthropic":
            return self._format_anthropic_result(result)
        if self.provider in _OPENAI_FAMILY:
            return self._format_openai_result(result)
        if self.provider in ("google", "gemini"):
            return self._format_google_result(result)
        return self._format_generic_result(result)

    def _parse_anthropic_tool_call(self, raw_call: dict[str, Any]) -> ToolCall:
        name = str(raw_call.get("name") or "")
        tool_id = raw_call.get("id")
        arguments = raw_call.get("input")
        if arguments is None:
            arguments = raw_call.get("arguments", {})
        return build_tool_call(tool_id, name, arguments)

    def _parse_openai_tool_call(self, raw_call: dict[str, Any]) -> ToolCall:
        fn = raw_call.get("function") or {}
        if not isinstance(fn, dict):
            fn = {}
        name = str(fn.get("name") or raw_call.get("name") or "")
        tool_id = raw_call.get("id")
        arguments = fn.get("arguments", raw_call.get("arguments", "{}"))
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments or "{}")
            except json.JSONDecodeError:
                arguments = {}
        if not isinstance(arguments, dict):
            arguments = {}
        provider_data = {}
        if raw_call.get("extra_content"):
            provider_data["extra_content"] = raw_call["extra_content"]
        if raw_call.get("call_id"):
            provider_data["call_id"] = raw_call["call_id"]
        if raw_call.get("response_item_id"):
            provider_data["response_item_id"] = raw_call["response_item_id"]
        return build_tool_call(tool_id, name, arguments, **provider_data)

    def _parse_google_tool_call(self, raw_call: dict[str, Any]) -> ToolCall:
        fn_call = raw_call.get("functionCall") or raw_call
        name = str(fn_call.get("name") or "")
        tool_id = raw_call.get("id")
        arguments = fn_call.get("args") or fn_call.get("arguments") or {}
        return build_tool_call(tool_id, name, arguments)

    def _parse_generic_tool_call(self, raw_call: dict[str, Any]) -> ToolCall:
        if "function" in raw_call:
            return self._parse_openai_tool_call(raw_call)
        if "input" in raw_call or raw_call.get("type") == "tool_use":
            return self._parse_anthropic_tool_call(raw_call)
        if "functionCall" in raw_call:
            return self._parse_google_tool_call(raw_call)
        name = str(raw_call.get("name") or "")
        arguments = raw_call.get("arguments") or raw_call.get("parameters") or {}
        return build_tool_call(raw_call.get("id"), name, arguments)

    def _format_anthropic_result(self, result: ToolResult) -> dict[str, Any]:
        return {
            "type": "tool_result",
            "tool_use_id": result.tool_call_id,
            "content": result.content,
            "is_error": result.is_error,
        }

    def _format_openai_result(self, result: ToolResult) -> dict[str, Any]:
        return {
            "role": "tool",
            "tool_call_id": result.tool_call_id,
            "name": result.name,
            "content": result.content,
        }

    def _format_google_result(self, result: ToolResult) -> dict[str, Any]:
        return {
            "role": "tool",
            "parts": [
                {
                    "functionResponse": {
                        "name": result.name,
                        "response": {"content": result.content},
                    }
                }
            ],
        }

    def _format_generic_result(self, result: ToolResult) -> dict[str, Any]:
        return self._format_openai_result(result)
