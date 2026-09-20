"""Reversible plugin lifecycle: registration ledger, mount/unmount, audit.

Hot enable/disable undoes tool schemas, prompt sections, MCP bindings, and
seam Provider contributions so nothing orphans in the agent loop or UI.

Product modules (Playbooks, CRM, billing, Document Vault, Channel Shield) are
not plugins and are outside this lifecycle.
"""

from __future__ import annotations

from keprix.plugin_lifecycle.api import (
    disable_plugin_hot,
    enable_plugin_hot,
    get_lifecycle_ledger,
    list_audit_events,
    mount_plugin,
    reset_lifecycle_for_tests,
    unmount_plugin,
)
from keprix.plugin_lifecycle.prompt_sections import (
    clear_prompt_section,
    get_prompt_section,
    list_prompt_sections,
    register_prompt_section,
)

__all__ = [
    "clear_prompt_section",
    "disable_plugin_hot",
    "enable_plugin_hot",
    "get_lifecycle_ledger",
    "get_prompt_section",
    "list_audit_events",
    "list_prompt_sections",
    "mount_plugin",
    "register_prompt_section",
    "reset_lifecycle_for_tests",
    "unmount_plugin",
]
