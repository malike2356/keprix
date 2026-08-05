"""MCP workbench for tool listing, binding, and risk gating (Prompt 58)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from keprix.backend.multiagent.message import AgentMessage, MessageType
from keprix.backend.multiagent.runtime import send_message

from keprix.compat import StrEnum


class ToolRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class McpToolSpec:
    server: str
    name: str
    description: str = ""
    risk: ToolRisk = ToolRisk.LOW
    requires_approval: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "server": self.server,
            "name": self.name,
            "description": self.description,
            "risk": self.risk.value,
            "requires_approval": self.requires_approval,
        }


@dataclass
class McpServerConfig:
    name: str
    trusted: bool = False
    bound_tools: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "trusted": self.trusted, "bound_tools": self.bound_tools}


DEFAULT_MCP_TOOLS: list[McpToolSpec] = [
    McpToolSpec("filesystem", "read_file", "Read a file", ToolRisk.LOW),
    McpToolSpec("filesystem", "write_file", "Write a file", ToolRisk.HIGH, requires_approval=True),
    McpToolSpec("browser", "navigate", "Open a URL", ToolRisk.MEDIUM),
    McpToolSpec("browser", "click", "Click an element", ToolRisk.MEDIUM),
    McpToolSpec("shell", "run_command", "Run shell command", ToolRisk.CRITICAL, requires_approval=True),
    McpToolSpec("database", "query", "Run SELECT query", ToolRisk.LOW),
    McpToolSpec("database", "execute", "Run write query", ToolRisk.HIGH, requires_approval=True),
]


class McpWorkbench:
    """Workbench abstraction for one or more MCP servers."""

    def __init__(self) -> None:
        self._servers: dict[str, McpServerConfig] = {}
        self._agent_bindings: dict[str, list[str]] = {}
        self._tool_log: list[dict[str, Any]] = []

    def list_tools(self, *, server: str | None = None) -> list[dict[str, Any]]:
        tools = DEFAULT_MCP_TOOLS
        if server:
            tools = [tool for tool in tools if tool.server == server]
        return [tool.to_dict() for tool in tools]

    def register_server(self, config: McpServerConfig) -> None:
        self._servers[config.name] = config

    def validate_trusted(self, server: str) -> bool:
        entry = self._servers.get(server)
        return bool(entry and entry.trusted)

    def bind_tools(self, agent_id: str, tool_names: list[str], *, server: str) -> dict[str, Any]:
        if not self.validate_trusted(server):
            raise PermissionError(f"MCP server not trusted: {server}")
        available = {f"{tool.server}.{tool.name}" for tool in DEFAULT_MCP_TOOLS if tool.server == server}
        bound: list[str] = []
        for name in tool_names:
            key = f"{server}.{name}" if "." not in name else name
            if key not in available and name not in available:
                continue
            bound.append(name if "." not in name else name.split(".", 1)[1])
        self._agent_bindings.setdefault(agent_id, []).extend(bound)
        server_cfg = self._servers.setdefault(server, McpServerConfig(name=server, trusted=True))
        server_cfg.bound_tools = list(dict.fromkeys([*server_cfg.bound_tools, *bound]))
        return {"agent_id": agent_id, "server": server, "bound_tools": bound}

    def get_bindings(self, agent_id: str) -> list[str]:
        return list(self._agent_bindings.get(agent_id, []))

    async def invoke_tool(
        self,
        *,
        agent_id: str,
        server: str,
        tool_name: str,
        params: dict[str, Any],
        workspace_id: str,
        run_id: str,
        approved: bool = False,
    ) -> dict[str, Any]:
        spec = next(
            (tool for tool in DEFAULT_MCP_TOOLS if tool.server == server and tool.name == tool_name),
            None,
        )
        if spec is None:
            raise KeyError(f"Unknown MCP tool: {server}.{tool_name}")
        if spec.requires_approval and not approved:
            await send_message(
                AgentMessage(
                    sender=agent_id,
                    recipient="approval_gate",
                    workspace_id=workspace_id,
                    run_id=run_id,
                    content=f"Approval required for {server}.{tool_name}",
                    message_type=MessageType.APPROVAL,
                    metadata={"tool": tool_name, "server": server, "params": params},
                )
            )
            return {"success": False, "blocked": True, "reason": "Approval required for dangerous tool"}

        entry = {
            "agent_id": agent_id,
            "server": server,
            "tool": tool_name,
            "params": params,
            "risk": spec.risk.value,
            "approved": approved or not spec.requires_approval,
        }
        self._tool_log.append(entry)
        await send_message(
            AgentMessage(
                sender=agent_id,
                recipient=server,
                workspace_id=workspace_id,
                run_id=run_id,
                content=f"Invoked {tool_name}",
                message_type=MessageType.TOOL,
                metadata=entry,
            )
        )
        return {"success": True, "result": {"tool": tool_name, "dry_run": True}, **entry}

    def tool_log(self, *, run_id: str | None = None) -> list[dict[str, Any]]:
        if run_id is None:
            return list(self._tool_log)
        return [entry for entry in self._tool_log if entry.get("run_id") == run_id]

    def clear(self) -> None:
        self._servers.clear()
        self._agent_bindings.clear()
        self._tool_log.clear()


_workbench: McpWorkbench | None = None


def get_mcp_workbench() -> McpWorkbench:
    global _workbench
    if _workbench is None:
        _workbench = McpWorkbench()
    return _workbench
