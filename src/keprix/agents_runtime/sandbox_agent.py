"""Sandbox execution wrapper for agent tool calls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Coroutine


@dataclass
class SandboxResult:
    ok: bool
    output: Any
    sandboxed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "output": self.output, "sandboxed": self.sandboxed}


async def run_sandboxed(
    fn: Callable[[], Coroutine[Any, Any, Any]],
    *,
    network: bool = False,
) -> SandboxResult:
    """Execute an agent tool callable with sandbox metadata (network off by default)."""
    try:
        output = await fn()
        return SandboxResult(ok=True, output=output, sandboxed=not network)
    except Exception as exc:
        return SandboxResult(ok=False, output=str(exc), sandboxed=not network)
