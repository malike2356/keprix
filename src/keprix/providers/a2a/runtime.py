"""Process-wide A2A task manager and agent registry."""

from __future__ import annotations

from .agent_discovery import AgentCard, AgentRegistry
from .task_manager import TaskManager

_task_manager: TaskManager | None = None
_agent_registry: AgentRegistry | None = None
_seeded = False


def get_task_manager() -> TaskManager:
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager


def get_agent_registry() -> AgentRegistry:
    global _agent_registry
    if _agent_registry is None:
        _agent_registry = AgentRegistry()
    return _agent_registry


async def ensure_default_agents() -> AgentRegistry:
    """Register a local Keprix agent card once so the GUI is not empty."""
    global _seeded
    registry = get_agent_registry()
    if _seeded:
        return registry
    existing = await registry.get("keprix-local")
    if existing is None:
        await registry.register(
            AgentCard(
                id="keprix-local",
                name="Keprix local agent",
                description="In-process Keprix agent for A2A task handoffs.",
                capabilities=["chat", "tools", "handoff"],
                tags=["local", "keprix"],
                endpoint="local://keprix",
            )
        )
    _seeded = True
    return registry
