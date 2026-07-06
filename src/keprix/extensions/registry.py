"""Extension registration and lifecycle for products built on Keprix."""

from __future__ import annotations

import importlib
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter

from keprix.governance.routes import router as governance_router
from keprix.governance.worker import start_governance_worker, stop_governance_worker

StartupHook = Callable[[], Awaitable[None] | None]
ShutdownHook = Callable[[], Awaitable[None] | None]


@dataclass
class ExtensionManifest:
    """A product or connector that extends Keprix at runtime."""

    name: str
    display_name: str
    version: str = "0.0.0"
    homepage: str | None = None
    routes: list[APIRouter] = field(default_factory=list)
    startup_hooks: list[StartupHook] = field(default_factory=list)
    shutdown_hooks: list[ShutdownHook] = field(default_factory=list)
    governance_provider: str | None = None
    billing_provider: str | None = None
    feature_flags: dict[str, bool] = field(default_factory=dict)


_REGISTRY: dict[str, ExtensionManifest] = {}
_LOADED = False


def register_extension(manifest: ExtensionManifest) -> None:
    _REGISTRY[manifest.name] = manifest
    try:
        from keprix.config import constants

        constants.EXTENSION_REGISTRY[manifest.name] = manifest
    except Exception:
        pass


def get_extension(name: str) -> ExtensionManifest | None:
    return _REGISTRY.get(name)


def list_extensions() -> list[ExtensionManifest]:
    return list(_REGISTRY.values())


def _governance_enabled() -> bool:
    return os.environ.get("KEPRIX_GOVERNANCE_ENABLED", "").lower() in {"1", "true", "yes"}


def get_governance_router() -> APIRouter:
    return governance_router


def _load_manifest_module(ext_name: str) -> ExtensionManifest | None:
    module_name = f"keprix.extensions.{ext_name}.manifest"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        return None
    loader = getattr(module, "load_manifest", None)
    if callable(loader):
        manifest = loader()
        if isinstance(manifest, ExtensionManifest):
            return manifest
    manifest = getattr(module, "MANIFEST", None)
    if isinstance(manifest, ExtensionManifest):
        return manifest
    return None


def load_active_extensions() -> list[ExtensionManifest]:
    global _LOADED
    if _LOADED:
        return list_extensions()

    raw = os.environ.get("KEPRIX_ACTIVE_EXTENSIONS", "").strip()
    names = [part.strip() for part in raw.split(",") if part.strip()]
    loaded: list[ExtensionManifest] = []
    for name in names:
        manifest = _load_manifest_module(name)
        if manifest is None:
            continue
        register_extension(manifest)
        loaded.append(manifest)
    _LOADED = True
    return loaded


async def start_extension_hooks() -> None:
    load_active_extensions()
    if _governance_enabled():
        await start_governance_worker()
    for manifest in list_extensions():
        for hook in manifest.startup_hooks:
            result = hook()
            if hasattr(result, "__await__"):
                await result


async def stop_extension_hooks() -> None:
    if _governance_enabled():
        await stop_governance_worker()
    for manifest in list_extensions():
        for hook in manifest.shutdown_hooks:
            result = hook()
            if hasattr(result, "__await__"):
                await result
