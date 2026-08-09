"""Keprix Document Vault programme package (Prompt 645+).

Native Keprix implementation of the shared Aiva/Keprix Document Vault
behavioral contract. Must never require Carina at runtime.
"""

from __future__ import annotations

from keprix.document_vault.flags import DocumentVaultFlags, load_flags

CONTRACT_VERSION = "1.0.0"
PRODUCT = "keprix"
CARINA_RUNTIME_REQUIRED = False

__all__ = [
    "CARINA_RUNTIME_REQUIRED",
    "CONTRACT_VERSION",
    "PRODUCT",
    "DocumentVaultFlags",
    "load_flags",
]
