"""Expose specialist agents as callable tools (Prompt 58)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from keprix.backend.multiagent.message import AgentMessage, MessageType
from keprix.backend.multiagent.registry import get_agent_registry
from keprix.backend.multiagent.runtime import send_message


@dataclass
class AgentToolResult:
    agent_id: str
    output: str
    artifacts: list[str] = field(default_factory=list)
    trace_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "output": self.output,
            "artifacts": self.artifacts,
            "trace_id": self.trace_id,
        }


class AgentTool:
    """Call a specialist agent as if it were a tool."""

    def __init__(
        self,
        agent_id: str,
        *,
        workspace_id: str = "local",
        run_id: str | None = None,
        caller: str = "coordinator",
    ) -> None:
        self.agent_id = agent_id
        self.workspace_id = workspace_id
        self.run_id = run_id or str(uuid4())
        self.caller = caller

    async def call(self, input_text: str, *, metadata: dict[str, Any] | None = None) -> AgentToolResult:
        registry = get_agent_registry()
        role = registry.get_role(self.agent_id)
        if role is None:
            raise KeyError(f"Unknown agent role: {self.agent_id}")

        tool_message = await send_message(
            AgentMessage(
                sender=self.caller,
                recipient=self.agent_id,
                workspace_id=self.workspace_id,
                run_id=self.run_id,
                content=input_text,
                message_type=MessageType.TOOL,
                metadata={"tool": f"agent.{self.agent_id}", **dict(metadata or {})},
            )
        )

        output = f"[{role.name}] {role.goal}: processed request"
        if role.tools:
            output += f" using {', '.join(role.tools)}"
        output += f" -> {input_text[:200]}"

        response = await send_message(
            AgentMessage(
                sender=self.agent_id,
                recipient=self.caller,
                workspace_id=self.workspace_id,
                run_id=self.run_id,
                content=output,
                message_type=MessageType.AGENT,
                metadata={"invoked_by_tool": True},
                artifact_refs=list(role.tools),
            )
        )
        return AgentToolResult(
            agent_id=self.agent_id,
            output=response.content,
            artifacts=list(response.artifact_refs),
            trace_id=response.trace_id,
        )

    def tool_spec(self) -> dict[str, Any]:
        role = get_agent_registry().get_role(self.agent_id)
        return {
            "name": f"agent.{self.agent_id}",
            "description": role.goal if role else f"Call agent {self.agent_id}",
            "parameters": {
                "type": "object",
                "properties": {"input": {"type": "string"}},
                "required": ["input"],
            },
        }


DEFAULT_AGENT_TOOLS = ("math_expert", "researcher", "browser_operator", "qa_reviewer", "compliance_reviewer")
