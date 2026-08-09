"""Document Vault format engines package (Prompt 647)."""

from __future__ import annotations

from keprix.document_vault.formats.registry import (
    FormatCapability,
    capability_matrix_for_clients,
    list_format_capabilities,
    resolve_format,
)

__all__ = [
    "FormatCapability",
    "capability_matrix_for_clients",
    "list_format_capabilities",
    "resolve_format",
]
