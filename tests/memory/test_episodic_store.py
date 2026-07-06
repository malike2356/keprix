"""Episodic store tests."""

from __future__ import annotations

import pytest

from keprix.memory.embeddings import EmbeddingService
from keprix.memory.episodic.store import InMemoryEpisodicStore


@pytest.fixture
def store():
    return InMemoryEpisodicStore(embeddings=EmbeddingService(deterministic=True))


@pytest.mark.asyncio
async def test_save_and_search(store):
    await store.save("user-1", "My favorite color is blue", metadata={"tags": ["preference"]})
    await store.save("user-1", "I work on keprix memory systems", metadata={"tags": ["work"]})

    results = await store.search("user-1", "favorite color", limit=5)
    assert results
    assert "blue" in results[0].content.lower()
    assert results[0].score is not None


@pytest.mark.asyncio
async def test_delete_and_clear(store):
    memory_id = await store.save("user-1", "temporary fact")
    await store.delete("user-1", memory_id)
    assert await store.list_all("user-1") == []

    await store.save("user-1", "one")
    await store.save("user-1", "two")
    await store.clear("user-1")
    assert await store.list_all("user-1") == []
