"""Codebase self-indexing tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.memory.embeddings import EmbeddingService
from keprix.memory.rag.codebase_indexer import (
    CodebaseRagIndexer,
    build_codebase_document,
    discover_codebase_files,
)
from keprix.memory.rag.indexer import RagIndexer
from keprix.memory.rag.retriever import RagRetriever


@pytest.fixture(autouse=True)
def _deterministic_embeddings(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("KEPRIX_EMBEDDING_DETERMINISTIC", "true")


def test_codebase_discovery_skips_secrets_and_reference_dump(tmp_path: Path):
    (tmp_path / "src" / "keprix").mkdir(parents=True)
    (tmp_path / "src" / "keprix" / "billing.py").write_text(
        "def create_checkout_session():\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "keprix" / ".env").write_text("SECRET=1", encoding="utf-8")
    (tmp_path / "1st-plan").mkdir()
    (tmp_path / "1st-plan" / "competitor.md").write_text("not self", encoding="utf-8")

    files = discover_codebase_files(root=tmp_path, include_roots=["src/keprix", "1st-plan"])
    rel = {path.relative_to(tmp_path).as_posix() for path in files}

    assert "src/keprix/billing.py" in rel
    assert "src/keprix/.env" not in rel
    assert "1st-plan/competitor.md" not in rel


def test_build_codebase_document_includes_path_and_symbols(tmp_path: Path):
    path = tmp_path / "module.py"
    path.write_text(
        "import os\n\nclass BillingPortal:\n    pass\n\ndef checkout():\n    return os.getcwd()\n",
        encoding="utf-8",
    )

    source_id, document = build_codebase_document(path, tmp_path)

    assert source_id == "module.py"
    assert "Keprix codebase file: module.py" in document
    assert "BillingPortal" in document
    assert "checkout" in document


@pytest.mark.asyncio
async def test_codebase_indexer_populates_retrievable_chunks(tmp_path: Path):
    source_dir = tmp_path / "src" / "keprix"
    source_dir.mkdir(parents=True)
    (source_dir / "upgrade.py").write_text(
        "\n".join(
            [
                "class UpgradeWizard:",
                "    def compatibility_check(self):",
                "        return 'migration dry run'",
            ]
        ),
        encoding="utf-8",
    )
    indexer = RagIndexer(database_url="", embeddings=EmbeddingService(deterministic=True))

    stats = await CodebaseRagIndexer(indexer, root=tmp_path).index(user_id="self")
    results = await RagRetriever(indexer=indexer, embeddings=indexer.embeddings).hybrid_search(
        "self",
        "compatibility check migration",
        source_types=["codebase"],
    )

    assert stats.files_indexed == 1
    assert stats.chunks >= 1
    assert results
    assert "upgrade.py" in results[0]["source"]


def test_codebase_rag_api_indexes_and_searches(tmp_path: Path, monkeypatch):
    source_dir = tmp_path / "src" / "keprix"
    source_dir.mkdir(parents=True)
    (source_dir / "memory.py").write_text(
        "def codebase_self_index():\n    return 'rag knows Keprix capabilities'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("KEPRIX_CODEBASE_ROOT", str(tmp_path))
    client = TestClient(create_app())

    indexed = client.post(
        "/api/rag/codebase/index",
        json={"include_roots": ["src/keprix"], "max_files": 25},
        headers={"X-User-Id": "api-self"},
    )
    assert indexed.status_code == 200
    assert indexed.json()["files_indexed"] == 1

    searched = client.post(
        "/api/rag/codebase/search",
        json={"query": "Keprix capabilities self index"},
        headers={"X-User-Id": "api-self"},
    )
    assert searched.status_code == 200
    assert searched.json()["results"]
    assert "memory.py" in searched.json()["results"][0]["source"]
