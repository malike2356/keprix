"""Agent discovery registry: advertise and query available agent capabilities."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentCard:
    """Self-description of an agent's capabilities.

    Modelled after the A2A specification agent card.
    """
    id: str
    name: str
    description: str
    capabilities: list[str] = field(default_factory=list)
    input_modes: list[str] = field(default_factory=lambda: ["text"])
    output_modes: list[str] = field(default_factory=lambda: ["text"])
    endpoint: str = ""
    tags: list[str] = field(default_factory=list)
    registered_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "input_modes": self.input_modes,
            "output_modes": self.output_modes,
            "endpoint": self.endpoint,
            "tags": self.tags,
        }


class AgentRegistry:
    """In-process registry for discoverable agents.

    Usage::

        registry = AgentRegistry()
        registry.register(AgentCard(
            id="summariser-v1",
            name="Document Summariser",
            description="Summarises long documents",
            capabilities=["summarise", "extract"],
            tags=["documents", "rag"],
        ))

        agents = registry.find(capability="summarise")
        agent  = registry.get("summariser-v1")
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentCard] = {}
        self._lock = asyncio.Lock()

    async def register(self, card: AgentCard) -> None:
        async with self._lock:
            self._agents[card.id] = card

    async def unregister(self, agent_id: str) -> None:
        async with self._lock:
            self._agents.pop(agent_id, None)

    async def get(self, agent_id: str) -> AgentCard | None:
        async with self._lock:
            return self._agents.get(agent_id)

    async def all(self) -> list[AgentCard]:
        async with self._lock:
            return list(self._agents.values())

    async def find(
        self,
        capability: str | None = None,
        tag: str | None = None,
        input_mode: str | None = None,
    ) -> list[AgentCard]:
        """Return agents matching ALL specified filters."""
        async with self._lock:
            results = list(self._agents.values())

        if capability:
            results = [a for a in results if capability in a.capabilities]
        if tag:
            results = [a for a in results if tag in a.tags]
        if input_mode:
            results = [a for a in results if input_mode in a.input_modes]

        return results

    async def best_for(self, task_description: str, tags: list[str] | None = None) -> AgentCard | None:
        """Simple keyword match to find the most relevant agent for a task.

        Returns the first agent whose name or description contains a word
        from the task description, optionally filtered by tags.
        """
        candidates = await self.find(tag=tags[0] if tags else None) if tags else await self.all()
        words = set(task_description.lower().split())
        for agent in candidates:
            searchable = f"{agent.name} {agent.description}".lower()
            if words.intersection(searchable.split()):
                return agent
        return candidates[0] if candidates else None
