"""Document pipeline test fixtures."""

from __future__ import annotations

import pytest

from keprix.documents.index_manager import DocumentIndexManager
from keprix.documents import index_manager as index_manager_module
from keprix.memory.rag.indexer import RagIndexer


@pytest.fixture
def isolated_index_manager(tmp_path, monkeypatch):
    manager = DocumentIndexManager(
        indexer=RagIndexer(),
        store_path=tmp_path / "indexes.json",
    )
    monkeypatch.setattr(index_manager_module, "_manager", manager)
    return manager
