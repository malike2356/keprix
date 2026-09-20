"""Capability seam Definitions (contracts).

Consumers depend only on these protocols. Providers implement them.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class FsDefinition(Protocol):
    """Filesystem seam: read/write/list within a provider-owned world."""

    provider_id: str

    def read_text(self, path: str, *, encoding: str = "utf-8") -> str: ...

    def write_text(self, path: str, content: str, *, encoding: str = "utf-8") -> None: ...

    def exists(self, path: str) -> bool: ...

    def list_dir(self, path: str = ".") -> list[str]: ...

    def tool_schemas(self) -> list[dict[str, Any]]: ...


@runtime_checkable
class ShellDefinition(Protocol):
    """Shell / subprocess seam."""

    provider_id: str

    def execute(
        self,
        command: str,
        *,
        cwd: str = "",
        timeout: int | None = None,
    ) -> dict[str, Any]: ...

    def tool_schemas(self) -> list[dict[str, Any]]: ...


@runtime_checkable
class MemoryDefinition(Protocol):
    """Durable / session memory seam (workspace-scoped)."""

    provider_id: str

    def read_store(self, store: str, *, workspace_id: str | None = None) -> str: ...

    def append_entry(
        self,
        store: str,
        entry: str,
        *,
        workspace_id: str | None = None,
    ) -> dict[str, Any]: ...

    def tool_schemas(self) -> list[dict[str, Any]]: ...


@runtime_checkable
class LlmDefinition(Protocol):
    """LLM routing / completion seam."""

    provider_id: str

    def resolve_route(self) -> dict[str, Any]: ...

    def complete(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]: ...

    def tool_schemas(self) -> list[dict[str, Any]]: ...


@runtime_checkable
class SubagentDefinition(Protocol):
    """Subagent spawn / delegate seam."""

    provider_id: str

    def describe(self) -> dict[str, Any]: ...

    def spawn(self, task: str, **kwargs: Any) -> dict[str, Any]: ...

    def tool_schemas(self) -> list[dict[str, Any]]: ...


@runtime_checkable
class WebDefinition(Protocol):
    """HTTP fetch / search / browse seam."""

    provider_id: str

    def search(self, query: str, *, limit: int = 5) -> dict[str, Any]: ...

    def fetch(self, url: str, **kwargs: Any) -> dict[str, Any]: ...

    def tool_schemas(self) -> list[dict[str, Any]]: ...
