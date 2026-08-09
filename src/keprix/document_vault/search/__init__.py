"""Document Vault search package (Prompt 652)."""

from __future__ import annotations

from keprix.document_vault.search.citations import VaultCitation, make_source_id
from keprix.document_vault.search.hooks import on_item_restored, on_item_trashed_or_deleted, on_item_written
from keprix.document_vault.search.indexer import VaultContentIndexer
from keprix.document_vault.search.policy import resolve_effective_index_policy, should_index_item
from keprix.document_vault.search.retriever import content_search

__all__ = [
    "VaultCitation",
    "VaultContentIndexer",
    "content_search",
    "make_source_id",
    "on_item_restored",
    "on_item_trashed_or_deleted",
    "on_item_written",
    "resolve_effective_index_policy",
    "should_index_item",
]
