"""Migration adapter registry (Prompt 42)."""

from __future__ import annotations

from pathlib import Path

from keprix.backend.migration.adapters.generic import GenericAdapter
from keprix.backend.migration.adapters.hermes import HermesAdapter
from keprix.backend.migration.adapters.markdown import MarkdownAdapter
from keprix.backend.migration.adapters.openclaw import OpenClawAdapter
from keprix.backend.migration.manifest import AgentMigrationManifest

ADAPTERS = {
    "hermes": HermesAdapter,
    "openclaw": OpenClawAdapter,
    "markdown": MarkdownAdapter,
    "generic": GenericAdapter,
}


def parse_source(source: str, path: Path) -> AgentMigrationManifest:
    adapter_cls = ADAPTERS.get(source)
    if adapter_cls is None:
        raise ValueError(f"Unsupported migration source: {source}")
    return adapter_cls().convert(path)
