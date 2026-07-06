"""Multi-provider model registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ModelProvider:
    name: str
    models: list[str]
    supports_tools: bool = True
    supports_streaming: bool = True
    cost_tier: str = "standard"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "models": self.models,
            "supports_tools": self.supports_tools,
            "supports_streaming": self.supports_streaming,
            "cost_tier": self.cost_tier,
        }


class ModelProviderRegistry:
    def __init__(self) -> None:
        self._providers = {
            "openai": ModelProvider("openai", ["gpt-4.1-mini", "gpt-4.1"], cost_tier="standard"),
            "anthropic": ModelProvider("anthropic", ["claude-sonnet-4-6"], cost_tier="premium"),
            "local": ModelProvider("local", ["ollama/llama3"], cost_tier="low", supports_streaming=True),
        }

    def list_providers(self) -> list[dict[str, Any]]:
        return [provider.to_dict() for provider in self._providers.values()]

    def get(self, name: str) -> ModelProvider | None:
        return self._providers.get(name)


_registry = ModelProviderRegistry()


def get_model_provider_registry() -> ModelProviderRegistry:
    return _registry
