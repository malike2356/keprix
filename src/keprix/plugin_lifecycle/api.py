"""Public mount / unmount API for reversible plugin lifecycle."""

from __future__ import annotations

import logging
from typing import Any

from keprix.plugin_lifecycle.audit import (
    emit_lifecycle_audit,
    list_audit_events,
    reset_audit_for_tests,
)
from keprix.plugin_lifecycle.ledger import (
    get_lifecycle_ledger,
    reset_ledger_for_tests,
)
from keprix.plugin_lifecycle.prompt_sections import (
    clear_prompt_section,
    reset_prompt_sections_for_tests,
)

logger = logging.getLogger(__name__)


def reset_lifecycle_for_tests() -> None:
    reset_ledger_for_tests()
    reset_audit_for_tests()
    reset_prompt_sections_for_tests()


def unmount_plugin(
    plugin_id: str,
    *,
    who: str = "operator",
) -> dict[str, Any]:
    """Unload runtime effects for *plugin_id* without deleting plugin files."""
    from keprix_cli.plugins import get_plugin_manager

    manager = get_plugin_manager()
    return manager.unmount_plugin(plugin_id, who=who)


def mount_plugin(
    plugin_id: str,
    *,
    who: str = "operator",
) -> dict[str, Any]:
    """Load / re-register a plugin's runtime effects in the current process."""
    from keprix_cli.plugins import get_plugin_manager

    manager = get_plugin_manager()
    return manager.mount_plugin(plugin_id, who=who)


def enable_plugin_hot(
    plugin_id: str,
    *,
    who: str = "operator",
) -> dict[str, Any]:
    """Idempotent enable: mount if needed. Safe when already mounted."""
    ledger = get_lifecycle_ledger()
    existing = ledger.get(plugin_id)
    if existing and (
        existing.tools
        or existing.hooks
        or existing.prompt_sections
        or existing.mcp_servers
        or existing.seam_providers
    ):
        emit_lifecycle_audit(
            "mount",
            plugin_id,
            who=who,
            ok=True,
            detail={"idempotent": True},
        )
        return {
            "ok": True,
            "plugin_id": plugin_id,
            "action": "mount",
            "idempotent": True,
            "registrations": existing.snapshot(),
        }
    return mount_plugin(plugin_id, who=who)


def disable_plugin_hot(
    plugin_id: str,
    *,
    who: str = "operator",
) -> dict[str, Any]:
    """Idempotent disable: unmount if mounted. Safe when already unmounted."""
    ledger = get_lifecycle_ledger()
    existing = ledger.get(plugin_id)
    if existing is None:
        emit_lifecycle_audit(
            "unmount",
            plugin_id,
            who=who,
            ok=True,
            detail={"idempotent": True, "already_cleared": True},
        )
        return {
            "ok": True,
            "plugin_id": plugin_id,
            "action": "unmount",
            "idempotent": True,
            "errors": [],
        }
    return unmount_plugin(plugin_id, who=who)


# Re-export for package __init__
__all__ = [
    "disable_plugin_hot",
    "enable_plugin_hot",
    "get_lifecycle_ledger",
    "list_audit_events",
    "mount_plugin",
    "reset_lifecycle_for_tests",
    "unmount_plugin",
    "clear_prompt_section",
]
