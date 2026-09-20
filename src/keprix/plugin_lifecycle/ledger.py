"""Per-plugin registration ledger."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class PluginRegistrations:
    """Everything a plugin registered that unload must reverse."""

    plugin_id: str
    tools: list[str] = field(default_factory=list)
    hooks: list[tuple[str, Callable[..., Any]]] = field(default_factory=list)
    middleware: list[tuple[str, Callable[..., Any]]] = field(default_factory=list)
    slash_commands: list[str] = field(default_factory=list)
    cli_commands: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    aux_tasks: list[str] = field(default_factory=list)
    prompt_sections: list[str] = field(default_factory=list)
    mcp_servers: list[str] = field(default_factory=list)
    seam_providers: list[tuple[str, str]] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)

    def snapshot(self) -> dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "tools": list(self.tools),
            "hooks": [name for name, _ in self.hooks],
            "middleware": [kind for kind, _ in self.middleware],
            "slash_commands": list(self.slash_commands),
            "cli_commands": list(self.cli_commands),
            "skills": list(self.skills),
            "aux_tasks": list(self.aux_tasks),
            "prompt_sections": list(self.prompt_sections),
            "mcp_servers": list(self.mcp_servers),
            "seam_providers": [f"{s}:{p}" for s, p in self.seam_providers],
            "platforms": list(self.platforms),
        }


class LifecycleLedger:
    """Track registrations per plugin/skill id for reversible unload."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._entries: dict[str, PluginRegistrations] = {}

    def ensure(self, plugin_id: str) -> PluginRegistrations:
        with self._lock:
            entry = self._entries.get(plugin_id)
            if entry is None:
                entry = PluginRegistrations(plugin_id=plugin_id)
                self._entries[plugin_id] = entry
            return entry

    def record_tool(self, plugin_id: str, name: str) -> None:
        with self._lock:
            entry = self.ensure(plugin_id)
            if name not in entry.tools:
                entry.tools.append(name)

    def record_hook(
        self,
        plugin_id: str,
        hook_name: str,
        callback: Callable[..., Any],
    ) -> None:
        with self._lock:
            self.ensure(plugin_id).hooks.append((hook_name, callback))

    def record_middleware(
        self,
        plugin_id: str,
        kind: str,
        callback: Callable[..., Any],
    ) -> None:
        with self._lock:
            self.ensure(plugin_id).middleware.append((kind, callback))

    def record_slash_command(self, plugin_id: str, name: str) -> None:
        with self._lock:
            entry = self.ensure(plugin_id)
            if name not in entry.slash_commands:
                entry.slash_commands.append(name)

    def record_cli_command(self, plugin_id: str, name: str) -> None:
        with self._lock:
            entry = self.ensure(plugin_id)
            if name not in entry.cli_commands:
                entry.cli_commands.append(name)

    def record_skill(self, plugin_id: str, qualified_name: str) -> None:
        with self._lock:
            entry = self.ensure(plugin_id)
            if qualified_name not in entry.skills:
                entry.skills.append(qualified_name)

    def record_aux_task(self, plugin_id: str, key: str) -> None:
        with self._lock:
            entry = self.ensure(plugin_id)
            if key not in entry.aux_tasks:
                entry.aux_tasks.append(key)

    def record_prompt_section(self, plugin_id: str, section_id: str) -> None:
        with self._lock:
            entry = self.ensure(plugin_id)
            if section_id not in entry.prompt_sections:
                entry.prompt_sections.append(section_id)

    def record_mcp_server(self, plugin_id: str, server_name: str) -> None:
        with self._lock:
            entry = self.ensure(plugin_id)
            if server_name not in entry.mcp_servers:
                entry.mcp_servers.append(server_name)

    def record_seam_provider(
        self,
        plugin_id: str,
        seam: str,
        provider_id: str,
    ) -> None:
        with self._lock:
            entry = self.ensure(plugin_id)
            pair = (seam, provider_id)
            if pair not in entry.seam_providers:
                entry.seam_providers.append(pair)

    def record_platform(self, plugin_id: str, platform_name: str) -> None:
        with self._lock:
            entry = self.ensure(plugin_id)
            if platform_name not in entry.platforms:
                entry.platforms.append(platform_name)

    def get(self, plugin_id: str) -> PluginRegistrations | None:
        with self._lock:
            entry = self._entries.get(plugin_id)
            return entry

    def pop(self, plugin_id: str) -> PluginRegistrations | None:
        with self._lock:
            return self._entries.pop(plugin_id, None)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {pid: e.snapshot() for pid, e in self._entries.items()}


_LEDGER: LifecycleLedger | None = None
_LEDGER_LOCK = threading.Lock()


def get_lifecycle_ledger() -> LifecycleLedger:
    global _LEDGER
    with _LEDGER_LOCK:
        if _LEDGER is None:
            _LEDGER = LifecycleLedger()
        return _LEDGER


def reset_ledger_for_tests() -> LifecycleLedger:
    global _LEDGER
    with _LEDGER_LOCK:
        _LEDGER = LifecycleLedger()
        return _LEDGER
