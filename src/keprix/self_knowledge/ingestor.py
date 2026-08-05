"""Ingest synthetic self-knowledge documents into the shared RAG user.

Works alongside the existing SelfKnowledgeIndexer which handles:
- Codebase source files
- Curated product docs (README, AGENTS.md, docs/features/*.md)
- Live capabilities inventory from the module catalog

This ingestor adds: pre-written reference documents covering API routes,
feature flags, settings, billing, architecture, and all other areas that
lack dedicated docs files. Both sets end up in the same Postgres RagIndexer
store under source_type="keprix_self" so retrieve_self_knowledge() finds them.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from keprix.memory.rag.self_knowledge import (
    SELF_KNOWLEDGE_SOURCE_TYPE,
    SELF_KNOWLEDGE_USER_ID,
    SelfKnowledgeIndexer,
    SelfKnowledgeIndexStats,
)
from keprix.self_knowledge.documents import KnowledgeDocument, generate_all_documents

log = logging.getLogger(__name__)


@dataclass
class IngestResult:
    synthetic_docs: int
    synthetic_chunks: int
    full_index_stats: SelfKnowledgeIndexStats | None
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "synthetic_docs": self.synthetic_docs,
            "synthetic_chunks": self.synthetic_chunks,
            "full_index": self.full_index_stats.to_dict() if self.full_index_stats else None,
            "errors": self.errors,
            "total_chunks": self.synthetic_chunks + (
                self.full_index_stats.total_chunks if self.full_index_stats else 0
            ),
        }


class SelfKnowledgeIngestor:
    """Runs a complete self-knowledge ingestion: synthetic docs + full index."""

    def __init__(
        self,
        *,
        user_id: str = SELF_KNOWLEDGE_USER_ID,
        include_codebase: bool = True,
        include_docs: bool = True,
        max_files: int = 1500,
    ) -> None:
        self.user_id = user_id
        self.include_codebase = include_codebase
        self.include_docs = include_docs
        self.max_files = max_files

    async def ingest(self) -> IngestResult:
        errors: list[str] = []
        synthetic_docs = 0
        synthetic_chunks = 0
        full_stats: SelfKnowledgeIndexStats | None = None

        # 1. Ingest synthetic reference documents
        try:
            from keprix.memory.rag.indexer import RagIndexer

            indexer = RagIndexer()
            docs: list[KnowledgeDocument] = generate_all_documents()
            for doc in docs:
                try:
                    chunks = await indexer.ingest(
                        user_id=self.user_id,
                        source_type=SELF_KNOWLEDGE_SOURCE_TYPE,
                        source_id=f"synthetic/{doc.source_id}",
                        content=f"{doc.title}\n\n{doc.content}",
                    )
                    synthetic_chunks += chunks
                    synthetic_docs += 1
                except Exception as exc:
                    errors.append(f"synthetic/{doc.source_id}: {exc}")
        except Exception as exc:
            errors.append(f"RagIndexer unavailable: {exc}")

        # 2. Run the full SelfKnowledgeIndexer (codebase + docs + capabilities)
        try:
            full_stats = await SelfKnowledgeIndexer().index(
                include_codebase=self.include_codebase,
                include_docs=self.include_docs,
                include_capabilities=True,
                max_files=self.max_files,
                user_id=self.user_id,
            )
        except Exception as exc:
            errors.append(f"full_index: {exc}")

        log.info(
            "Self-knowledge ingestion complete: synthetic=%d docs (%d chunks), full=%s, errors=%d",
            synthetic_docs,
            synthetic_chunks,
            full_stats.to_dict() if full_stats else "failed",
            len(errors),
        )
        return IngestResult(
            synthetic_docs=synthetic_docs,
            synthetic_chunks=synthetic_chunks,
            full_index_stats=full_stats,
            errors=errors,
        )


def run_sync() -> IngestResult:
    """Convenience helper for CLI/script use."""
    return asyncio.run(SelfKnowledgeIngestor().ingest())
