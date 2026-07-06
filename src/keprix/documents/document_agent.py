"""High-level document agent facade."""

from __future__ import annotations

from typing import Any

from keprix.documents.index_manager import DocumentIndex, get_index_manager
from keprix.documents.workflow import run_extract_workflow, run_ingest_workflow, run_query_workflow


class DocumentAgent:
    def __init__(self) -> None:
        self._indexes = get_index_manager()

    def create_index(self, *, user_id: str, name: str) -> DocumentIndex:
        return self._indexes.create_index(user_id=user_id, name=name)

    async def upload_and_index(
        self,
        index_id: str,
        *,
        filename: str,
        content: bytes | str,
    ) -> dict[str, Any]:
        return await run_ingest_workflow(
            index_id=index_id,
            connector="file",
            payload={"filename": filename, "content": content},
        )

    async def ask(
        self,
        *,
        user_id: str,
        question: str,
        source_types: list[str] | None = None,
        evidence_first: bool = True,
    ) -> dict[str, Any]:
        return await run_query_workflow(
            user_id=user_id,
            question=question,
            source_types=source_types,
            evidence_first=evidence_first,
        )

    async def extract(self, *, text: str, schema_name: str) -> dict[str, Any]:
        return await run_extract_workflow(text=text, schema_name=schema_name)

    def explain_index(self, index_id: str) -> dict[str, Any]:
        coverage = self._indexes.inspect_coverage(index_id)
        stale = self._indexes.list_stale_documents(index_id)
        return {"coverage": coverage, "stale_documents": stale}


_agent: DocumentAgent | None = None


def get_document_agent() -> DocumentAgent:
    global _agent
    if _agent is None:
        _agent = DocumentAgent()
    return _agent
