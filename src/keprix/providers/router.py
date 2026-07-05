"""Provider router: selects and returns the correct LLM provider.

Priority on 'auto' detection:
  1. Anthropic (if ANTHROPIC_API_KEY set)
  2. OpenAI (if OPENAI_API_KEY set)
  3. Ollama (if OLLAMA_BASE_URL reachable)
  4. Raises RuntimeError if no provider is configured

Cursor implements each concrete provider adapter (Prompt 04).
This router is stable - add new providers by registering them in _registry.
"""

from __future__ import annotations

import logging

from keprix.config.settings import get_settings
from keprix.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class ProviderRouter:
    _instance: ProviderRouter | None = None

    def __new__(cls) -> ProviderRouter:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._registry: dict[str, LLMProvider] = {}
            cls._instance._default: str = ""
        return cls._instance

    def register(self, provider: LLMProvider) -> None:
        self._registry[provider.name] = provider
        logger.debug("Registered provider: %s (default model: %s)", provider.name, provider.default_model)

    def get(self, model_or_provider: str = "") -> LLMProvider:
        """Return the provider for a model string like 'claude-sonnet-4-6' or 'anthropic'.

        Falls back to the default provider when model_or_provider is empty or 'auto'.
        """
        if not model_or_provider or model_or_provider == "auto":
            return self._get_default()

        for provider in self._registry.values():
            if model_or_provider.startswith(provider.name):
                return provider
            if model_or_provider in getattr(provider, "_models", []):
                return provider

        return self._get_default()

    def _get_default(self) -> LLMProvider:
        settings = get_settings()
        preferred = settings.KEPRIX_DEFAULT_PROVIDER

        order = [preferred] if preferred != "auto" else []
        if settings.ANTHROPIC_API_KEY:
            order.append("anthropic")
        if settings.OPENAI_API_KEY:
            order.append("openai")
        order.append("ollama")

        for name in order:
            if name in self._registry:
                return self._registry[name]

        if not self._registry:
            raise RuntimeError(
                "No LLM providers are configured. "
                "Set ANTHROPIC_API_KEY or OPENAI_API_KEY in your .env file."
            )
        return next(iter(self._registry.values()))

    def all(self) -> list[LLMProvider]:
        return list(self._registry.values())
