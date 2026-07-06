"""Agent role registry and playbook YAML persistence (Prompt 58)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from keprix.backend.multiagent.group_chat import GroupChatPolicy


@dataclass
class AgentRoleDef:
    name: str
    goal: str
    backstory: str = ""
    tools: list[str] = field(default_factory=list)
    connects_to: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "backstory": self.backstory,
            "tools": self.tools,
            "connects_to": self.connects_to,
        }


@dataclass
class MultiAgentPlaybook:
    name: str
    workspace_id: str = "local"
    roles: dict[str, AgentRoleDef] = field(default_factory=dict)
    connections: list[dict[str, str]] = field(default_factory=list)
    group_chat: dict[str, Any] = field(default_factory=dict)
    mcp_servers: list[dict[str, Any]] = field(default_factory=list)

    def to_yaml(self) -> str:
        payload = {
            "name": self.name,
            "workspace_id": self.workspace_id,
            "roles": {key: role.to_dict() for key, role in self.roles.items()},
            "connections": self.connections,
            "group_chat": self.group_chat,
            "mcp_servers": self.mcp_servers,
        }
        return yaml.safe_dump(payload, sort_keys=False)

    @classmethod
    def from_yaml(cls, text: str) -> MultiAgentPlaybook:
        raw = yaml.safe_load(text) or {}
        roles = {
            role_id: AgentRoleDef(
                name=role_id,
                goal=str(config.get("goal") or ""),
                backstory=str(config.get("backstory") or ""),
                tools=list(config.get("tools") or []),
                connects_to=list(config.get("connects_to") or []),
            )
            for role_id, config in dict(raw.get("roles") or {}).items()
        }
        return cls(
            name=str(raw.get("name") or "multi-agent-playbook"),
            workspace_id=str(raw.get("workspace_id") or "local"),
            roles=roles,
            connections=list(raw.get("connections") or []),
            group_chat=dict(raw.get("group_chat") or {}),
            mcp_servers=list(raw.get("mcp_servers") or []),
        )


class AgentRegistry:
    def __init__(self) -> None:
        self._roles: dict[str, AgentRoleDef] = {}
        self._playbooks: dict[str, MultiAgentPlaybook] = {}
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        defaults = {
            "math_expert": AgentRoleDef("math_expert", "Solve math and logic problems", tools=["calculator"]),
            "researcher": AgentRoleDef("researcher", "Gather and cite sources", tools=["search", "citations"]),
            "browser_operator": AgentRoleDef("browser_operator", "Operate browser tasks", tools=["browser.navigate"]),
            "analyst": AgentRoleDef("analyst", "Analyze data and produce summaries", tools=["analytics.query"]),
            "asset_builder": AgentRoleDef("asset_builder", "Draft marketing assets", tools=["documents.write"]),
            "compliance_reviewer": AgentRoleDef("compliance_reviewer", "Review outputs for policy compliance", tools=[]),
            "qa_reviewer": AgentRoleDef("qa_reviewer", "Review code quality and tests", tools=["code.review"]),
            "coordinator": AgentRoleDef(
                "coordinator",
                "Route tasks to specialists",
                tools=["agent.researcher", "agent.browser_operator"],
                connects_to=["researcher", "browser_operator", "analyst"],
            ),
        }
        self._roles.update(defaults)

    def list_roles(self) -> list[str]:
        return sorted(self._roles.keys())

    def get_role(self, name: str) -> AgentRoleDef | None:
        return self._roles.get(name)

    def upsert_role(self, role: AgentRoleDef) -> None:
        self._roles[role.name] = role

    def save_playbook(self, playbook: MultiAgentPlaybook, *, root: Path | None = None) -> Path:
        directory = (root or _playbook_dir()).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{playbook.name}.yaml"
        path.write_text(playbook.to_yaml(), encoding="utf-8")
        self._playbooks[playbook.name] = playbook
        for role_id, role in playbook.roles.items():
            self._roles[role_id] = role
        return path

    def get_playbook(self, name: str) -> MultiAgentPlaybook | None:
        return self._playbooks.get(name)

    def list_playbooks(self) -> list[str]:
        return sorted(self._playbooks.keys())

    def load_playbooks_from_disk(self, *, root: Path | None = None) -> int:
        directory = root or _playbook_dir()
        if not directory.is_dir():
            return 0
        count = 0
        for path in sorted(directory.glob("*.yaml")):
            playbook = MultiAgentPlaybook.from_yaml(path.read_text(encoding="utf-8"))
            self._playbooks[playbook.name] = playbook
            for role_id, role in playbook.roles.items():
                self._roles[role_id] = role
            count += 1
        return count


def _playbook_dir() -> Path:
    cwd = Path.cwd() / ".keprix" / "multiagent" / "playbooks"
    if cwd.parent.parent.exists():
        return cwd
    return Path(__file__).resolve().parents[4] / ".keprix" / "multiagent" / "playbooks"


def default_playbook(name: str = "starter-team") -> MultiAgentPlaybook:
    return MultiAgentPlaybook(
        name=name,
        roles={
            "coordinator": AgentRoleDef(
                "coordinator",
                "Route tasks to specialists",
                tools=["agent.researcher"],
                connects_to=["researcher", "analyst"],
            ),
            "researcher": AgentRoleDef("researcher", "Research with citations", tools=["search"]),
            "analyst": AgentRoleDef("analyst", "Summarize findings", tools=["analytics.query"]),
        },
        connections=[
            {"from": "coordinator", "to": "researcher"},
            {"from": "coordinator", "to": "analyst"},
        ],
        group_chat={
            "policy": GroupChatPolicy.SUPERVISOR_MODERATED.value,
            "supervisor": "coordinator",
            "participants": ["coordinator", "researcher", "analyst"],
        },
        mcp_servers=[{"name": "filesystem", "trusted": True, "bound_tools": ["read_file"]}],
    )


_agent_registry: AgentRegistry | None = None


def get_agent_registry() -> AgentRegistry:
    global _agent_registry
    if _agent_registry is None:
        _agent_registry = AgentRegistry()
    return _agent_registry
