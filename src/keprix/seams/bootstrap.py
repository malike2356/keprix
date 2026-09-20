"""Bootstrap default Providers for all six seams."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keprix.seams.policy import PolicyWrappedFs, PolicyWrappedShell, PolicyWrappedWeb
from keprix.seams.providers import (
    DefaultLlmProvider,
    DefaultMemoryProvider,
    DefaultSubagentProvider,
    DefaultWebProvider,
    LocalFsProvider,
    LocalShellProvider,
    SandboxedFsProvider,
    SandboxedShellProvider,
)
from keprix.seams.registry import SeamRegistry, _reset_registry_for_tests, get_seam_registry

_bootstrapped = False


def ensure_default_seams(
    *,
    force: bool = False,
    sandbox_root: str | Path | None = None,
    memory_base: str | Path | None = None,
) -> SeamRegistry:
    """Register default (+ sandboxed) Providers and wrap dangerous ones in policy.

    Idempotent unless *force* is True. Soft Wall / vault / Channel Shield gates
    wrap fs, shell, and web Providers so consumers never skip policy.
    """
    global _bootstrapped
    registry = get_seam_registry()
    if _bootstrapped and not force:
        return registry

    if force:
        registry.clear()

    fs_local = PolicyWrappedFs(LocalFsProvider())
    registry.register("fs", fs_local, make_active=True)

    shell_local = PolicyWrappedShell(LocalShellProvider())
    registry.register("shell", shell_local, make_active=True)

    if sandbox_root is not None:
        root = Path(sandbox_root)
        registry.register("fs", PolicyWrappedFs(SandboxedFsProvider(root)))
        registry.register("shell", PolicyWrappedShell(SandboxedShellProvider(root)))

    mem_kwargs: dict[str, Any] = {}
    if memory_base is not None:
        mem_kwargs["base_dir"] = memory_base
    registry.register("memory", DefaultMemoryProvider(**mem_kwargs), make_active=True)
    registry.register("llm", DefaultLlmProvider(), make_active=True)
    registry.register("subagent", DefaultSubagentProvider(), make_active=True)
    registry.register("web", PolicyWrappedWeb(DefaultWebProvider()), make_active=True)

    _bootstrapped = True
    return registry


def reset_seams_for_tests(**kwargs: Any) -> SeamRegistry:
    """Reset global registry and re-bootstrap (tests only)."""
    global _bootstrapped
    _bootstrapped = False
    _reset_registry_for_tests()
    return ensure_default_seams(force=True, **kwargs)
