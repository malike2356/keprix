"""Consumer accessors: call Definitions only, never concrete Providers."""

from __future__ import annotations

from typing import Any

from keprix.seams.bootstrap import ensure_default_seams
from keprix.seams.registry import get_seam_registry


def _active(seam: str) -> Any:
    ensure_default_seams()
    return get_seam_registry().get(seam)  # type: ignore[arg-type]


def get_fs() -> Any:
    """Return the active filesystem Definition."""
    return _active("fs")


def get_shell() -> Any:
    """Return the active shell Definition."""
    return _active("shell")


def get_memory() -> Any:
    """Return the active memory Definition."""
    return _active("memory")


def get_llm() -> Any:
    """Return the active LLM Definition."""
    return _active("llm")


def get_subagent() -> Any:
    """Return the active subagent Definition."""
    return _active("subagent")


def get_web() -> Any:
    """Return the active web Definition."""
    return _active("web")
