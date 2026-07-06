"""Registry of named typed agents for CLI, API, and SDK consumers."""

from __future__ import annotations

from typing import Any

from keprix.typed_agents.agent import TypedAgent, create_support_agent

_REGISTRY: dict[str, TypedAgent[Any, Any]] = {}


def register_typed_agent(agent: TypedAgent[Any, Any]) -> None:
    _REGISTRY[agent.name] = agent


def get_typed_agent(name: str) -> TypedAgent[Any, Any] | None:
    return _REGISTRY.get(name)


def list_typed_agents() -> list[str]:
    return sorted(_REGISTRY)


def bootstrap_typed_agents() -> None:
    if _REGISTRY:
        return
    register_typed_agent(create_support_agent())


bootstrap_typed_agents()
