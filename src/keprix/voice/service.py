"""Singleton accessors for the wake word registry."""

from __future__ import annotations

from pathlib import Path

from keprix.voice.wake import WakeWordRegistry

_registry: WakeWordRegistry | None = None


def get_wake_registry(storage_path: Path | None = None) -> WakeWordRegistry:
    global _registry
    if storage_path is not None:
        return WakeWordRegistry(storage_path=storage_path)
    if _registry is None:
        _registry = WakeWordRegistry()
    return _registry


def reset_wake_registry_for_tests() -> None:
    global _registry
    _registry = None
