"""Shared schemas for typed agents."""

from __future__ import annotations

from datetime import datetime
from keprix.compat import UTC
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentRunContext(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    workspace_id: str = "default"
    user_id: str = "default"
    model: str = "keprix-default"
    prompt_version: str = "v1"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationRepairMessage(BaseModel):
    kind: str
    message: str
    errors: list[dict[str, Any]] = Field(default_factory=list)
    attempt: int = 1

    def to_prompt_block(self) -> str:
        lines = [f"Validation failed ({self.kind}): {self.message}"]
        for error in self.errors:
            loc = ".".join(str(part) for part in error.get("loc", []))
            detail = error.get("msg", error.get("message", "invalid"))
            lines.append(f"- {loc}: {detail}" if loc else f"- {detail}")
        return "\n".join(lines)


class ArtifactMetadata(BaseModel):
    artifact_id: str
    artifact_type: str
    title: str
    trace_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    sensitivity: str = "internal"


class HandoffPayload(BaseModel):
    target_agent: str
    reason: str
    summary: str
    trace_id: str
    context: dict[str, Any] = Field(default_factory=dict)


class ToolDefinitionSchema(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    approval_action: str | None = None


class TypedAgentSchemaExport(BaseModel):
    agent_name: str
    output_schema: dict[str, Any]
    dependencies_schema: dict[str, Any]
    tools: list[ToolDefinitionSchema]
    context_schema: dict[str, Any]


def export_type_schemas(
    *,
    agent_name: str,
    output_type: type[BaseModel],
    dependencies_type: type[BaseModel],
    tools: list[Any],
    context: AgentRunContext | None = None,
) -> dict[str, Any]:
    tool_rows = []
    for tool in tools:
        tool_rows.append(
            ToolDefinitionSchema(
                name=tool.name,
                description=tool.description,
                input_schema=tool.input_model.model_json_schema(),
                output_schema=tool.output_model.model_json_schema() if tool.output_model else None,
                approval_action=tool.approval_action,
            )
        )
    export = TypedAgentSchemaExport(
        agent_name=agent_name,
        output_schema=output_type.model_json_schema(),
        dependencies_schema=dependencies_type.model_json_schema(),
        tools=tool_rows,
        context_schema=(context or AgentRunContext()).model_json_schema(),
    )
    return export.model_dump()
