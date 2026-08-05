"""Plugins hub state."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PluginItem:
    name: str
    description: str = ""
    installed: bool = False
    enabled: bool = False


class PluginsHubState:
    def __init__(self, plugins: list[PluginItem] | None = None) -> None:
        self.plugins = list(plugins or [])

    def search(self, query: str) -> list[PluginItem]:
        needle = query.lower().strip()
        return [plugin for plugin in self.plugins if not needle or needle in plugin.name.lower() or needle in plugin.description.lower()]

