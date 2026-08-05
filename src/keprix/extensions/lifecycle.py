"""Extension lifecycle manager: ordered startup and shutdown."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .base import KeprixExtension

logger = logging.getLogger(__name__)


class ExtensionLifecycle:
    """Manage ordered startup and shutdown of all loaded extensions.

    Startup runs in registration order. Shutdown runs in reverse order
    (LIFO) so dependencies unwind cleanly.

    Usage::

        lifecycle = ExtensionLifecycle()
        lifecycle.register(abbis_ext)
        lifecycle.register(petraclus_ext)
        await lifecycle.startup()
        ...
        await lifecycle.shutdown()
    """

    def __init__(self) -> None:
        self._extensions: list[KeprixExtension] = []
        self._started: list[str] = []

    def register(self, ext: KeprixExtension) -> None:
        self._extensions.append(ext)
        logger.debug("Extension registered: %s v%s", ext.name, ext.version)

    def register_all(self, extensions: list[KeprixExtension]) -> None:
        for ext in extensions:
            self.register(ext)

    async def startup(self) -> list[str]:
        """Call on_startup for each extension. Returns names of started extensions."""
        started: list[str] = []
        for ext in self._extensions:
            try:
                await ext.on_startup()
                self._started.append(ext.name)
                started.append(ext.name)
                logger.info("Extension started: %s", ext.name)
            except Exception as exc:
                logger.error("Extension %s failed to start: %s", ext.name, exc)
        return started

    async def shutdown(self) -> None:
        """Call on_shutdown in LIFO order."""
        for ext in reversed(self._extensions):
            if ext.name not in self._started:
                continue
            try:
                await ext.on_shutdown()
                logger.info("Extension stopped: %s", ext.name)
            except Exception as exc:
                logger.error("Extension %s failed to stop cleanly: %s", ext.name, exc)
        self._started.clear()

    def mount_routes(self, app: Any, prefix: str = "/api") -> None:
        """Register each extension's FastAPI routes onto the app."""
        for ext in self._extensions:
            for router in ext.routes:
                route_prefix = f"{prefix}/{ext.name}"
                app.include_router(router, prefix=route_prefix)
                logger.debug("Mounted routes for %s at %s", ext.name, route_prefix)

    def all_tools(self) -> list[Any]:
        """Return the combined list of domain tools from all extensions."""
        tools: list[Any] = []
        for ext in self._extensions:
            tools.extend(ext.domain_tools)
        return tools

    def all_personas(self) -> list[Any]:
        return [p for ext in self._extensions for p in ext.personas]

    def summary(self) -> dict[str, Any]:
        return {
            "registered": [e.name for e in self._extensions],
            "started": list(self._started),
            "total_tools": sum(len(e.domain_tools) for e in self._extensions),
        }
