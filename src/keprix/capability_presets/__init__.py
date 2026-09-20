"""Capability presets / declarative packs (prompt 771).

Compose coding vs CRM vs sidecar profiles via YAML. Apply mounts/unmounts
through keprix.plugin_lifecycle (769) and seam Providers (768). Soft Wall
cannot be disabled by a pack. Playbooks, billing, Document Vault stay
first-class OS modules.
"""

from __future__ import annotations

from keprix.capability_presets.apply import (
    apply_preset,
    apply_preset_file,
    diff_presets,
    list_available_presets,
    show_preset,
)
from keprix.capability_presets.loader import get_preset, list_presets, load_preset_file
from keprix.capability_presets.schema import PresetValidationError, validate_preset
from keprix.capability_presets.state import (
    get_active_state,
    set_state_path_for_tests,
)

__all__ = [
    "PresetValidationError",
    "apply_preset",
    "apply_preset_file",
    "diff_presets",
    "get_active_state",
    "get_preset",
    "list_available_presets",
    "list_presets",
    "load_preset_file",
    "set_state_path_for_tests",
    "show_preset",
    "validate_preset",
]
