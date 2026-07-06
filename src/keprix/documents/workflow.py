"""Document-agent workflow orchestration."""

from __future__ import annotations

from typing import Any

from keprix.documents.connector_registry import get_connector
from keprix.documents.index_manager import get_index_manager
from keprix.documents.query_engine import DocumentQueryEngine
from keprix.documents.structured_extract import extract_structured


async def run_ingest_workflow(
    *,
    index_id: str,
    connector: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    doc = await get_connector(connector).load(**payload)
    record = await get_index_manager().add_document(
        index_id,
        source_id=doc.filename,
        source_type=doc.source_type,
        content=doc.text,
        metadata=doc.metadata,
    )
    return {"document": record, "filename": doc.filename, "source_type": doc.source_type}


async def run_query_workflow(
    *,
    user_id: str,
    question: str,
    source_types: list[str] | None = None,
    evidence_first: bool = True,
) -> dict[str, Any]:
    engine = DocumentQueryEngine(indexer=get_index_manager().indexer)
    result = await engine.query(
        user_id,
        question,
        source_types=source_types,
        evidence_first=evidence_first,
    )
    return result.to_dict()


async def run_extract_workflow(*, text: str, schema_name: str) -> dict[str, Any]:
    return extract_structured(text, schema_name)
