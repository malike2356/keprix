"""Query engine tests."""

import pytest

from keprix.documents.index_manager import DocumentIndexManager
from keprix.documents.query_engine import DocumentQueryEngine
from keprix.memory.rag.indexer import RagIndexer


@pytest.mark.asyncio
async def test_query_engine_returns_citations_and_path(tmp_path) -> None:
    indexer = RagIndexer()
    manager = DocumentIndexManager(indexer=indexer, store_path=tmp_path / "indexes.json")
    index = manager.create_index(user_id="user-1", name="Research")
    await manager.add_document(
        index.index_id,
        source_id="paper.md",
        source_type="markdown",
        content="Quantum error correction improves reliability of qubit arrays.",
    )
    engine = DocumentQueryEngine(indexer=indexer)
    result = await engine.query("user-1", "What improves qubit reliability?", evidence_first=True)
    assert result.citations
    assert result.retrieval_path
    assert "indexed documents" in result.answer.lower()
    assert result.citations[0].source.endswith("paper.md")
