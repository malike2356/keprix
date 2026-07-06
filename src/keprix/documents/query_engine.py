"""Document query engine with citations and retrieval explanations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from keprix.memory.rag.indexer import RagIndexer
from keprix.documents.redaction import redact_for_log
from keprix.documents.reranker import rerank_chunks
from keprix.documents.retriever import DocumentRetriever


@dataclass
class Citation:
    source: str
    snippet: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "snippet": self.snippet, "score": self.score}


@dataclass
class QueryResult:
    question: str
    answer: str
    citations: list[Citation] = field(default_factory=list)
    retrieval_path: list[str] = field(default_factory=list)
    evidence_first: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "citations": [item.to_dict() for item in self.citations],
            "retrieval_path": self.retrieval_path,
            "evidence_first": self.evidence_first,
        }


class DocumentQueryEngine:
    def __init__(self, retriever: DocumentRetriever | None = None, *, indexer: RagIndexer | None = None) -> None:
        self._retriever = retriever or DocumentRetriever(indexer=indexer)

    async def query(
        self,
        user_id: str,
        question: str,
        *,
        limit: int = 5,
        source_types: list[str] | None = None,
        metadata_filters: dict[str, Any] | None = None,
        evidence_first: bool = True,
    ) -> QueryResult:
        _ = metadata_filters  # reserved for future metadata-aware filtering
        rows = await self._retriever.retrieve(
            user_id,
            question,
            limit=limit,
            source_types=source_types,
            hybrid=True,
        )
        reranked = rerank_chunks(question, rows, limit=limit)
        citations = [
            Citation(
                source=str(row.get("source") or "unknown"),
                snippet=str(row.get("content") or "")[:240],
                score=float(row.get("rerank_score") or row.get("score") or 0.0),
            )
            for row in reranked
        ]
        retrieval_path = [
            "hybrid_retrieval",
            "metadata_filter" if source_types else "no_metadata_filter",
            "rerank",
            "citation_build",
        ]
        if evidence_first and citations:
            evidence = " ".join(f"[{idx + 1}] {cite.snippet}" for idx, cite in enumerate(citations[:3]))
            answer = f"Based on indexed documents: {evidence}"
        elif citations:
            answer = citations[0].snippet
        else:
            answer = "No matching documents were found in the index."
        # Never log raw snippets; audit logs should use redact_for_log if needed.
        _ = redact_for_log(answer)
        return QueryResult(
            question=question,
            answer=answer,
            citations=citations,
            retrieval_path=retrieval_path,
            evidence_first=evidence_first,
        )
