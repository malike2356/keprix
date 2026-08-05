"""Provider-agnostic tool schema definitions."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParameterSchema:
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum: list[str] | None = None

    def to_json_schema(self) -> dict[str, Any]:
        schema: dict[str, Any] = {"type": self.type, "description": self.description}
        if self.enum:
            schema["enum"] = list(self.enum)
        if self.default is not None:
            schema["default"] = self.default
        return schema


@dataclass
class ReturnSchema:
    type: str
    description: str
    schema: dict[str, Any] | None = None


@dataclass
class ToolExample:
    description: str
    parameters: dict[str, Any]
    result_summary: str


@dataclass
class ToolSchema:
    """Provider-agnostic tool definition."""

    name: str
    description: str
    parameters: dict[str, ParameterSchema] = field(default_factory=dict)
    returns: ReturnSchema = field(
        default_factory=lambda: ReturnSchema(type="json", description="Tool result payload.")
    )
    examples: list[ToolExample] = field(default_factory=list)

    def required_parameter_names(self) -> list[str]:
        return [name for name, param in self.parameters.items() if param.required]

    def to_json_schema_parameters(self) -> dict[str, Any]:
        properties = {
            name: param.to_json_schema() for name, param in self.parameters.items()
        }
        required = self.required_parameter_names()
        schema: dict[str, Any] = {"type": "object", "properties": properties}
        if required:
            schema["required"] = required
        return schema

    def to_openai(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.to_json_schema_parameters(),
            },
        }

    def to_anthropic(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.to_json_schema_parameters(),
        }

    def to_google(self) -> dict[str, Any]:
        decl: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "parameters": self.to_json_schema_parameters(),
        }
        return {"functionDeclarations": [decl]}

    def to_bedrock(self) -> dict[str, Any]:
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {"json": self.to_json_schema_parameters()},
            }
        }

    def to_generic(self) -> str:
        from agent.tool_description import generate_natural_description

        return generate_natural_description(self)

    @classmethod
    def from_openai_function(cls, function: dict[str, Any]) -> ToolSchema:
        """Build a ToolSchema from an OpenAI-style function dict."""
        name = str(function.get("name") or "").strip()
        description = str(function.get("description") or "").strip()
        params = function.get("parameters") or {}
        if not isinstance(params, dict):
            params = {}
        properties = params.get("properties") or {}
        if not isinstance(properties, dict):
            properties = {}
        required_names = set(params.get("required") or [])
        if not isinstance(required_names, (list, set, tuple)):
            required_names = set()

        parameters: dict[str, ParameterSchema] = {}
        for param_name, raw in properties.items():
            if not isinstance(raw, dict):
                continue
            param_type = str(raw.get("type") or "string")
            enum_vals = raw.get("enum")
            if enum_vals is not None and not isinstance(enum_vals, list):
                enum_vals = None
            parameters[param_name] = ParameterSchema(
                name=param_name,
                type=param_type,
                description=str(raw.get("description") or "").strip(),
                required=param_name in required_names,
                default=raw.get("default"),
                enum=[str(v) for v in enum_vals] if enum_vals else None,
            )

        return cls(
            name=name,
            description=description,
            parameters=parameters,
            returns=ReturnSchema(type="json", description="Tool result payload."),
        )

    @classmethod
    def from_openai_tool(cls, tool: dict[str, Any]) -> ToolSchema:
        function = tool.get("function") or {}
        if not isinstance(function, dict):
            function = {}
        return cls.from_openai_function(function)


def schemas_from_openai_tools(tools: list[dict[str, Any]]) -> list[ToolSchema]:
    return [ToolSchema.from_openai_tool(tool) for tool in tools if isinstance(tool, dict)]
