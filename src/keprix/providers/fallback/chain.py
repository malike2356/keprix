"""Fallback chain executor."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from keprix.providers.fallback.error_handler import AllProvidersExhausted

ProviderCallable = Callable[..., Awaitable[Any]]


class FallbackChain:
    def __init__(self, providers: dict[str, ProviderCallable]) -> None:
        self.providers = providers

    async def execute(self, ordered_provider_ids: list[str], **kwargs: Any) -> Any:
        last_error: Exception | None = None
        for provider_id in ordered_provider_ids:
            handler = self.providers.get(provider_id)
            if handler is None:
                continue
            try:
                return await handler(**kwargs)
            except Exception as exc:
                last_error = exc
        raise AllProvidersExhausted("All providers in fallback chain failed", tried=len(ordered_provider_ids), last_error=last_error)
