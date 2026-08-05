"""Prompt 230 embedding and knowledge pack tests."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
ML_SERVICE = ROOT / "apps/ml-service"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class FakeProvider:
    def dimensions(self, _model: str = "voyage-3") -> int:
        return 1024

    async def embed(self, texts: list[str], _model: str = "voyage-3") -> list[list[float]]:
        return [[1.0 if index == 0 else 0.0 for index in range(1024)] for _text in texts]


class FakeAcquire:
    def __init__(self, conn: "FakeConn"):
        self.conn = conn

    async def __aenter__(self) -> "FakeConn":
        return self.conn

    async def __aexit__(self, *_args: Any) -> None:
        return None


class FakeConn:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.deleted_sources: list[tuple[str, str]] = []

    async def execute(self, query: str, *args: Any) -> None:
        if query.strip().startswith("DELETE FROM knowledge_chunks"):
            self.deleted_sources.append((args[0], args[1]))

    async def executemany(self, _query: str, rows: list[tuple[Any, ...]]) -> None:
        for row in rows:
            self.rows.append(
                {
                    "pack_id": row[0],
                    "source_uri": row[1],
                    "chunk_index": row[2],
                    "content": row[3],
                    "token_count": row[4],
                    "metadata": json.loads(row[6]),
                }
            )

    async def fetch(self, query: str, *_args: Any) -> list[dict[str, Any]]:
        if "FROM knowledge_packs" in query:
            return [{"pack_id": "borehole-operations", "display_name": "Borehole Operations Corpus", "chunk_count": 1}]
        return [
            {
                "content": "Fresh basement granite needs fracture zones for useful water yield.",
                "source_uri": "formation-glossary.txt",
                "chunk_index": 0,
                "metadata": {"source_label": "formation-glossary"},
                "score": 0.82,
            }
        ]


class FakePool:
    def __init__(self) -> None:
        self.conn = FakeConn()

    def acquire(self) -> FakeAcquire:
        return FakeAcquire(self.conn)


def _embedding_service():
    sys.path.insert(0, str(ML_SERVICE))
    try:
        module = _load_module("ml_service_embedding_service_test", ML_SERVICE / "services/embedding_service.py")
        return module.EmbeddingService(FakeProvider(), FakePool())
    finally:
        sys.path.remove(str(ML_SERVICE))


def test_ingest_replaces_source_and_stores_chunks() -> None:
    import asyncio

    service = _embedding_service()
    stored = asyncio.run(
        service.ingest_document(
            "borehole-operations",
            "formation-glossary.txt",
            "granite fracture water yield " * 120,
            {"source_label": "formation-glossary"},
            max_tokens_per_chunk=64,
            overlap_tokens=8,
        )
    )

    assert stored >= 2
    assert service.pool.conn.deleted_sources == [("borehole-operations", "formation-glossary.txt")]
    assert service.pool.conn.rows[0]["metadata"]["source_label"] == "formation-glossary"


def test_search_returns_structured_results() -> None:
    import asyncio

    service = _embedding_service()
    results = asyncio.run(service.search("borehole-operations", "water yield in granite formations"))

    assert results[0].score >= 0.7
    assert results[0].source_uri == "formation-glossary.txt"


def test_embeddings_router_uses_service_dependency() -> None:
    sys.path.insert(0, str(ML_SERVICE))
    try:
        main = _load_module("ml_service_main_embeddings_test", ML_SERVICE / "main.py")
        dependencies = sys.modules["dependencies"]
        dependencies.set_embedding_service(_embedding_service())
        client = TestClient(main.app)
        response = client.post(
            "/embeddings/search",
            json={"pack_id": "borehole-operations", "query": "water yield in granite formations"},
        )
    finally:
        sys.path.remove(str(ML_SERVICE))

    assert response.status_code == 200
    assert response.json()["results"][0]["source_uri"] == "formation-glossary.txt"


def test_search_domain_knowledge_tool_formats_results(monkeypatch) -> None:
    from keprix.tools import ml_service_tools

    monkeypatch.setattr(
        ml_service_tools,
        "_post_json",
        lambda _path, _payload: {
            "results": [
                {
                    "content": "Granite needs fracture zones.",
                    "score": 0.8,
                    "source_uri": "formation-glossary.txt",
                    "chunk_index": 0,
                    "metadata": {"source_label": "formation-glossary"},
                }
            ]
        },
    )

    result = json.loads(
        ml_service_tools.search_domain_knowledge_handler(
            {"query": "granite yield", "pack_id": "borehole-operations"}
        )
    )

    assert result["found"] is True
    assert result["results"][0]["source"] == "formation-glossary"


def test_seed_corpus_contains_three_packs() -> None:
    corpus = ML_SERVICE / "seed/corpus"
    assert (corpus / "borehole-operations/formation-glossary.txt").is_file()
    assert (corpus / "wrc-regulations/wrc-licence-categories.txt").is_file()
    assert (corpus / "gbda-guidelines/membership-stages.txt").is_file()
