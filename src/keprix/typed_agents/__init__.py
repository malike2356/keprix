"""Pydantic AI-style typed agents with dependency injection."""

from keprix.typed_agents.agent import AgentRunResult, TypedAgent, TypedTool, create_support_agent
from keprix.typed_agents.deps_factory import build_agent_dependencies, build_support_dependencies
from keprix.typed_agents.dependencies import AgentDependencies
from keprix.typed_agents.registry import bootstrap_typed_agents, get_typed_agent, list_typed_agents
from keprix.typed_agents.schemas import AgentRunContext, export_type_schemas

__all__ = [
    "AgentDependencies",
    "AgentRunContext",
    "AgentRunResult",
    "TypedAgent",
    "TypedTool",
    "bootstrap_typed_agents",
    "build_agent_dependencies",
    "build_support_dependencies",
    "create_support_agent",
    "export_type_schemas",
    "get_typed_agent",
    "list_typed_agents",
]
