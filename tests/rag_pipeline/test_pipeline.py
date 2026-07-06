"""RAG pipeline tests."""

from __future__ import annotations

import pytest

from keprix.playbook.runtime import playbook_registry
from keprix.rag_pipeline.pipeline import RagPipeline


@pytest.mark.asyncio
async def test_pipeline_ingest_and_query_with_citations() -> None:
    pipeline = RagPipeline("test-pipeline", store_kind="memory")
    ingest = await pipeline.ingest(
        user_id="user-1",
        source_type="plaintext",
        source_id="building-guide",
        content="Building 3 maintenance schedule covers HVAC checks every Monday morning.",
    )
    assert ingest.playbook_run_id
    assert ingest.context.chunks

    query = await pipeline.query(
        user_id="user-1",
        question="What does Building 3 maintenance cover?",
    )
    assert query.context.citations
    assert query.context.answer
    assert "Building 3" in query.context.answer or query.context.citations[0]["snippet"]
    assert query.evaluation_id
    assert query.playbook_run_id
    assert playbook_registry.get(query.playbook_run_id) is not None


@pytest.mark.asyncio
async def test_sqlite_document_store_roundtrip(tmp_path) -> None:
    from keprix.rag_pipeline.document_store import SqliteDocumentStore

    store = SqliteDocumentStore(path=tmp_path / "chunks.sqlite")
    pipeline = RagPipeline("sqlite-pipeline", store=store)

    await pipeline.ingest(
        user_id="user-sqlite",
        source_type="plaintext",
        source_id="policy",
        content="Retention policy keeps audit logs for 90 days.",
    )
    sources = await pipeline.store.list_sources("user-sqlite")
    assert sources
    assert sources[0]["chunk_count"] >= 1
