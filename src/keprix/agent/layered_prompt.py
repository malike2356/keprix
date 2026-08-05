"""Layered system prompt assembly (Fable 5-inspired architecture).

Each layer is rendered in enum order inside XML-style markers. Layers can be
added, replaced, or omitted independently without affecting others.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class PromptLayer(Enum):
    IDENTITY = 1
    BUDGET = 2
    SAFETY = 3
    TOOLS = 4
    TONE = 5
    MEMORY = 6
    EXECUTION = 7
    DOMAIN = 8
    PERSONA = 9
    PRODUCT = 10


@dataclass(frozen=True)
class PromptSessionContext:
    """Session metadata injected into identity and budget layers."""

    model_name: str
    provider_name: str
    session_id: str
    keprix_version: str

    @classmethod
    def from_agent(cls, agent: Any) -> PromptSessionContext:
        version = "unknown"
        try:
            from importlib import metadata

            version = metadata.version("keprix")
        except Exception:
            try:
                from keprix_cli import __version__

                version = __version__
            except Exception:
                pass
        return cls(
            model_name=getattr(agent, "model", "") or "unknown",
            provider_name=getattr(agent, "provider", "") or "unknown",
            session_id=getattr(agent, "session_id", "") or "",
            keprix_version=version,
        )


class LayeredPromptBuilder:
    """Builds system prompts in ordered layers. Each layer constrains the next."""

    def __init__(self, session: Optional[PromptSessionContext] = None):
        self.session = session
        self.layers: dict[PromptLayer, str] = {}

    def add_layer(self, layer: PromptLayer, content: str) -> None:
        """Add or replace a layer. Layers are rendered in enum order."""
        stripped = (content or "").strip()
        if stripped:
            self.layers[layer] = stripped

    def remove_layer(self, layer: PromptLayer) -> None:
        self.layers.pop(layer, None)

    def build(self) -> str:
        """Render the full system prompt with layer markers."""
        parts: list[str] = []
        for layer in PromptLayer:
            content = self.layers.get(layer)
            if not content:
                continue
            tag = layer.name.lower()
            parts.append(f"<{tag}>")
            parts.append(content)
            parts.append(f"</{tag}>")
        return "\n".join(parts)


def domain_layer_keys(text: str) -> set[str]:
    """Alias for domain detection used by assembly and tests."""
    from agent.layers.domains import detect_domains

    return detect_domains(text)


__all__ = [
    "PromptLayer",
    "PromptSessionContext",
    "LayeredPromptBuilder",
    "domain_layer_keys",
]
