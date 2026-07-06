"""Runtime tool name inventory for mutation gap detection."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_registry_warning_logged = False
_store_warning_logged = False


def list_runtime_tool_names() -> list[str]:
    """Return built-in registry names plus installed generated mutation tools."""
    global _registry_warning_logged, _store_warning_logged
    names: dict[str, str] = {}

    try:
        from tools.registry import registry

        for name in registry.get_all_tool_names():
            key = name.lower()
            if key not in names:
                names[key] = name
    except Exception as exc:
        if not _registry_warning_logged:
            logger.warning("tool registry unavailable for mutation inventory: %s", exc)
            _registry_warning_logged = True

    try:
        from keprix.agent.keprix.store import get_generated_tool_store

        for record in get_generated_tool_store().list_all(status="installed"):
            key = record.tool_name.lower()
            if key not in names:
                names[key] = record.tool_name
    except Exception as exc:
        if not _store_warning_logged:
            logger.warning("generated tool store unavailable for mutation inventory: %s", exc)
            _store_warning_logged = True

    return sorted(names.values(), key=str.lower)
