"""Keprix Document Vault programme package (Prompt 645+).

Native Keprix implementation of the shared Aiva/Keprix Document Vault
behavioral contract. Must never require Carina at runtime.
"""

from __future__ import annotations

from keprix.document_vault.flags import DocumentVaultFlags, load_flags
from keprix.document_vault.service import DocumentVaultService, get_document_vault_service
from keprix.document_vault.store import DocumentVaultStore, get_document_vault_store

CONTRACT_VERSION = "1.0.0"
PRODUCT = "keprix"
CARINA_RUNTIME_REQUIRED = False

__all__ = [
    "CARINA_RUNTIME_REQUIRED",
    "CONTRACT_VERSION",
    "PRODUCT",
    "DocumentVaultFlags",
    "DocumentVaultService",
    "DocumentVaultStore",
    "get_document_vault_service",
    "get_document_vault_store",
    "load_flags",
]
