"""RAG indexer and retriever tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.memory.embeddings import EmbeddingService
from keprix.memory.rag.indexer import RagIndexer, chunk_text
from keprix.memory.rag.retriever import RagRetriever


@pytest.fixture(autouse=True)
def _deterministic_embeddings(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("KEPRIX_EMBEDDING_DETERMINISTIC", "true")


def test_chunk_2000_word_document_into_at_least_four_chunks():
    words = ["word"] * 2000
    text = " ".join(words)
    chunks = chunk_text(text, chunk_tokens=512, overlap_tokens=64)
    assert len(chunks) >= 4


@pytest.mark.asyncio
async def test_ingest_and_search_plaintext():
    indexer = RagIndexer(embeddings=EmbeddingService(deterministic=True))
    retriever = RagRetriever(indexer=indexer, embeddings=indexer.embeddings)
    content = "Keprix supports hybrid RAG search across indexed notes and documents."
    chunks = await indexer.ingest(
        user_id="user-rag",
        source_type="plaintext",
        source_id="note-1",
        content=content,
    )
    assert chunks >= 1

    results = await retriever.search("user-rag", "hybrid RAG", limit=3)
    assert results
    assert "hybrid" in results[0]["content"].lower()


@pytest.mark.asyncio
async def test_hybrid_search_ranks_by_combined_score():
    indexer = RagIndexer(embeddings=EmbeddingService(deterministic=True))
    retriever = RagRetriever(indexer=indexer, embeddings=indexer.embeddings)
    await indexer.ingest(
        user_id="user-h",
        source_type="plaintext",
        source_id="a",
        content="alpha beta keyword match document",
    )
    await indexer.ingest(
        user_id="user-h",
        source_type="plaintext",
        source_id="b",
        content="vector only semantic similarity content",
    )
    results = await retriever.hybrid_search("user-h", "keyword match", limit=2)
    assert results
    assert results[0]["score"] >= results[-1]["score"]
    assert "keyword" in results[0]["content"].lower()


def test_rag_ingest_api_creates_retrievable_chunks():
    client = TestClient(create_app())
    ingest = client.post(
        "/api/rag/ingest",
        json={
            "source_type": "plaintext",
            "source_id": "doc-1",
            "content": "Plain text ingestion creates retrievable RAG chunks for keprix.",
        },
        headers={"X-User-Id": "api-user"},
    )
    assert ingest.status_code == 200
    assert ingest.json()["chunks"] >= 1

    search = client.post(
        "/api/rag/search",
        json={"query": "retrievable RAG", "hybrid": True},
        headers={"X-User-Id": "api-user"},
    )
    assert search.status_code == 200
    assert search.json()["results"]
